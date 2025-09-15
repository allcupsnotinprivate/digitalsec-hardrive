import abc
from datetime import datetime
from typing import Literal, Sequence
from uuid import UUID

from loguru import logger

from app.exceptions import BusinessLogicError, NotFoundError, OperationNotAllowedError
from app.infrastructure import ATextSummarizer
from app.models import Forwarded, PotentialRecipient, ProcessStatus, Route, SimilarDocumentSource

from . import ACandidateEvaluator
from .aClasses import AService
from .agents import A_AgentsService
from .documents import ADocumentsService
from .retrievers import ARetrieverService
from .uow import AUnitOfWork


class ARoutesService(AService, abc.ABC):
    @abc.abstractmethod
    async def initialize(self, document_id: UUID, sender_id: UUID | None = None) -> Route:
        raise NotImplementedError

    @abc.abstractmethod
    async def retrieve(self, id: UUID) -> Route:
        raise NotImplementedError

    @abc.abstractmethod
    async def investigate(self, id: UUID, allow_recovery: bool = False) -> Route:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch(self, id: UUID) -> tuple[Route, Sequence[Forwarded]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def search(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        sender_id: UUID | None,
        status: ProcessStatus | None,
        started_from: datetime | None,
        started_to: datetime | None,
        completed_from: datetime | None,
        completed_to: datetime | None,
    ) -> tuple[list[Route], int]:
        raise NotImplementedError


class RoutesService(ARoutesService):
    def __init__(
        self,
        retriever_limit: int,
        retriever_soft_limit_multiplier: float,
        retriever_score_threshold: float | None,
        retriever_distance_metric: Literal["cosine", "l2", "inner"],
        retriever_aggregation_method: Literal["mean", "max", "top_k_mean"],
        candidate_score_threshold: float,
        uow: AUnitOfWork,
        summarizer: ATextSummarizer,
        retriever: ARetrieverService,
        documents_service: ADocumentsService,
        agents_service: A_AgentsService,
        candidate_evaluator: ACandidateEvaluator,
    ):
        self.retriever_limit = retriever_limit
        self.retriever_soft_limit_multiplier = retriever_soft_limit_multiplier
        self.retriever_score_threshold = retriever_score_threshold
        self.retriever_distance_metric = retriever_distance_metric
        self.retriever_aggregation_method = retriever_aggregation_method
        self.candidate_score_threshold = candidate_score_threshold
        self.uow = uow
        self.retriever = retriever
        self.documents_service = documents_service
        self.agents_service = agents_service
        self.summarizer = summarizer
        self.candidate_evaluator = candidate_evaluator

    async def initialize(self, document_id: UUID, sender_id: UUID | None = None) -> Route:
        async with self.uow as uow_ctx:
            route = Route(document_id=document_id, sender_id=sender_id)
            await uow_ctx.routes.add(route)
        return route

    async def retrieve(self, id: UUID) -> Route:
        async with self.uow as uow_ctx:
            route = await uow_ctx.routes.get(id)
            if not route:
                raise NotFoundError(f"Route with id={id} not found")
        return route

    async def investigate(self, id: UUID, allow_recovery: bool = False) -> Route:
        route = await self.retrieve(id)

        # TODO: It is assumed that it is possible to investigate without sender, but components are not ready for this
        if route.sender_id is None:
            raise BusinessLogicError("It is impossible to conduct investigation without information about sender.")

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

            # similar documents (first line)
            similar_documents = await self.retriever.retrieve_documents_by_similar_document(
                document_id=route.document_id,
                limit=self.retriever_limit,
                sender_id=route.sender_id,
                soft_limit_multiplier=self.retriever_soft_limit_multiplier,
                score_threshold=self.retriever_score_threshold,
                distance_metric=self.retriever_distance_metric,
                aggregation_method=self.retriever_aggregation_method,
            )

            # similar documents (second line)
            duplicate_documents_ids = [doc.id for doc, _ in similar_documents]
            second_similar_documents = await self.retriever.retrieve_documents_by_similar_document(
                document_id=route.document_id,
                limit=self.retriever_limit,
                sender_id=None,
                soft_limit_multiplier=self.retriever_soft_limit_multiplier,
                score_threshold=self.retriever_score_threshold,
                distance_metric=self.retriever_distance_metric,
                aggregation_method=self.retriever_aggregation_method,
                exclude_document_ids=duplicate_documents_ids,
            )
            if not similar_documents and second_similar_documents:
                default_recipients = await self.agents_service.get_default_recipients()
                fallback_score = self.candidate_score_threshold if self.candidate_score_threshold is not None else 0.99
                predicted_forwards = [
                    Forwarded(
                        purpose=None,
                        sender_id=route.sender_id,
                        recipient_id=agent.id,
                        document_id=route.document_id,
                        route_id=route.id,
                        is_valid=None,
                        score=fallback_score,
                    )
                    for agent in default_recipients
                ]
                async with self.uow as uow_ctx:
                    await uow_ctx.forwarded.add_many(predicted_forwards)
                    route = await uow_ctx.routes.update_status(route_id=route.id, status=ProcessStatus.COMPLETED)
                return route

            second_similar_documents = [(doc, score * 0.55) for doc, score in second_similar_documents]
            similar_documents.extend(second_similar_documents)

            # ----- Identifying potential recipients ------

            potential_recipients: dict[UUID, PotentialRecipient] = dict()

            for similar_doc, similar_score in similar_documents:
                try:
                    similar_doc_recipients = await self.agents_service.get_existing_recipients_for_sender(
                        sender_id=route.sender_id,  # type: ignore[arg-type]
                        document_id=similar_doc.id,
                    )
                except (Exception,):
                    logger.warning(
                        "No potential recipients found for similar document.",
                        similar_document_id=similar_doc.id,
                        sender_id=route.sender_id,
                    )
                    continue

                for similar_doc_recipient in similar_doc_recipients:
                    potential_recipient = potential_recipients.get(similar_doc_recipient.id)
                    if not potential_recipient:
                        potential_recipient = PotentialRecipient(agent_id=similar_doc_recipient.id)
                        potential_recipients[similar_doc_recipient.id] = potential_recipient

                    similar_document_source = SimilarDocumentSource(
                        document_id=similar_doc.id, document_similar_score=similar_score
                    )
                    potential_recipient.similar_docs.add(similar_document_source)

            # ----- Score potential recipients ------

            await self.candidate_evaluator.evaluate(
                sender_id=route.sender_id,  # type: ignore[arg-type]
                potential_recipients=potential_recipients,
                similar_documents=similar_documents,
                eligible_threshold=self.candidate_score_threshold,
            )

            # ----- Build forwarded -----

            predicted_forwards = []
            for potential_recipient in potential_recipients.values():
                if potential_recipient.is_eligible:
                    predicted_forwarded = Forwarded(
                        purpose=None,
                        sender_id=route.sender_id,
                        recipient_id=potential_recipient.agent_id,
                        document_id=route.document_id,
                        route_id=route.id,
                        is_valid=None if potential_recipient.is_eligible else False,
                        score=potential_recipient.score,
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

    async def search(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        sender_id: UUID | None,
        status: ProcessStatus | None,
        started_from: datetime | None,
        started_to: datetime | None,
        completed_from: datetime | None,
        completed_to: datetime | None,
    ) -> tuple[list[Route], int]:
        async with self.uow as uow_ctx:
            return await uow_ctx.routes.search(
                page=page,
                page_size=page_size,
                document_id=document_id,
                sender_id=sender_id,
                status=status,
                started_from=started_from,
                started_to=started_to,
                completed_from=completed_from,
                completed_to=completed_to,
            )
