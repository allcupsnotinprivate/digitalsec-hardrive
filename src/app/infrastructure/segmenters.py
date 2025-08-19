import abc
from typing import Any

import nltk
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .aClasses import AInfrastructure
from .vectorizer import ATextVectorizer


class ATextSegmenter(AInfrastructure, abc.ABC):
    @abc.abstractmethod
    async def chunk(self, content: str) -> list[str]:
        raise NotImplementedError


class SemanticTextSegmenter(ATextSegmenter):
    def __init__(
        self,
        max_chunk_size: int,
        min_chunk_size: int,
        similarity_threshold: float,
        language: str,
        vectorizer: ATextVectorizer,
    ):
        self.vectorizer = vectorizer

        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.similarity_threshold = similarity_threshold
        self.language = language

    async def chunk(self, content: str) -> list[str]:
        sentences = self._split_into_sentences(content)

        if not sentences:
            return []

        similarities = await self._calculate_sentence_similarities(sentences)

        chunks = await self._create_semantic_chunks(sentences, similarities)

        return chunks

    async def _calculate_sentence_similarities(self, sentences: list[str]) -> np.ndarray[Any, Any]:
        if len(sentences) <= 1:
            return np.array([[1.0]])

        embeddings = []
        for sentence in sentences:
            if not sentence.strip():
                embeddings.append(np.zeros(1536))
                continue

            try:
                embedding = await self.vectorizer.vectorize(sentence)
                embeddings.append(embedding)  # type: ignore[arg-type]
            except (Exception,):
                embeddings.append(np.zeros(1536))

        try:
            similarity_matrix: np.ndarray[Any, Any] = cosine_similarity(embeddings)
            return similarity_matrix
        except (Exception,):
            return np.zeros((len(sentences), len(sentences)))

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        result: list[str] = nltk.sent_tokenize(text, language="russian")
        return result

    async def _create_semantic_chunks(self, sentences: list[str], similarities: np.ndarray[Any, Any]) -> list[str]:
        chunks = []
        current_chunk = [0]

        for i in range(1, len(sentences)):
            avg_similarity = np.mean([similarities[i, j] for j in current_chunk])

            potential_chunk_size = sum(len(sentences[j]) for j in current_chunk) + len(sentences[i])

            if avg_similarity >= self.similarity_threshold and potential_chunk_size <= self.max_chunk_size:
                current_chunk.append(i)
            else:
                chunks.append(" ".join([sentences[j] for j in current_chunk]))
                current_chunk = [i]

        if current_chunk:
            chunks.append(" ".join([sentences[j] for j in current_chunk]))

        processed_chunks = []
        pending_chunk = []
        pending_size = 0

        for chunk in chunks:
            chunk_size = len(chunk)

            if pending_size + chunk_size <= self.max_chunk_size:
                pending_chunk.append(chunk)
                pending_size += chunk_size
            else:
                if pending_chunk:
                    processed_chunks.append(" ".join(pending_chunk))
                    pending_chunk = []
                    pending_size = 0

                if chunk_size <= self.max_chunk_size:
                    pending_chunk = [chunk]
                    pending_size = chunk_size
                else:
                    processed_chunks.append(chunk)

        if pending_chunk:
            processed_chunks.append(" ".join(pending_chunk))

        final_chunks = []
        for chunk in processed_chunks:
            if len(chunk) >= self.min_chunk_size:
                final_chunks.append(chunk)
            elif final_chunks:
                final_chunks[-1] = final_chunks[-1] + " " + chunk
            else:
                final_chunks.append(chunk)

        return final_chunks
