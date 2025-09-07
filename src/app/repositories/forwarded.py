import abc
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

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

    @abc.abstractmethod
    async def get_recipient_stats_for_sender(self, sender_id: UUID) -> dict[UUID, int]:
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

    async def get_recipient_stats_for_sender(self, sender_id: UUID) -> dict[UUID, int]:
        stmt = (
            select(self.model_class.recipient_id, func.count(self.model_class.id))
            .where(
                self.model_class.sender_id == sender_id,
                self.model_class.is_valid.is_(True),
                self.model_class.is_hidden.is_(False),
            )
            .group_by(self.model_class.recipient_id)
        )
        result = await self.session.execute(stmt)
        pairs = result.all()
        return {recipient_id: count for recipient_id, count in pairs}
