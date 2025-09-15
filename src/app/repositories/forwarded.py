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

    @abc.abstractmethod
    async def search(
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

    async def search(
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
        filters: list[Any] = []
        if document_id:
            filters.append(self.model_class.document_id == document_id)
        if sender_id:
            filters.append(self.model_class.sender_id == sender_id)
        if recipient_id:
            filters.append(self.model_class.recipient_id == recipient_id)
        if route_id:
            filters.append(self.model_class.route_id == route_id)
        if is_valid is not None:
            filters.append(self.model_class.is_valid.is_(is_valid))
        if is_hidden is not None:
            filters.append(self.model_class.is_hidden.is_(is_hidden))
        if purpose:
            filters.append(self.model_class.purpose.ilike(f"%{purpose}%"))

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
        forwarded = list(result.scalars().all())
        return forwarded, total
