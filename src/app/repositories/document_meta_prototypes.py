import abc
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import desc

from app.models import DocumentMetaPrototype
from app.repositories import ARepository


class ADocumentMetaPrototypesRepository(ARepository[DocumentMetaPrototype, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, DocumentMetaPrototype)

    @abc.abstractmethod
    async def get_last(self, document_id: UUID) -> DocumentMetaPrototype | None:
        raise NotImplementedError


class DocumentMetaPrototypesRepository(ADocumentMetaPrototypesRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_last(self, document_id: UUID) -> DocumentMetaPrototype | None:
        stmt = (
            select(DocumentMetaPrototype)
            .filter_by(document_id=document_id)
            .order_by(desc(DocumentMetaPrototype.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        document_meta_prototype = result.scalars().one_or_none()

        return document_meta_prototype
