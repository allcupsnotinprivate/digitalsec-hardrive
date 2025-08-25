import abc
import statistics
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Literal, Sequence
from uuid import UUID

import orjson
from loguru import logger

from app.infrastructure import ARedisClient, ATextVectorizer
from app.models import Document, DocumentChunk
from app.utils.hash import create_md5_hash

from .aClasses import AService
from .uow import AUnitOfWork


class ARetrieverService(AService, abc.ABC):
    @abc.abstractmethod
    async def retrieve_documents_by_similar_document(
        self,
        document_id: UUID,
        sender_id: UUID | None,
        limit: int,
        *,
        distance_metric: Literal["cosine", "l2", "inner"] = "cosine",
        aggregation_method: Literal["mean", "max", "top_k_mean"] = "mean",
        soft_limit_multiplier: float = 3.0,
        score_threshold: float | None = None,
    ) -> Sequence[tuple[Document, float]]:
        raise NotImplementedError


class RetrieverService(ARetrieverService):
    def __init__(self, cache_ttl: int, uow: AUnitOfWork, vectorizer: ATextVectorizer, redis: ARedisClient):
        self.cache_ttl = cache_ttl
        self.uow = uow
        self.vectorizer = vectorizer
        self.redis = redis

    # TODO: Implement soft-limit - take more chunks than `limit` to better aggregate by document_id, and after aggregation trim by limit.
    # TODO: Add weighted aggregation - take into account chunk positions, sizes or chunk weights when aggregating.
    # TODO: Add `score_threshold` parameter to discard irrelevant documents immediately by threshold.
    async def retrieve_documents_by_similar_document(
        self,
        document_id: UUID,
        sender_id: UUID | None,
        limit: int,
        *,
        distance_metric: Literal["cosine", "l2", "inner"] = "cosine",
        aggregation_method: Literal["mean", "max", "top_k_mean"] = "max",
        soft_limit_multiplier: float = 3.0,
        score_threshold: float | None = None,
    ) -> Sequence[tuple[Document, float]]:
        logger.debug(
            "Retriever query",
            definition_type="Query" if isinstance(document_id, str) else "Document ID",
            sender_id=sender_id,
            limit=limit,
            distance_metric=distance_metric,
            aggregation_method=aggregation_method,
        )

        async with self.uow as uow_ctx:
            soft_limit = int(limit * soft_limit_multiplier)

            document_chunks = await uow_ctx.document_chunks.get_document_chunks(document_id=document_id)
            relevant_chunks: list[tuple[DocumentChunk, float]] = list()
            for chunk in document_chunks:
                document_relevant_chunks = await uow_ctx.document_chunks.get_relevant_chunks(
                    embedding=chunk.embedding, limit=soft_limit, distance_metric=distance_metric, sender_id=sender_id
                )
                for candidate_chunk, chunk_score in document_relevant_chunks:
                    if distance_metric == "inner":
                        rerank_score = self._text_similarity(chunk.content, candidate_chunk.content)
                        combined_score = (chunk_score + rerank_score) / 2
                    else:
                        rerank_distance = 1 - self._text_similarity(chunk.content, candidate_chunk.content)
                        combined_score = (chunk_score + rerank_distance) / 2
                    relevant_chunks.append((candidate_chunk, combined_score))

            logger.debug("Found relevant chunks", chunks_count=len(relevant_chunks))

            doc_scores: dict[UUID, list[tuple[float, float]]] = defaultdict(list)
            for chunk, score in relevant_chunks:
                weight = self._chunk_weight(chunk)
                doc_scores[chunk.document_id].append((score, weight))

            doc_id_with_score: list[tuple[UUID, float]] = []
            for doc_id, score_weight_pairs in doc_scores.items():
                aggregated = self._aggregate_scores(
                    score_weight_pairs, method=aggregation_method, distance_metric=distance_metric
                )
                logger.debug(
                    "Aggregated score has been obtained",
                    score=aggregated,
                    score_threshold=score_threshold,
                    distance_metric=distance_metric,
                )
                if score_threshold is None:
                    doc_id_with_score.append((doc_id, aggregated))
                else:
                    if distance_metric == "inner":
                        if aggregated >= score_threshold:
                            doc_id_with_score.append((doc_id, aggregated))
                    else:
                        if aggregated <= score_threshold:
                            doc_id_with_score.append((doc_id, aggregated))

            if distance_metric == "inner":
                doc_id_with_score.sort(key=lambda tup: tup[1], reverse=True)
            else:
                doc_id_with_score.sort(key=lambda tup: tup[1])

            sorted_doc_ids = [doc_id for doc_id, _ in doc_id_with_score]
            documents = await uow_ctx.documents.get_by_ids(sorted_doc_ids)
            doc_by_id = {doc.id: doc for doc in documents if doc is not None}

            logger.debug("Aggregated documents", documnets_count=len(doc_id_with_score))

            final_result: list[tuple[Document, float]] = []
            for doc_id, score in doc_id_with_score[:limit]:
                doc = doc_by_id.get(doc_id)
                if doc:
                    final_result.append((doc, score))

            logger.debug("Returning documents", documents_count=len(final_result))

            # statistic logs
            if not final_result:
                logger.warning("No documents retrieved")
            else:
                scores = [score for _, score in final_result]
                chunk_scores = [score for _, score in relevant_chunks]
                logger.info(
                    "Retrieval statistics",
                    document_min_score=f"{min(scores):.4f}",
                    document_max_score=f"{max(scores):.4f}",
                    document_mean_score=f"{statistics.mean(scores):.4f}",
                    chunk_min_score=f"{min(chunk_scores):.4f}",
                    chunk_max_score=f"max={max(chunk_scores):.4f}",
                    chunk_mean_score=f"{statistics.mean(chunk_scores):.4f}",
                )

            return final_result

    @staticmethod
    def _aggregate_scores(
        scores: list[tuple[float, float]],
        method: Literal["mean", "max", "top_k_mean"],
        *,
        distance_metric: Literal["cosine", "l2", "inner"],
        k: int = 3,
    ) -> float:
        if method == "mean":
            total_weight = sum(weight for _, weight in scores)
            if total_weight == 0:
                return 0.0
            return sum(score * weight for score, weight in scores) / total_weight
        if method == "max":
            if distance_metric == "inner":
                return max(score for score, _ in scores)
            return min(score for score, _ in scores)
        if method == "top_k_mean":
            if distance_metric == "inner":
                top_scores = sorted(scores, key=lambda s: s[0], reverse=True)[:k]
            else:
                top_scores = sorted(scores, key=lambda s: s[0])[:k]
            total_weight = sum(weight for _, weight in top_scores)
            if total_weight == 0:
                return 0.0
            return sum(score * weight for score, weight in top_scores) / total_weight
        raise ValueError(f"Unknown aggregation method: {method}")

    async def _vectorize(self, text: str) -> list[float]:
        text_hash = str(create_md5_hash(text, as_bytes=False))
        cache_key = f"retriever:embeddings:{text_hash}"

        cached = await self.redis.get(cache_key)
        if cached:
            embedding = orjson.loads(cached)
            if isinstance(embedding, list):
                return embedding

        embedding = await self.vectorizer.vectorize(text)
        await self.redis.set(cache_key, orjson.dumps(embedding), ex=self.cache_ttl)
        return embedding

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        return SequenceMatcher(None, text1, text2).ratio()

    @staticmethod
    def _chunk_weight(chunk: DocumentChunk) -> float:
        size_weight = float(len(chunk.content))
        position_weight = 2.0 if chunk.parent_id is None else 1.0
        return size_weight * position_weight
