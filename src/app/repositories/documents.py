import abc
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.repositories import ARepository


class ADocumentsRepository(ARepository[Document, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Document)

    @abc.abstractmethod
    async def get_by_ids(self, ids: Sequence[UUID]) -> list[Document | None]:
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
