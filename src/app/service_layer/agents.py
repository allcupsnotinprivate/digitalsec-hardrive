import abc
from typing import Sequence
from uuid import UUID

from app.exceptions import NotFoundError
from app.infrastructure import ATextVectorizer
from app.models import Agent

from .aClasses import AService
from .uow import AUnitOfWork


class A_AgentsService(AService, abc.ABC):
    @abc.abstractmethod
    async def register(self, name: str, description: str | None) -> Agent:
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve(self, id: UUID) -> Agent:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_existing_recipients_for_sender(self, sender_id: UUID, document_id: UUID | None) -> Sequence[Agent]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_existing_recipients_for_document(self, document_id: UUID) -> Sequence[Agent]:
        raise NotImplementedError


class AgentsService(A_AgentsService):
    def __init__(
        self,
        uow: AUnitOfWork,
        vectorizer: ATextVectorizer,
    ):
        self.uow = uow
        self.vectorizer = vectorizer

    async def register(self, name: str, description: str | None) -> Agent:
        description_embedding = None
        if description:
            description_embedding = await self.vectorizer.vectorize(description)
        async with self.uow as uow_ctx:
            agent = Agent(name=name, description=description, embedding=description_embedding)
            await uow_ctx.agents.add(agent)

        return agent

    async def retrieve(self, id: UUID) -> Agent:
        async with self.uow as uow_ctx:
            agent = await uow_ctx.agents.get(id)
            if not agent:
                raise NotFoundError("Agent with id={id} not found")
        return agent

    async def get_existing_recipients_for_sender(self, sender_id: UUID, document_id: UUID | None) -> Sequence[Agent]:
        async with self.uow as uow_ctx:
            existing_recipients = await uow_ctx.agents.get_recipients_from_sender(sender_id, document_id)
        if not existing_recipients:
            raise NotFoundError("No recipients were found for sender.")
        return existing_recipients

    async def get_existing_recipients_for_document(self, document_id: UUID) -> Sequence[Agent]:
        async with self.uow as uow_ctx:
            existing_recipients = await uow_ctx.agents.get_recipients_from_document(document_id)
        if not existing_recipients:
            raise NotFoundError("No recipients were found for document.")
        return existing_recipients
