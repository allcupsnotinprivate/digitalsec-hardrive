import uuid
from dataclasses import dataclass, field
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BOOLEAN, FLOAT, TIMESTAMP, VARCHAR, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import BYTEA, ENUM, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.utils.timestamps import now_with_tz

from .enums import AnalyticsTimeWindow, ProcessStatus

# ----- ORM Models -----

ProcessStatusT = ENUM(ProcessStatus, name="process_status", create_type=False)


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, insert_default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), insert_default=now_with_tz, nullable=False)


class Agent(Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(VARCHAR(124), nullable=False)
    description: Mapped[str | None] = mapped_column(VARCHAR(512), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, insert_default=True)
    is_default_recipient: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, insert_default=False)


class Document(Base):
    __tablename__ = "documents"

    name: Mapped[str] = mapped_column(VARCHAR(124), nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    content: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    hash: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id"), nullable=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Route(Base):
    __tablename__ = "routes"

    status: Mapped[ProcessStatus] = mapped_column(ProcessStatusT, nullable=False, insert_default=ProcessStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, insert_default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, insert_default=None)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)


class Forwarded(Base):
    __tablename__ = "forwarded"

    purpose: Mapped[str | None] = mapped_column(VARCHAR(52), nullable=True)
    is_valid: Mapped[bool | None] = mapped_column(BOOLEAN, nullable=True, insert_default=None)
    is_hidden: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, insert_default=False)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    route_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True)
    score: Mapped[float | None] = mapped_column(FLOAT, nullable=True)

    __table_args__ = (CheckConstraint("sender_id != recipient_id", name="ck_forwarded_sender_recipient_different"),)


# ----- Row Models -----


@dataclass(slots=True)
class RoutesOverviewRow:
    total: int
    pending: int
    in_progress: int
    completed: int
    failed: int
    timeout: int
    completed_last_24h: int
    avg_completion_seconds: float | None
    p95_completion_seconds: float | None
    avg_queue_seconds: float | None
    p95_queue_seconds: float | None
    in_progress_avg_age_seconds: float | None
    pending_avg_age_seconds: float | None


@dataclass(slots=True)
class RouteBucketRow:
    bucket_start: datetime
    total: int
    completed: int
    in_progress: int
    pending: int
    failed: int
    timeout: int
    avg_completion_seconds: float | None
    avg_queue_seconds: float | None


@dataclass(slots=True)
class ForwardedOverviewRow:
    total_predictions: int
    manual_pending: int
    auto_approved: int
    auto_rejected: int
    routes_with_predictions: int
    routes_manual_pending: int
    routes_with_rejections: int
    distinct_recipients: int
    distinct_senders: int
    avg_score: float | None
    manual_avg_score: float | None
    accepted_avg_score: float | None
    rejected_avg_score: float | None
    first_forwarded_at: datetime | None
    last_forwarded_at: datetime | None


@dataclass(slots=True)
class ForwardedBucketRow:
    bucket_start: datetime
    total: int
    manual_pending: int
    auto_approved: int
    auto_rejected: int
    avg_score: float | None


@dataclass(slots=True)
class InventorySummary:
    documents_total: int
    agents_total: int
    routes_total: int


@dataclass(slots=True)
class RoutesOverview:
    total: int
    pending: int
    in_progress: int
    completed: int
    failed: int
    timeout: int
    completed_last_24h: int
    average_completion_seconds: float | None = None
    completion_p95_seconds: float | None = None
    average_queue_seconds: float | None = None
    queue_p95_seconds: float | None = None
    in_progress_average_age_seconds: float | None = None
    pending_average_age_seconds: float | None = None
    failure_rate: float | None = None
    throughput_per_hour_last_24h: float | None = None


@dataclass(slots=True)
class RouteBucket:
    bucket_start: datetime
    bucket_end: datetime
    total: int
    completed: int
    in_progress: int
    pending: int
    failed: int
    timeout: int
    average_completion_seconds: float | None = None
    average_queue_seconds: float | None = None


@dataclass(slots=True)
class RoutesSummary:
    window: AnalyticsTimeWindow
    bucket_size_seconds: int
    bucket_limit: int
    overview: RoutesOverview
    buckets: list[RouteBucket]


@dataclass(slots=True)
class ForwardedOverview:
    total_predictions: int
    manual_pending: int
    auto_approved: int
    auto_rejected: int
    routes_with_predictions: int
    routes_manual_pending: int
    routes_auto_resolved: int
    routes_with_rejections: int
    average_predictions_per_route: float | None = None
    auto_resolution_ratio: float | None = None
    auto_acceptance_rate: float | None = None
    manual_backlog_ratio: float | None = None
    routes_coverage_ratio: float | None = None
    rejection_ratio: float | None = None
    distinct_recipients: int = 0
    distinct_senders: int = 0
    average_score: float | None = None
    manual_average_score: float | None = None
    accepted_average_score: float | None = None
    rejected_average_score: float | None = None
    first_forwarded_at: datetime | None = None
    last_forwarded_at: datetime | None = None
    routes_distribution: list["ForwardedRecipientDistribution"] = field(default_factory=list)


@dataclass(slots=True)
class ForwardedBucket:
    bucket_start: datetime
    bucket_end: datetime
    total: int
    manual_pending: int
    auto_approved: int
    auto_rejected: int
    average_score: float | None = None


@dataclass(slots=True)
class ForwardedSummary:
    window: AnalyticsTimeWindow
    bucket_size_seconds: int
    bucket_limit: int
    overview: ForwardedOverview
    buckets: list[ForwardedBucket]


@dataclass(slots=True)
class ForwardedRecipientDistributionRow:
    recipient_id: uuid.UUID | None
    recipient_name: str | None
    routes: int


@dataclass(slots=True)
class ForwardedRecipientDistribution:
    recipient_id: uuid.UUID | None
    recipient_name: str | None
    routes: int
    percentage: float


@dataclass(slots=True)
class AnalyticsFilters:
    time_from: datetime | None = None
    time_to: datetime | None = None
    sender_id: uuid.UUID | None = None
    recipient_id: uuid.UUID | None = None

    def is_empty(self) -> bool:
        return not any((self.time_from, self.time_to, self.sender_id, self.recipient_id))


@dataclass(slots=True)
class AnalyticsOverview:
    inventory: InventorySummary
    routes: RoutesOverview
    forwarded: ForwardedOverview
