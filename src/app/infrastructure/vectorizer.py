import abc

import litellm
import tenacity
from aiocache import BaseCache
from loguru import logger

from app.utils.hash import create_md5_hash

from .aClasses import AInfrastructure


class ATextVectorizer(AInfrastructure, abc.ABC):
    @abc.abstractmethod
    async def vectorize(self, text: str) -> list[float]:
        raise NotImplementedError


class TextVectorizer(ATextVectorizer):
    def __init__(self, base_url: str | None, api_key: str, model: str, cache: BaseCache):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.cache = cache
        self.namespace = "vectorizer"

    async def vectorize(self, text: str) -> list[float]:
        cache_key = self.cache.build_key(create_md5_hash(text, as_bytes=False), self.namespace)
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        embedding = await self._get_embeddings(text)
        logger.debug("Embedding built", embedding_dim=len(embedding), text_size=len(text))

        await self.cache.set(cache_key, embedding, ttl=300)

        return embedding

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        retry=tenacity.retry_if_exception_type(Exception),
        wait=tenacity.wait_random_exponential(multiplier=1, max=60),
    )
    async def _get_embeddings(self, text: str) -> list[float]:
        try:
            response = await litellm.aembedding(
                model=self.model,
                api_base=self.base_url,
                api_key=self.api_key,
                input=[text],
            )
        except Exception as e:
            raise

        embedding: list[float] = response["data"][0]["embedding"]

        return embedding
