import abc
from typing import Literal, Sequence
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import and_, asc, exists

from app.models import DocumentChunk, Forwarded
from app.repositories import ARepository


class ADocumentChunksRepository(ARepository[DocumentChunk, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DocumentChunk)

    @abc.abstractmethod
    async def get_relevant_chunks(
        self,
        embedding: list[float],
        limit: int,
        distance_metric: Literal["cosine", "l2", "inner"],
        sender_id: UUID | None = None,
        is_valid: bool | None = None,
        is_hidden: bool | None = None,
        chunk_score_threshold: float | None = None,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_document_chunks(self, document_id: UUID) -> list[DocumentChunk]:
        raise NotImplementedError


class DocumentChunksRepository(ADocumentChunksRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_relevant_chunks(
        self,
        embedding: list[float],
        limit: int = 10,
        distance_metric: Literal["cosine", "l2", "inner"] = "cosine",
        sender_id: UUID | None = None,
        is_valid: bool | None = None,
        is_hidden: bool | None = None,
        chunk_score_threshold: float | None = None,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        vector = embedding

        if distance_metric == "cosine":
            distance_func = DocumentChunk.embedding.cosine_distance(vector)
            order_direction = asc
        elif distance_metric == "l2":
            distance_func = DocumentChunk.embedding.l2_distance(vector)
            order_direction = asc
        elif distance_metric == "inner":
            distance_func = DocumentChunk.embedding.max_inner_product(vector)
            order_direction = desc
        else:
            raise ValueError(f"Unsupported distance metric: {distance_metric}")

        stmt = select(
            DocumentChunk,
            distance_func.label("cosine_distance"),
        )

        if sender_id is not None or is_valid is not None or is_hidden is not None:
            forwarded_filters = [Forwarded.document_id == DocumentChunk.document_id]
            if sender_id is not None:
                forwarded_filters.append(Forwarded.sender_id == sender_id)
            if is_valid is not None:
                forwarded_filters.append(Forwarded.is_valid.is_(is_valid))
            if is_hidden is not None:
                forwarded_filters.append(Forwarded.is_hidden.is_(is_hidden))

            forwarded_subquery = exists().where(and_(*forwarded_filters))
            stmt = stmt.where(forwarded_subquery)

        if chunk_score_threshold is not None:
            if distance_metric == "inner":
                stmt = stmt.filter(distance_func >= chunk_score_threshold)
            else:
                stmt = stmt.filter(distance_func <= chunk_score_threshold)

        stmt = stmt.order_by(order_direction(distance_func)).limit(limit)

        result = await self.session.execute(stmt)
        return result.all()  # type: ignore[return-value]

    async def get_document_chunks(self, document_id: UUID) -> list[DocumentChunk]:
        stmt = select(self.model_class).filter_by(document_id=document_id)
        result = await self.session.execute(stmt)
        chunks: list[DocumentChunk] = list(result.scalars().all())

        parent_to_chunk = {chunk.parent_id: chunk for chunk in chunks}

        head_chunk = parent_to_chunk.get(None)
        if not head_chunk:
            raise ValueError(f"No head chunk (with parent_id=None) found for document {document_id}")

        ordered_chunks = [head_chunk]
        current_chunk = head_chunk

        while True:
            next_chunk = next((c for c in chunks if c.parent_id == current_chunk.id), None)
            if not next_chunk:
                break
            ordered_chunks.append(next_chunk)
            current_chunk = next_chunk

        return ordered_chunks
