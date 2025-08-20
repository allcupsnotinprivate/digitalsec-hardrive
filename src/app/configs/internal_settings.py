from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.logs import LogLevel


class SegmenterSettings(BaseModel):
    max_chunk_size: int = Field(default=1800)
    min_chunk_size: int = Field(default=100)
    similarity_threshold: float = Field(default=0.5)
    language: Literal["russian"] = Field(default="russian")


class RetrieverSettings(BaseModel):
    cache_ttl: int = Field(default=900)


class RouterSettings(BaseModel):
    retriever_limit: int = Field(default=20)
    retriever_soft_limit_multiplier: float = Field(default=5.0)
    investigation_timeout: float = Field(default=300, gt=5)


class LogsSettings(BaseModel):
    enable: bool = Field(default=True)
    level: LogLevel = Field(default=LogLevel.INFO)

    @field_validator("level", mode="before")
    def validate_level_field(cls, v: str | int) -> LogLevel:
        return LogLevel(int(v))


class InternalSettings(BaseModel):
    log: LogsSettings = Field(default_factory=LogsSettings)
    segmenter: SegmenterSettings = Field(default_factory=SegmenterSettings)
    retriever: RetrieverSettings = Field(default_factory=RetrieverSettings)
    router: RouterSettings = Field(default_factory=RouterSettings)
