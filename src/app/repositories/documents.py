import abc
from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

from app.models import Document
from app.repositories import ARepository


class ADocumentsRepository(ARepository[Document, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Document)

    @abc.abstractmethod
    async def get_by_ids(self, ids: Sequence[UUID]) -> list[Document | None]:
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


class DocumentsRepository(ADocumentsRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_ids(self, ids: Sequence[UUID]) -> list[Document | None]:
        if not ids:
            return []

        stmt = select(Document).where(Document.id.in_(ids))
        result = await self.session.execute(stmt)
        found_docs = result.scalars().all()

        id_to_doc = {doc.id: doc for doc in found_docs}

        return [id_to_doc.get(doc_id) for doc_id in ids]

    async def search(
        self,
        *,
        page: int,
        page_size: int,
        name: str | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> tuple[list[Document], int]:
        filters: list[Any] = []
        if name:
            filters.append(self.model_class.name.ilike(f"%{name}%"))
        if created_from:
            filters.append(self.model_class.created_at >= created_from)
        if created_to:
            filters.append(self.model_class.created_at <= created_to)

        count_stmt = select(func.count()).select_from(self.model_class).where(*filters)
        total_result = await self.session.execute(count_stmt)
        total = int(total_result.scalar_one())

        stmt = (
            select(self.model_class)
            .where(*filters)
            .order_by(self.model_class.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        documents = list(result.scalars().all())
        return documents, total
