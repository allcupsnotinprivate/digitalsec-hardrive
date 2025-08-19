from app import infrastructure, service_layer
from app.configs import Settings


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
    def __init__(self, settings: Settings, vectorizer: infrastructure.ATextVectorizer):
        sg = settings.internal.segmenter
        super().__init__(
            max_chunk_size=sg.max_chunk_size,
            min_chunk_size=sg.min_chunk_size,
            similarity_threshold=sg.similarity_threshold,
            language=sg.language,
            vectorizer=vectorizer,
        )


class TextSummarizerWrapper(infrastructure.TextSummarizer):
    def __init__(self, settings: Settings):
        ts = settings.external.summarizer
        super().__init__(model=ts.model)


class TextVectorizerWrapper(infrastructure.TextVectorizer):
    def __init__(self, settings: Settings):
        tv = settings.external.vectorizer
        super().__init__(model=tv.model)


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
    ):
        router = settings.internal.router
        super().__init__(
            retriever_limit=router.retriever_limit,
            retriever_soft_limit_multiplier=router.retriever_soft_limit_multiplier,
            uow=uow,
            summarizer=summarizer,
            retriever=retriever,
            documents_service=documents_service,
            agents_service=agents_service,
        )
