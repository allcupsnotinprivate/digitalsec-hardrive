from app import infrastructure, service_layer
from app.configs import Settings
from app.container.keys import RedisCache
from app.utils.cleaners import BasicDocumentCleaner


class PostgresDatabaseWrapper(infrastructure.PostgresDatabase):
    def __init__(self, settings: Settings):
        pg = settings.external.postgres
        super().__init__(
            user=pg.user,
            password=pg.password,
            host=pg.host,
            port=pg.port,
            database=pg.database,
            automigrate=pg.automigrate,
        )


class SemanticTextSegmenterWrapper(infrastructure.SemanticTextSegmenter):
    def __init__(self, settings: Settings, vectorizer: infrastructure.ATextVectorizer, cache: RedisCache):
        sg = settings.internal.segmenter
        super().__init__(
            max_chunk_size=sg.max_chunk_size,
            min_chunk_size=sg.min_chunk_size,
            similarity_threshold=sg.similarity_threshold,
            language=sg.language,
            vectorizer=vectorizer,
            cache=cache,
        )


class TextSummarizerWrapper(infrastructure.TextSummarizer):
    def __init__(self, settings: Settings):
        ts = settings.external.summarizer
        super().__init__(model=ts.model)


class TextVectorizerWrapper(infrastructure.TextVectorizer):
    def __init__(self, settings: Settings, cache: RedisCache):
        tv = settings.external.vectorizer
        super().__init__(model=tv.model, base_url=tv.base_url, api_key=tv.api_key, cache=cache)


class RedisClientWrapper(infrastructure.RedisClient):
    def __init__(self, settings: Settings):
        redis = settings.external.redis
        super().__init__(host=redis.host, port=redis.port, db=redis.database, password=redis.password)


class RetrieverServiceWrapper(service_layer.RetrieverService):
    def __init__(
        self,
        settings: Settings,
        uow: service_layer.AUnitOfWork,
        vectorizer: infrastructure.ATextVectorizer,
        redis: infrastructure.ARedisClient,
    ):
        super().__init__(cache_ttl=settings.internal.retriever.cache_ttl, uow=uow, vectorizer=vectorizer, redis=redis)


class RoutesServiceWrapper(service_layer.RoutesService):
    def __init__(
        self,
        settings: Settings,
        uow: service_layer.AUnitOfWork,
        summarizer: infrastructure.ATextSummarizer,
        retriever: service_layer.ARetrieverService,
        documents_service: service_layer.ADocumentsService,
        agents_service: service_layer.A_AgentsService,
        candidate_evaluator: service_layer.ACandidateEvaluator,
    ):
        router = settings.internal.router
        super().__init__(
            retriever_limit=router.retriever_limit,
            retriever_soft_limit_multiplier=router.retriever_soft_limit_multiplier,
            retriever_score_threshold=router.retriever_score_threshold,
            retriever_distance_metric=router.retriever_distance_metric,
            retriever_aggregation_method=router.retriever_aggregation_method,
            candidate_score_threshold=router.candidate_score_threshold,
            uow=uow,
            summarizer=summarizer,
            retriever=retriever,
            documents_service=documents_service,
            agents_service=agents_service,
            candidate_evaluator=candidate_evaluator,
        )


class AnalyticsServiceWrapper(service_layer.AnalyticsService):
    def __init__(
        self,
        settings: Settings,
        uow: service_layer.AUnitOfWork,
        redis: infrastructure.ARedisClient,
    ):
        analytics = settings.internal.analytics
        super().__init__(
            uow=uow,
            redis=redis,
            overview_cache_ttl=analytics.overview_cache_ttl,
            routes_summary_cache_ttl=analytics.routes_summary_cache_ttl,
            forwarded_summary_cache_ttl=analytics.forwarded_summary_cache_ttl,
            default_bucket_limit=analytics.default_bucket_limit,
        )


class BasicDocumentCleanerWrapper(BasicDocumentCleaner):
    def __init__(self, settings: Settings):
        super().__init__(language=settings.internal.segmenter.language)


class RabbitMQWrapper(infrastructure.RabbitMQ):
    def __init__(self, settings: Settings):
        super().__init__(settings.external.rabbitmq.url)  # type: ignore[arg-type]
