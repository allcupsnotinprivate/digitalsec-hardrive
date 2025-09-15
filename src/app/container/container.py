import asyncio

import aiocache
import aioinject

from app import infrastructure, service_layer
from app.configs import Settings
from app.utils.cleaners import ATextCleaner

from .keys import DocumentsSemaphore, InvestigationSemaphore, RedisCache
from .wrappers import (
    BasicDocumentCleanerWrapper,
    PostgresDatabaseWrapper,
    RabbitMQWrapper,
    RedisClientWrapper,
    RetrieverServiceWrapper,
    RoutesServiceWrapper,
    SemanticTextSegmenterWrapper,
    TextSummarizerWrapper,
    TextVectorizerWrapper,
)

# Container & settings

container = aioinject.Container()
settings = Settings()

# settings
container.register(aioinject.Object(settings))

# resources
container.register(
    aioinject.Object(asyncio.Semaphore(settings.internal.documents.loading_parallelism), DocumentsSemaphore),
    aioinject.Object(asyncio.Semaphore(settings.internal.router.investigation_parallelism), InvestigationSemaphore),
    aioinject.Object(aiocache.Cache.from_url(settings.external.redis.url_with_pool_max_size(10)), RedisCache),
)


# utils
container.register(
    aioinject.Singleton(BasicDocumentCleanerWrapper, ATextCleaner),
)

# infrastructure
container.register(
    aioinject.Singleton(PostgresDatabaseWrapper, infrastructure.APostgresDatabase),
    aioinject.Singleton(infrastructure.SchedulerManager, infrastructure.ASchedulerManager),
    aioinject.Singleton(TextVectorizerWrapper, infrastructure.ATextVectorizer),
    aioinject.Singleton(SemanticTextSegmenterWrapper, infrastructure.ATextSegmenter),
    aioinject.Singleton(TextSummarizerWrapper, infrastructure.ATextSummarizer),
    aioinject.Singleton(RedisClientWrapper, infrastructure.ARedisClient),
    aioinject.Singleton(RabbitMQWrapper, infrastructure.ARabbitMQ),
)

# service layer
container.register(
    aioinject.Transient(service_layer.UnitOfWork, service_layer.AUnitOfWork),
    aioinject.Transient(service_layer.AgentsService, service_layer.A_AgentsService),
    aioinject.Transient(service_layer.DocumentsService, service_layer.ADocumentsService),
    aioinject.Transient(RetrieverServiceWrapper, service_layer.ARetrieverService),
    aioinject.Transient(RoutesServiceWrapper, service_layer.ARoutesService),
    aioinject.Transient(service_layer.CandidateEvaluator, service_layer.ACandidateEvaluator),
)
