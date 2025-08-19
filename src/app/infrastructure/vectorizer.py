import abc

import litellm
import tenacity

from .aClasses import AInfrastructure


class ATextVectorizer(AInfrastructure, abc.ABC):
    @abc.abstractmethod
    async def vectorize(self, text: str) -> list[float]:
        raise NotImplementedError


class TextVectorizer(ATextVectorizer):
    def __init__(self, model: str):
        self.model = model

    async def vectorize(self, text: str) -> list[float]:
        embedding = await self._get_llm_estimation(text)
        return embedding

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(Exception),
    )
    async def _get_llm_estimation(self, text: str) -> list[float]:
        response = await litellm.aembedding(
            model=self.model,
            input=[text],
        )

        embedding: list[float] = response["data"][0]["embedding"]

        return embedding
