from typing import Literal

from pydantic import BaseModel, Field, computed_field


class SummarizerSettings(BaseModel):
    model: str = Field(default="gpt-4o-mini")


class VectorizerSettings(BaseModel):
    model: str = Field(default="openai/text-embedding-multilingual-e5-large-instruct")
    base_url: str | None = Field(default="http://localhost:1234")
    api_key: str = Field(default="...")


class PostgresSettings(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5432)
    database: str = Field(default="digitalsec_router")
    user: str = Field(default="digitalsec_username")
    password: str = Field(default="digitalsec_password")
    automigrate: bool = Field(default=True)


class RedisSettings(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=6379)
    database: int = Field(default=0)
    password: str = Field(default="digitalsec_password")

    def url_with_pool_max_size(self, pool_max_size: int) -> str:
        return f"redis://:{self.password}@{self.host}:{self.port}/{self.database}?pool_max_size={pool_max_size}"


class RabbitMQSettings(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5672)
    user: str = Field(default="guest")
    password: str = Field(default="guest")

    @computed_field
    def url(self) -> str:
        domain = self.host if not self.host else f"{self.host}:{self.port}"
        return f"amqp://{self.user}:{self.password}@{domain}/"


class S3Settings(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int | None = Field(default=9000)
    region: str = Field(default="us-east-1")
    access_key: str = Field(default="digitalsec")
    secret_key: str = Field(default="digitalsec_password")
    bucket: str = Field(default="digitalsec-documents")
    use_ssl: bool = Field(default=False)
    scheme: Literal["http", "https"] = Field(default="http")

    @computed_field()
    def endpoint_url(self) -> str:
        url = f"{self.scheme}://{self.host}"
        if self.port:
            url += f":{self.port}"
        return url


class ExternalSettings(BaseModel):
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    summarizer: SummarizerSettings = Field(default_factory=SummarizerSettings)
    vectorizer: VectorizerSettings = Field(default_factory=VectorizerSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
