import abc
from typing import Sequence
from uuid import UUID

from app.exceptions import NotFoundError
from app.infrastructure import ATextSegmenter, ATextVectorizer
from app.models import Document, DocumentChunk, Forwarded
from app.utils.hash import create_sha256_hash

from .aClasses import AService
from .uow import AUnitOfWork


class ADocumentsService(AService, abc.ABC):
    @abc.abstractmethod
    async def admit(self, name: str, content: str) -> Document:
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve(self, id: UUID) -> Document:
        raise NotImplementedError

    @abc.abstractmethod
    async def extract_document_content(self, document_id: UUID) -> str:
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


class DocumentsService(ADocumentsService):
    def __init__(
        self,
        uow: AUnitOfWork,
        segmenter: ATextSegmenter,
        vectorizer: ATextVectorizer,
    ):
        self.uow = uow
        self.segmenter = segmenter
        self.vectorizer = vectorizer

    async def admit(self, name: str, content: str) -> Document:
        content_chunks = await self.segmenter.chunk(content)
        async with self.uow as uow_ctx:
            document = Document(name=name)
            await uow_ctx.documents.add(document)

            previous_chunk_id = None
            for i, chunk in enumerate(content_chunks):
                chunk_embedding = await self.vectorizer.vectorize(chunk)
                chunk_hash = create_sha256_hash(chunk)
                document_chunk = DocumentChunk(
                    content=chunk,
                    embedding=chunk_embedding,
                    hash=chunk_hash,
                    document_id=document.id,
                    parent_id=previous_chunk_id,
                )
                await uow_ctx.document_chunks.add(document_chunk)
                previous_chunk_id = document_chunk.id

        return document

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
