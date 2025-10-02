import abc
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

from app.models import Agent, Forwarded
from app.repositories import ARepository


class A_AgentsRepository(ARepository[Agent, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Agent)

    @abc.abstractmethod
    async def get_recipients_from_sender(self, sender_id: UUID, document_id: UUID | None) -> Sequence[Agent]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_recipients_from_document(self, document_id: UUID) -> Sequence[Agent]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_default_recipients(self) -> Sequence[Agent]:
        raise NotImplementedError

    @abc.abstractmethod
    async def search(
        self,
        *,
        page: int,
        page_size: int,
        name: str | None,
        ids: list[UUID] | None,
        description: str | None,
        is_active: bool | None,
        is_default_recipient: bool | None,
        is_sender: bool | None = None,
        is_recipient: bool | None = None,
    ) -> tuple[list[Agent], int]:
        raise NotImplementedError


class AgentsRepository(A_AgentsRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_recipients_from_sender(self, sender_id: UUID, document_id: UUID | None) -> Sequence[Agent]:
        forwarded_stmt = select(Forwarded.recipient_id).where(
            Forwarded.sender_id == sender_id,
            Forwarded.is_valid.is_(True),
            Forwarded.is_hidden.is_(False),
            Forwarded.recipient_id.isnot(None),
        )

        if document_id:
            forwarded_stmt = forwarded_stmt.where(Forwarded.document_id == document_id)

        forwarded_subquery = forwarded_stmt.distinct().subquery()

        stmt = select(self.model_class).where(self.model_class.id.in_(select(forwarded_subquery.c.recipient_id)))

        result = await self.session.execute(stmt)
        agents = result.scalars().all()
        return agents

    async def get_recipients_from_document(self, document_id: UUID) -> Sequence[Agent]:
        forwarded_subquery = (
            select(Forwarded.recipient_id)
            .where(
                Forwarded.document_id == document_id,
                Forwarded.is_valid.is_(True),
                Forwarded.is_hidden.is_(False),
                Forwarded.recipient_id.isnot(None),
            )
            .distinct()
            .subquery()
        )

        stmt = select(self.model_class).where(self.model_class.id.in_(select(forwarded_subquery.c.recipient_id)))

        result = await self.session.execute(stmt)
        agents = result.scalars().all()
        return agents

    async def get_default_recipients(self) -> Sequence[Agent]:
        stmt = select(self.model_class).where(
            self.model_class.is_default_recipient.is_(True),
            self.model_class.is_active.is_(True),
        )

        result = await self.session.execute(stmt)
        agents = result.scalars().all()
        return agents

    async def search(
        self,
        *,
        page: int,
        page_size: int,
        name: str | None,
        ids: list[UUID] | None,
        description: str | None,
        is_active: bool | None,
        is_default_recipient: bool | None,
        is_sender: bool | None = None,
        is_recipient: bool | None = None,
    ) -> tuple[list[Agent], int]:
        filters: list[Any] = []
        if name:
            filters.append(self.model_class.name.ilike(f"%{name}%"))
        if description:
            filters.append(self.model_class.description.ilike(f"%{description}%"))
        if is_active is not None:
            filters.append(self.model_class.is_active.is_(is_active))
        if ids:
            filters.append(self.model_class.id.in_(ids))
        if is_default_recipient is not None:
            filters.append(self.model_class.is_default_recipient.is_(is_default_recipient))
        if is_sender is not None:
            sender_exists = exists().where(Forwarded.sender_id == self.model_class.id)
            filters.append(sender_exists if is_sender else sender_exists.not_())
        if is_recipient is not None:
            recipient_exists = exists().where(Forwarded.recipient_id == self.model_class.id)
            filters.append(recipient_exists if is_recipient else recipient_exists.not_())

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
        agents = list(result.scalars().all())
        return agents, total
