import abc
import mimetypes
from datetime import datetime
from typing import Mapping, Sequence, TypedDict
from uuid import UUID, uuid4

import numpy as np
from loguru import logger

from app.exceptions import BusinessLogicError, NotFoundError
from app.infrastructure import AS3Client, ATextSegmenter, ATextVectorizer
from app.models import Document, DocumentChunk, Forwarded
from app.utils.cleaners import ATextCleaner
from app.utils.files import sanitize_filename
from app.utils.hash import create_sha256_hash

from .aClasses import AService
from .uow import AUnitOfWork


class ForwardedUpdateData(TypedDict, total=False):
    is_hidden: bool
    is_valid: bool | None
    purpose: str | None


class ADocumentsService(AService, abc.ABC):
    @abc.abstractmethod
    async def admit(
            self,
            name: str,
            *,
            text_content: str | None = None,
            file_bytes: bytes | None = None,
            content_type: str | None = None,
            original_filename: str | None = None,
            metadata: Mapping[str, str] | None = None,
    ) -> Document:
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve(self, id: UUID) -> Document:
        raise NotImplementedError

    @abc.abstractmethod
    async def extract_document_content(self, document_id: UUID) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def build_download_url(self, document: Document, *, expires_in: int | None = None) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_download_url(self, document_id: UUID, *, expires_in: int | None = None) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def forward(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        document_id: UUID,
        route_id: UUID | None = None,
        is_valid: bool | None = None,
        purpose: str | None = None,
    ) -> Forwarded:
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve_forwards(self, id: UUID, sender_id: UUID | None) -> Sequence[Forwarded]:
        raise NotImplementedError

    @abc.abstractmethod
    async def search(
        self,
        *,
        page: int,
        page_size: int,
        name: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> tuple[list[Document], int]:
        raise NotImplementedError

    @abc.abstractmethod
    async def search_chunks(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        parent_id: UUID | None,
        content: str | None,
    ) -> tuple[list[DocumentChunk], int]:
        raise NotImplementedError

    @abc.abstractmethod
    async def search_forwarded(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        sender_id: UUID | None,
        recipient_id: UUID | None,
        route_id: UUID | None,
        is_valid: bool | None,
        is_hidden: bool | None,
        purpose: str | None,
    ) -> tuple[list[Forwarded], int]:
        raise NotImplementedError

    @abc.abstractmethod
    async def update_forwarded(self, forwarded_id: UUID, changes: ForwardedUpdateData) -> Forwarded:
        raise NotImplementedError


class DocumentsService(ADocumentsService):
    def __init__(
        self,
            uow: AUnitOfWork,
            segmenter: ATextSegmenter,
            vectorizer: ATextVectorizer,
            text_cleaner: ATextCleaner,
            storage_client: AS3Client,
            storage_bucket: str,
            presigned_url_ttl: int,
    ):
        self.uow = uow
        self.segmenter = segmenter
        self.vectorizer = vectorizer
        self.text_cleaner = text_cleaner
        self.storage_client = storage_client
        self.storage_bucket = storage_bucket
        self.presigned_url_ttl = presigned_url_ttl
        self._bucket_initialized = False

    async def admit(
            self,
            name: str,
            *,
            text_content: str | None = None,
            file_bytes: bytes | None = None,
            content_type: str | None = None,
            original_filename: str | None = None,
            metadata: Mapping[str, str] | None = None,
    ) -> Document:
        if (text_content is None and file_bytes is None) or (text_content is not None and file_bytes is not None):
            raise BusinessLogicError("Provide either raw text or a document file for admission, not both.")

        await self._ensure_bucket()

        metadata_payload: dict[str, str] = dict(metadata or {})
        metadata_payload.setdefault("document_name", name)

        if file_bytes is None:
            assert text_content is not None  # for type-checkers
            if not text_content.strip():
                raise BusinessLogicError("Document content must not be empty.")

            normalized_filename = sanitize_filename(name, ".txt")
            original_name = normalized_filename
            bytes_payload = text_content.encode("utf-8")
            resolved_content_type = content_type or "text/plain; charset=utf-8"
            raw_content = text_content
            metadata_payload.setdefault("source", "text")
        else:
            normalized_filename = sanitize_filename(original_filename or name)
            original_name = original_filename or normalized_filename
            bytes_payload = file_bytes
            guessed_type, _ = mimetypes.guess_type(normalized_filename)
            resolved_content_type = content_type or guessed_type or "application/octet-stream"
            raw_content = file_bytes.decode("utf-8", errors="ignore")
            metadata_payload.setdefault("source", "file")

        metadata_payload.setdefault("original_filename", original_name)

        clean_content = self.text_cleaner.clean(raw_content)
        logger.debug("Text cleared", original_size=len(raw_content), final_size=len(clean_content))

        content_chunks = await self.segmenter.chunk(clean_content)

        document_id = uuid4()
        metadata_payload.setdefault("document_id", str(document_id))
        storage_key = f"documents/{document_id}/{normalized_filename}"

        await self.storage_client.upload(
            bucket=self.storage_bucket,
            key=storage_key,
            body=bytes_payload,
            content_type=resolved_content_type,
            metadata=metadata_payload,
        )

        async with self.uow as uow_ctx:
            document = Document(
                id=document_id,
                name=name,
                storage_bucket=self.storage_bucket,
                storage_key=storage_key,
                content_type=resolved_content_type,
                file_size=len(bytes_payload),
                original_filename=original_name,
                storage_metadata=metadata_payload or None,
            )
            await uow_ctx.documents.add(document)

            previous_chunk_id = None
            for i, chunk in enumerate(content_chunks):
                chunk_hash = create_sha256_hash(chunk)

                try:
                    chunk_embedding = await self.vectorizer.vectorize(chunk)
                except (Exception,):
                    logger.exception("Failed to vectorize chunk", chunk_length=len(chunk), chunk_hash=chunk_hash)
                    chunk_embedding = np.zeros(1024)  # type: ignore[assignment]

                document_chunk = DocumentChunk(
                    content=chunk,
                    embedding=chunk_embedding,
                    hash=chunk_hash,
                    document_id=document.id,
                    parent_id=previous_chunk_id,
                )
                await uow_ctx.document_chunks.add(document_chunk)
                previous_chunk_id = document_chunk.id

        logger.debug(
            "Document admitted",
            document_id=document.id,
            chunks=len(content_chunks),
            storage_key=storage_key,
        )

        return document

    async def build_download_url(self, document: Document, *, expires_in: int | None = None) -> str:
        if not document.storage_key or not document.storage_bucket:
            raise BusinessLogicError("Document storage metadata is not available.")

        await self._ensure_bucket()
        ttl = expires_in or self.presigned_url_ttl
        return await self.storage_client.generate_presigned_url(
            bucket=document.storage_bucket,
            key=document.storage_key,
            expires_in=ttl,
        )

    async def get_download_url(self, document_id: UUID, *, expires_in: int | None = None) -> str:
        document = await self.retrieve(document_id)
        return await self.build_download_url(document, expires_in=expires_in)

    async def _ensure_bucket(self) -> None:
        if self._bucket_initialized:
            return
        await self.storage_client.ensure_bucket(self.storage_bucket)
        self._bucket_initialized = True

    async def retrieve(self, id: UUID) -> Document:
        async with self.uow as uow_ctx:
            document = await uow_ctx.documents.get(id)
            if not document:
                raise NotFoundError("Document with id={id} not found")
        return document

    async def extract_document_content(self, document_id: UUID) -> str:
        async with self.uow as uow_ctx:
            document_chunks = await uow_ctx.document_chunks.get_document_chunks(document_id=document_id)
        content = "\n".join(chunk.content for chunk in document_chunks)
        return content

    async def forward(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        document_id: UUID,
        route_id: UUID | None = None,
        is_valid: bool | None = None,
        purpose: str | None = None,
    ) -> Forwarded:
        async with self.uow as uow_ctx:
            forwarded = Forwarded(
                purpose=purpose,
                is_valid=is_valid,
                route_id=route_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                document_id=document_id,
            )
            await uow_ctx.forwarded.add(forwarded)
        return forwarded

    async def retrieve_forwards(self, id: UUID, sender_id: UUID | None = None) -> Sequence[Forwarded]:
        async with self.uow as uow_ctx:
            forwards = await uow_ctx.forwarded.get_by_document_id(document_id=id, sender_id=sender_id)
        return forwards

    async def search(
        self,
        *,
        page: int,
        page_size: int,
        name: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> tuple[list[Document], int]:
        async with self.uow as uow_ctx:
            return await uow_ctx.documents.search(
                page=page,
                page_size=page_size,
                name=name,
                created_from=created_from,
                created_to=created_to,
            )

    async def search_chunks(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        parent_id: UUID | None,
        content: str | None,
    ) -> tuple[list[DocumentChunk], int]:
        async with self.uow as uow_ctx:
            return await uow_ctx.document_chunks.search(
                page=page,
                page_size=page_size,
                document_id=document_id,
                parent_id=parent_id,
                content=content,
            )

    async def search_forwarded(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        sender_id: UUID | None,
        recipient_id: UUID | None,
        route_id: UUID | None,
        is_valid: bool | None,
        is_hidden: bool | None,
        purpose: str | None,
    ) -> tuple[list[Forwarded], int]:
        async with self.uow as uow_ctx:
            return await uow_ctx.forwarded.search(
                page=page,
                page_size=page_size,
                document_id=document_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                route_id=route_id,
                is_valid=is_valid,
                is_hidden=is_hidden,
                purpose=purpose,
            )

    async def update_forwarded(self, forwarded_id: UUID, changes: ForwardedUpdateData) -> Forwarded:
        if not changes:
            raise BusinessLogicError("No fields provided for update")

        async with self.uow as uow_ctx:
            forwarded = await uow_ctx.forwarded.update_fields(forwarded_id, changes)

            if not forwarded:
                raise NotFoundError(f"Forwarded with id={forwarded_id} not found")

        return forwarded
