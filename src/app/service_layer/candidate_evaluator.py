import abc
from collections import defaultdict
from typing import Sequence
from uuid import UUID

from loguru import logger

from app.models import Document, PotentialRecipient

from .aClasses import AService
from .uow import AUnitOfWork


class ACandidateEvaluator(AService, abc.ABC):
    @abc.abstractmethod
    async def evaluate(
        self,
        sender_id: UUID,
        potential_recipients: dict[UUID, PotentialRecipient],
        similar_documents: Sequence[tuple[Document, float]],
        eligible_threshold: float,
    ) -> None:
        raise NotImplementedError


class CandidateEvaluator(ACandidateEvaluator):
    def __init__(self, uow: AUnitOfWork):
        self.uow = uow

    async def evaluate(
        self,
        sender_id: UUID,
        potential_recipients: dict[UUID, PotentialRecipient],
        similar_documents: Sequence[tuple[Document, float]],
        eligible_threshold: float,
    ) -> None:
        frequency_scores = self._frequency_score(potential_recipients)
        collaborative_scores = await self._collaborative_score(sender_id, potential_recipients)
        historical_scores = await self._historical_score(potential_recipients, similar_documents)

        for agent_id, recipient in potential_recipients.items():
            total = frequency_scores.get(agent_id, 0.0)
            total += collaborative_scores.get(agent_id, 0.0)
            total += historical_scores.get(agent_id, 0.0)
            recipient.score = total / 3
            recipient.is_eligible = recipient.score > eligible_threshold

            logger.debug(
                "Aggregated weighted assessment of a potential candidate.",
                agent_id=agent_id,
                score=recipient.score,
                is_eligible=recipient.is_eligible,
            )

    @staticmethod
    def _frequency_score(potential_recipients: dict[UUID, PotentialRecipient]) -> dict[UUID, float]:
        freq: dict[UUID, float] = {}
        for agent_id, recipient in potential_recipients.items():
            score = 0.0
            for doc_source in recipient.similar_docs:
                score += doc_source.document_similar_score or 1.0
            freq[agent_id] = score

        max_score = max(freq.values(), default=0.0)
        if max_score == 0:
            return {agent_id: 0.0 for agent_id in potential_recipients.keys()}

        return {agent_id: score / max_score for agent_id, score in freq.items()}

    async def _collaborative_score(
        self, sender_id: UUID, potential_recipients: dict[UUID, PotentialRecipient]
    ) -> dict[UUID, float]:
        async with self.uow as uow_ctx:
            stats = await uow_ctx.forwarded.get_recipient_stats_for_sender(sender_id)

        max_count = max(stats.values(), default=0)
        if max_count == 0:
            return {agent_id: 0.0 for agent_id in potential_recipients.keys()}

        return {agent_id: stats.get(agent_id, 0) / max_count for agent_id in potential_recipients.keys()}

    async def _historical_score(
        self,
        potential_recipients: dict[UUID, PotentialRecipient],
        similar_documents: Sequence[tuple[Document, float]],
    ) -> dict[UUID, float]:
        counts: defaultdict[UUID, float] = defaultdict(float)
        async with self.uow as uow_ctx:
            for document, weight in similar_documents:
                forwards = await uow_ctx.forwarded.get_by_document_id(document.id, sender_id=None)
                forwards = sorted(forwards, key=lambda f: f.created_at)
                for idx in range(len(forwards) - 1):
                    nxt = forwards[idx + 1].recipient_id
                    if nxt in potential_recipients:
                        counts[nxt] += weight or 1.0

        max_count = max(counts.values(), default=0.0)
        if max_count == 0:
            return {agent_id: 0.0 for agent_id in potential_recipients.keys()}

        return {agent_id: counts.get(agent_id, 0.0) / max_count for agent_id in potential_recipients.keys()}
