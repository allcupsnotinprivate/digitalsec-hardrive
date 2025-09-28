from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.models import AnalyticsTimeWindow
from app.utils.schemas import BaseAPISchema


class AnalyticsAPISchema(BaseAPISchema):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class InventorySummaryResponse(AnalyticsAPISchema):
    documents_total: int
    agents_total: int
    routes_total: int


class RoutesOverviewResponse(AnalyticsAPISchema):
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


class RouteBucketResponse(AnalyticsAPISchema):
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


class RoutesSummaryResponse(AnalyticsAPISchema):
    window: AnalyticsTimeWindow
    bucket_size_seconds: int
    bucket_limit: int
    overview: RoutesOverviewResponse
    buckets: list[RouteBucketResponse]


class ForwardedRecipientDistributionResponse(AnalyticsAPISchema):
    recipient_id: UUID | None = None
    recipient_name: str | None = None
    routes: int
    percentage: float


class ForwardedOverviewResponse(AnalyticsAPISchema):
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
    distinct_recipients: int
    distinct_senders: int
    average_score: float | None = None
    manual_average_score: float | None = None
    accepted_average_score: float | None = None
    rejected_average_score: float | None = None
    first_forwarded_at: datetime | None = None
    last_forwarded_at: datetime | None = None
    routes_distribution: list[ForwardedRecipientDistributionResponse] = Field(default_factory=list)


class ForwardedBucketResponse(AnalyticsAPISchema):
    bucket_start: datetime
    bucket_end: datetime
    total: int
    manual_pending: int
    auto_approved: int
    auto_rejected: int
    average_score: float | None = None


class ForwardedSummaryResponse(AnalyticsAPISchema):
    window: AnalyticsTimeWindow
    bucket_size_seconds: int
    bucket_limit: int
    overview: ForwardedOverviewResponse
    buckets: list[ForwardedBucketResponse]


class AnalyticsOverviewResponse(AnalyticsAPISchema):
    inventory: InventorySummaryResponse
    routes: RoutesOverviewResponse
    forwarded: ForwardedOverviewResponse
