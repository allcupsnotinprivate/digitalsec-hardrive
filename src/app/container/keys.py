import asyncio
from typing import NewType

import aiocache

DocumentsSemaphore = NewType("DocumentsSemaphore", asyncio.Semaphore)
InvestigationSemaphore = NewType("InvestigationSemaphore", asyncio.Semaphore)
RedisCache = NewType("RedisCache", aiocache.BaseCache)  # type: ignore[valid-newtype]
