import abc
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
