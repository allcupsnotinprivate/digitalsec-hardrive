import abc
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Forwarded
from app.repositories import ARepository


class AForwardedRepository(ARepository[Forwarded, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Forwarded)

    @abc.abstractmethod
    async def get_by_document_id(self, document_id: UUID, sender_id: UUID | None) -> Sequence[Forwarded]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_route_id(self, route_id: UUID) -> Sequence[Forwarded]:
        raise NotImplementedError


class ForwardedRepository(AForwardedRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_document_id(self, document_id: UUID, sender_id: UUID | None = None) -> Sequence[Forwarded]:
        stmt = select(self.model_class).filter_by(document_id=document_id)
        if sender_id:
            stmt = stmt.filter_by(sender_id=sender_id)
        result = await self.session.execute(stmt)
        forwards = result.scalars().all()
        return forwards  # noqa

    async def get_by_route_id(self, route_id: UUID) -> Sequence[Forwarded]:
        stmt = select(self.model_class).filter_by(route_id=route_id)
        result = await self.session.execute(stmt)
        forwards = result.scalars().all()
        return forwards  # noqa
