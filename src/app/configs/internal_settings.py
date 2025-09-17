from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app import LOGS_DIR
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
    retriever_score_threshold: float | None = Field(default=None, ge=0.0)
    retriever_distance_metric: Literal["cosine", "l2", "inner"] = Field(default="cosine")
    retriever_aggregation_method: Literal["mean", "max", "top_k_mean"] = Field(default="max")
    investigation_timeout: float = Field(default=300, gt=5)
    candidate_score_threshold: float = Field(default=0.6, ge=0.0, lt=1.0)
    investigation_parallelism: int = Field(default=4, ge=1)


class DocumentsAdmissionSettings(BaseModel):
    loading_parallelism: int = Field(default=2, ge=1)


class AnalyticsSettings(BaseModel):
    overview_cache_ttl: int = Field(default=60, ge=0)
    routes_summary_cache_ttl: int = Field(default=120, ge=0)
    forwarded_summary_cache_ttl: int = Field(default=120, ge=0)
    default_bucket_limit: int = Field(default=24, ge=1, le=336)


class LogsSettings(BaseModel):
    enable: bool = Field(default=True)
    level: LogLevel = Field(default=LogLevel.INFO)
    file: Path = Field(default=LOGS_DIR / "journal.log")

    @field_validator("level", mode="before")
    def validate_level_field(cls, v: str | int) -> LogLevel:
        return LogLevel(int(v))


class InternalSettings(BaseModel):
    log: LogsSettings = Field(default_factory=LogsSettings)
    segmenter: SegmenterSettings = Field(default_factory=SegmenterSettings)
    retriever: RetrieverSettings = Field(default_factory=RetrieverSettings)
    router: RouterSettings = Field(default_factory=RouterSettings)
    documents: DocumentsAdmissionSettings = Field(default_factory=DocumentsAdmissionSettings)
    analytics: AnalyticsSettings = Field(default_factory=AnalyticsSettings)
