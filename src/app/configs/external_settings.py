from pydantic import BaseModel, Field


class SummarizerSettings(BaseModel):
    model: str = Field(default="gpt-4o-mini")


class VectorizerSettings(BaseModel):
    model: str = Field(default="lm_studio/text-embedding-multilingual-e5-large-instruct")


class PostgresSettings(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5432)
    database: str = Field(default="digitalsec")
    user: str = Field(default="digitalsec_username")
    password: str = Field(default="digitalsec_password")
    automigrate: bool = Field(default=True)


class RedisSettings(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=6379)
    database: int = Field(default=0)
    password: str = Field(default="digitalsec_password")


class ExternalSettings(BaseModel):
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    summarizer: SummarizerSettings = Field(default_factory=SummarizerSettings)
    vectorizer: VectorizerSettings = Field(default_factory=VectorizerSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
