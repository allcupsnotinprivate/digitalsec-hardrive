import abc
from typing import Sequence
from uuid import UUID

from loguru import logger

from app.exceptions import BusinessLogicError, NotFoundError, OperationNotAllowedError
from app.infrastructure import ATextSummarizer
from app.models import Forwarded, PotentialRecipient, ProcessStatus, Route, SimilarDocumentSource

from .aClasses import AService
from .agents import A_AgentsService
from .documents import ADocumentsService
from .retrievers import ARetrieverService
from .uow import AUnitOfWork


class ARoutesService(AService, abc.ABC):
    @abc.abstractmethod
    async def initialize(self, document_id: UUID) -> Route:
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve(self, id: UUID) -> Route:
        raise NotImplementedError

    @abc.abstractmethod
    async def investigate(self, id: UUID, sender_id: UUID | None, allow_recovery: bool = False) -> Route:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch(self, id: UUID) -> tuple[Route, Sequence[Forwarded]]:
        raise NotImplementedError


class RoutesService(ARoutesService):
    def __init__(
        self,
        retriever_limit: int,
        retriever_soft_limit_multiplier: float,
        retriever_score_threshold: float | None,
        uow: AUnitOfWork,
        summarizer: ATextSummarizer,
        retriever: ARetrieverService,
        documents_service: ADocumentsService,
        agents_service: A_AgentsService,
    ):
        self.retriever_limit = retriever_limit
        self.retriever_soft_limit_multiplier = retriever_soft_limit_multiplier
        self.retriever_score_threshold = retriever_score_threshold
        self.uow = uow
        self.retriever = retriever
        self.documents_service = documents_service
        self.agents_service = agents_service
        self.summarizer = summarizer

    async def initialize(self, document_id: UUID) -> Route:
        async with self.uow as uow_ctx:
            route = Route(document_id=document_id)
            await uow_ctx.routes.add(route)
        return route

    async def retrieve(self, id: UUID) -> Route:
        async with self.uow as uow_ctx:
            route = await uow_ctx.routes.get(id)
            if not route:
                raise NotFoundError(f"Route with id={id} not found")
        return route

    async def investigate(self, id: UUID, sender_id: UUID | None, allow_recovery: bool = False) -> Route:
        if not sender_id:
            raise BusinessLogicError("It is impossible to conduct investigation without information about sender.")

        route = await self.retrieve(id)

        if route.status != ProcessStatus.PENDING:
            if allow_recovery and route.status in (ProcessStatus.FAILED, ProcessStatus.TIMEOUT):
                async with self.uow as uow_ctx:
                    route = await uow_ctx.routes.update_status(id, ProcessStatus.PENDING)
            else:
                raise OperationNotAllowedError(f"Route investigation completed with status {route.status.value}")

        async with self.uow as uow_ctx:
            route = await uow_ctx.routes.update_status(id, ProcessStatus.IN_PROGRESS)

        try:
            # ----- Retrieve Similar Documents ------

            similar_documents = await self.retriever.retrieve_documents_by_similar_document(
                document_id=route.document_id,
                limit=self.retriever_limit,
                sender_id=sender_id,
                soft_limit_multiplier=self.retriever_soft_limit_multiplier,
                score_threshold=self.retriever_score_threshold,
            )

            if not similar_documents:
                raise BusinessLogicError("No similar documents could be found.")

            # ----- Identifying potential recipients ------

            potential_recipients: dict[UUID, PotentialRecipient] = dict()

            for similar_doc, similar_score in similar_documents:
                try:
                    similar_doc_recipients = await self.agents_service.get_existing_recipients_for_sender(
                        sender_id=sender_id, document_id=similar_doc.id
                    )
                except (Exception,):
                    logger.warning(
                        "No potential recipients found for similar document.",
                        similar_document_id=similar_doc.id,
                        sender_id=sender_id,
                    )
                    continue

                for similar_doc_recipient in similar_doc_recipients:
                    potential_recipient = potential_recipients.get(similar_doc_recipient.id)
                    if not potential_recipient:
                        # TODO: mechanism for determining eligibility should be implemented in further steps
                        potential_recipient = PotentialRecipient(agent_id=similar_doc_recipient.id, is_eligible=True)
                        potential_recipients[similar_doc_recipient.id] = potential_recipient

                    similar_document_source = SimilarDocumentSource(
                        document_id=similar_doc.id, document_similar_score=similar_score
                    )
                    potential_recipient.similar_docs.add(similar_document_source)

            # ----- Score potential recipients ------

            # TODO:
            # 1) Calculate score of potential recipients by:
            #    a) Frequency of occurrence in found similar documents (more occurrences → higher score).
            #    b) Semantic similarity of recipient's description (Agent.description / Agent.embedding)
            #       with summary/document content.
            #    c) Load factor: inverse of recipient's current workload
            # 2) Add if necessary:
            #    a) Take into account `recency` (how long ago last forwarded was sent to this agent).
            #    b) Take into account prior `success_rate` of forwarding (is_valid in Forwarded) to recipient for similar documents.
            #    c) Apply exclusion rules if recipient has conflicts of interest or is in a denylist.
            # 3) Combine metrics into final `weighted_score` with configurable weights:
            #    final_score = w1 * frequency_score + w2 * semantic_similarity_score + w3 * recency_score + ...
            #    and cut off (`is_eligible`) by threshold, or sort by final_score.

            # ----- Build forwarded -----

            predicted_forwards = []
            for potential_recipient in potential_recipients.values():
                if potential_recipient.is_eligible:
                    predicted_forwarded = Forwarded(
                        purpose=None,
                        sender_id=sender_id,
                        recipient_id=potential_recipient.agent_id,
                        document_id=route.document_id,
                        route_id=route.id,
                        is_valid=None,
                    )
                    predicted_forwards.append(predicted_forwarded)

            async with self.uow as uow_ctx:
                await uow_ctx.forwarded.add_many(predicted_forwards)
                route = await uow_ctx.routes.update_status(route_id=route.id, status=ProcessStatus.COMPLETED)

        except Exception as e:
            async with self.uow as uow_ctx:
                route = await uow_ctx.routes.update_status(route_id=route.id, status=ProcessStatus.FAILED)
            logger.error("Failed to conduct investigation", exc=e)

        return route

    async def fetch(self, id: UUID) -> tuple[Route, Sequence[Forwarded]]:
        route = await self.retrieve(id)
        async with self.uow as uow_ctx:
            forwards = await uow_ctx.forwarded.get_by_route_id(route_id=id)
        return route, forwards
