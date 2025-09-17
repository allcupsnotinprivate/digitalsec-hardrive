import abc
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, TypeVar

from app.infrastructure import ARedisClient
from app.models import (
    AnalyticsOverview,
    AnalyticsTimeWindow,
    ForwardedBucket,
    ForwardedBucketRow,
    ForwardedOverview,
    ForwardedOverviewRow,
    ForwardedSummary,
    InventorySummary,
    RouteBucket,
    RouteBucketRow,
    RoutesOverview,
    RoutesOverviewRow,
    RoutesSummary,
)

from .aClasses import AService
from .uow import AUnitOfWork

T = TypeVar("T")


class A_AnalyticsService(AService, abc.ABC):
    @abc.abstractmethod
    async def get_overview(self) -> AnalyticsOverview:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_routes_summary(
        self, *, window: AnalyticsTimeWindow, bucket_limit: int | None = None
    ) -> RoutesSummary:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_forwarded_summary(
        self, *, window: AnalyticsTimeWindow, bucket_limit: int | None = None
    ) -> ForwardedSummary:
        raise NotImplementedError


class AnalyticsService(A_AnalyticsService):
    def __init__(
        self,
        *,
        uow: AUnitOfWork,
        redis: ARedisClient,
        overview_cache_ttl: int,
        routes_summary_cache_ttl: int,
        forwarded_summary_cache_ttl: int,
        default_bucket_limit: int,
    ) -> None:
        self.uow = uow
        self.redis = redis
        self.overview_cache_ttl = overview_cache_ttl
        self.routes_summary_cache_ttl = routes_summary_cache_ttl
        self.forwarded_summary_cache_ttl = forwarded_summary_cache_ttl
        self.default_bucket_limit = default_bucket_limit

    async def get_overview(self) -> AnalyticsOverview:
        cache_key = "analytics:overview:v1"
        cached = await self._get_cached(cache_key, _dict_to_analytics_overview)
        if cached is not None:
            return cached

        async with self.uow as uow_ctx:
            totals = await uow_ctx.analytics.get_totals()
            routes_overview_row = await uow_ctx.analytics.get_routes_overview()
            forwarded_overview_row = await uow_ctx.analytics.get_forwarded_overview()

        inventory = InventorySummary(**totals)
        routes_overview = _build_routes_overview(routes_overview_row)
        forwarded_overview = _build_forwarded_overview(forwarded_overview_row, routes_total=inventory.routes_total)

        overview = AnalyticsOverview(inventory=inventory, routes=routes_overview, forwarded=forwarded_overview)

        await self._set_cached(
            cache_key,
            overview,
            _analytics_overview_to_dict,
            ttl=self.overview_cache_ttl,
        )
        return overview

    async def get_routes_summary(
        self, *, window: AnalyticsTimeWindow, bucket_limit: int | None = None
    ) -> RoutesSummary:
        limit = bucket_limit or self.default_bucket_limit
        cache_key = f"analytics:routes:summary:{window.value}:{limit}"
        cached = await self._get_cached(cache_key, _dict_to_routes_summary)
        if cached is not None:
            return cached

        async with self.uow as uow_ctx:
            overview_row = await uow_ctx.analytics.get_routes_overview()
            bucket_rows = await uow_ctx.analytics.get_route_buckets(bucket_size=window.delta, bucket_limit=limit)

        overview = _build_routes_overview(overview_row)
        buckets = [_build_route_bucket(row, window.delta) for row in bucket_rows]
        summary = RoutesSummary(
            window=window,
            bucket_size_seconds=int(window.delta.total_seconds()),
            bucket_limit=limit,
            overview=overview,
            buckets=buckets,
        )

        await self._set_cached(
            cache_key,
            summary,
            _routes_summary_to_dict,
            ttl=self.routes_summary_cache_ttl,
        )
        return summary

    async def get_forwarded_summary(
        self, *, window: AnalyticsTimeWindow, bucket_limit: int | None = None
    ) -> ForwardedSummary:
        limit = bucket_limit or self.default_bucket_limit
        cache_key = f"analytics:forwarded:summary:{window.value}:{limit}"
        cached = await self._get_cached(cache_key, _dict_to_forwarded_summary)
        if cached is not None:
            return cached

        async with self.uow as uow_ctx:
            overview_row = await uow_ctx.analytics.get_forwarded_overview()
            bucket_rows = await uow_ctx.analytics.get_forwarded_buckets(bucket_size=window.delta, bucket_limit=limit)
            totals = await uow_ctx.analytics.get_totals()

        overview = _build_forwarded_overview(overview_row, routes_total=totals["routes_total"])
        buckets = [_build_forwarded_bucket(row, window.delta) for row in bucket_rows]
        summary = ForwardedSummary(
            window=window,
            bucket_size_seconds=int(window.delta.total_seconds()),
            bucket_limit=limit,
            overview=overview,
            buckets=buckets,
        )

        await self._set_cached(
            cache_key,
            summary,
            _forwarded_summary_to_dict,
            ttl=self.forwarded_summary_cache_ttl,
        )
        return summary

    async def _get_cached(self, key: str, parser: Callable[[dict[str, Any]], T]) -> T | None:
        try:
            cached = await self.redis.get(key)
        except Exception:
            return None
        if not cached:
            return None
        try:
            payload = json.loads(cached if isinstance(cached, str) else cached.decode("utf-8"))
        except Exception:
            return None
        try:
            return parser(payload)
        except Exception:
            return None

    async def _set_cached(
        self,
        key: str,
        value: T,
        serializer: Callable[[T], dict[str, Any]],
        *,
        ttl: int,
    ) -> None:
        if ttl <= 0:
            return
        payload = json.dumps(serializer(value), default=_serialize_value)
        try:
            await self.redis.set(key, payload, ex=ttl)
        except Exception:
            return


def _build_routes_overview(row: RoutesOverviewRow) -> RoutesOverview:
    failure_total = row.failed + row.timeout
    failure_rate = (failure_total / row.total) if row.total else None
    throughput = (row.completed_last_24h / 24) if row.completed_last_24h else None
    return RoutesOverview(
        total=row.total,
        pending=row.pending,
        in_progress=row.in_progress,
        completed=row.completed,
        failed=row.failed,
        timeout=row.timeout,
        completed_last_24h=row.completed_last_24h,
        average_completion_seconds=row.avg_completion_seconds,
        completion_p95_seconds=row.p95_completion_seconds,
        average_queue_seconds=row.avg_queue_seconds,
        queue_p95_seconds=row.p95_queue_seconds,
        in_progress_average_age_seconds=row.in_progress_avg_age_seconds,
        pending_average_age_seconds=row.pending_avg_age_seconds,
        failure_rate=failure_rate,
        throughput_per_hour_last_24h=throughput,
    )


def _build_route_bucket(row: RouteBucketRow, delta: timedelta) -> RouteBucket:
    return RouteBucket(
        bucket_start=row.bucket_start,
        bucket_end=row.bucket_start + delta,
        total=row.total,
        completed=row.completed,
        in_progress=row.in_progress,
        pending=row.pending,
        failed=row.failed,
        timeout=row.timeout,
        average_completion_seconds=row.avg_completion_seconds,
        average_queue_seconds=row.avg_queue_seconds,
    )


def _build_forwarded_overview(row: ForwardedOverviewRow, *, routes_total: int) -> ForwardedOverview:
    auto_volume = row.auto_approved + row.auto_rejected
    avg_predictions_per_route = (
        row.total_predictions / row.routes_with_predictions if row.routes_with_predictions else None
    )
    auto_resolution_ratio = (auto_volume / row.total_predictions) if row.total_predictions else None
    auto_acceptance_rate = row.auto_approved / auto_volume if auto_volume else None
    manual_backlog_ratio = row.manual_pending / row.total_predictions if row.total_predictions else None
    routes_auto_resolved = max(row.routes_with_predictions - row.routes_manual_pending, 0)
    routes_coverage_ratio = row.routes_with_predictions / routes_total if routes_total else None
    return ForwardedOverview(
        total_predictions=row.total_predictions,
        manual_pending=row.manual_pending,
        auto_approved=row.auto_approved,
        auto_rejected=row.auto_rejected,
        routes_with_predictions=row.routes_with_predictions,
        routes_manual_pending=row.routes_manual_pending,
        routes_auto_resolved=routes_auto_resolved,
        routes_with_rejections=row.routes_with_rejections,
        average_predictions_per_route=avg_predictions_per_route,
        auto_resolution_ratio=auto_resolution_ratio,
        auto_acceptance_rate=auto_acceptance_rate,
        manual_backlog_ratio=manual_backlog_ratio,
        routes_coverage_ratio=routes_coverage_ratio,
        distinct_recipients=row.distinct_recipients,
        distinct_senders=row.distinct_senders,
        average_score=row.avg_score,
        manual_average_score=row.manual_avg_score,
        accepted_average_score=row.accepted_avg_score,
        rejected_average_score=row.rejected_avg_score,
        first_forwarded_at=row.first_forwarded_at,
        last_forwarded_at=row.last_forwarded_at,
    )


def _build_forwarded_bucket(row: ForwardedBucketRow, delta: timedelta) -> ForwardedBucket:
    return ForwardedBucket(
        bucket_start=row.bucket_start,
        bucket_end=row.bucket_start + delta,
        total=row.total,
        manual_pending=row.manual_pending,
        auto_approved=row.auto_approved,
        auto_rejected=row.auto_rejected,
        average_score=row.avg_score,
    )


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _analytics_overview_to_dict(value: AnalyticsOverview) -> dict[str, Any]:
    return asdict(value)


def _routes_summary_to_dict(value: RoutesSummary) -> dict[str, Any]:
    payload = asdict(value)
    payload["window"] = value.window.value
    return payload


def _forwarded_summary_to_dict(value: ForwardedSummary) -> dict[str, Any]:
    payload = asdict(value)
    payload["window"] = value.window.value
    return payload


def _dict_to_analytics_overview(data: dict[str, Any]) -> AnalyticsOverview:
    return AnalyticsOverview(
        inventory=_dict_to_inventory_summary(data["inventory"]),
        routes=_dict_to_routes_overview(data["routes"]),
        forwarded=_dict_to_forwarded_overview(data["forwarded"]),
    )


def _dict_to_routes_summary(data: dict[str, Any]) -> RoutesSummary:
    return RoutesSummary(
        window=AnalyticsTimeWindow(data["window"]),
        bucket_size_seconds=int(data["bucket_size_seconds"]),
        bucket_limit=int(data["bucket_limit"]),
        overview=_dict_to_routes_overview(data["overview"]),
        buckets=[_dict_to_route_bucket(item) for item in data.get("buckets", [])],
    )


def _dict_to_forwarded_summary(data: dict[str, Any]) -> ForwardedSummary:
    return ForwardedSummary(
        window=AnalyticsTimeWindow(data["window"]),
        bucket_size_seconds=int(data["bucket_size_seconds"]),
        bucket_limit=int(data["bucket_limit"]),
        overview=_dict_to_forwarded_overview(data["overview"]),
        buckets=[_dict_to_forwarded_bucket(item) for item in data.get("buckets", [])],
    )


def _dict_to_inventory_summary(data: dict[str, Any]) -> InventorySummary:
    return InventorySummary(
        documents_total=int(data["documents_total"]),
        agents_total=int(data["agents_total"]),
        routes_total=int(data["routes_total"]),
    )


def _dict_to_routes_overview(data: dict[str, Any]) -> RoutesOverview:
    return RoutesOverview(
        total=int(data["total"]),
        pending=int(data["pending"]),
        in_progress=int(data["in_progress"]),
        completed=int(data["completed"]),
        failed=int(data["failed"]),
        timeout=int(data["timeout"]),
        completed_last_24h=int(data["completed_last_24h"]),
        average_completion_seconds=_as_float(data.get("average_completion_seconds")),
        completion_p95_seconds=_as_float(data.get("completion_p95_seconds")),
        average_queue_seconds=_as_float(data.get("average_queue_seconds")),
        queue_p95_seconds=_as_float(data.get("queue_p95_seconds")),
        in_progress_average_age_seconds=_as_float(data.get("in_progress_average_age_seconds")),
        pending_average_age_seconds=_as_float(data.get("pending_average_age_seconds")),
        failure_rate=_as_float(data.get("failure_rate")),
        throughput_per_hour_last_24h=_as_float(data.get("throughput_per_hour_last_24h")),
    )


def _dict_to_route_bucket(data: dict[str, Any]) -> RouteBucket:
    return RouteBucket(
        bucket_start=_parse_datetime(data["bucket_start"]),  # type: ignore[arg-type]
        bucket_end=_parse_datetime(data["bucket_end"]),  # type: ignore[arg-type]
        total=int(data["total"]),
        completed=int(data["completed"]),
        in_progress=int(data["in_progress"]),
        pending=int(data["pending"]),
        failed=int(data["failed"]),
        timeout=int(data["timeout"]),
        average_completion_seconds=_as_float(data.get("average_completion_seconds")),
        average_queue_seconds=_as_float(data.get("average_queue_seconds")),
    )


def _dict_to_forwarded_overview(data: dict[str, Any]) -> ForwardedOverview:
    return ForwardedOverview(
        total_predictions=int(data["total_predictions"]),
        manual_pending=int(data["manual_pending"]),
        auto_approved=int(data["auto_approved"]),
        auto_rejected=int(data["auto_rejected"]),
        routes_with_predictions=int(data["routes_with_predictions"]),
        routes_manual_pending=int(data["routes_manual_pending"]),
        routes_auto_resolved=int(data["routes_auto_resolved"]),
        routes_with_rejections=int(data["routes_with_rejections"]),
        average_predictions_per_route=_as_float(data.get("average_predictions_per_route")),
        auto_resolution_ratio=_as_float(data.get("auto_resolution_ratio")),
        auto_acceptance_rate=_as_float(data.get("auto_acceptance_rate")),
        manual_backlog_ratio=_as_float(data.get("manual_backlog_ratio")),
        routes_coverage_ratio=_as_float(data.get("routes_coverage_ratio")),
        distinct_recipients=int(data["distinct_recipients"]),
        distinct_senders=int(data["distinct_senders"]),
        average_score=_as_float(data.get("average_score")),
        manual_average_score=_as_float(data.get("manual_average_score")),
        accepted_average_score=_as_float(data.get("accepted_average_score")),
        rejected_average_score=_as_float(data.get("rejected_average_score")),
        first_forwarded_at=_parse_datetime(data.get("first_forwarded_at")),
        last_forwarded_at=_parse_datetime(data.get("last_forwarded_at")),
    )


def _dict_to_forwarded_bucket(data: dict[str, Any]) -> ForwardedBucket:
    return ForwardedBucket(
        bucket_start=_parse_datetime(data["bucket_start"]),  # type: ignore[arg-type]
        bucket_end=_parse_datetime(data["bucket_end"]),  # type: ignore[arg-type]
        total=int(data["total"]),
        manual_pending=int(data["manual_pending"]),
        auto_approved=int(data["auto_approved"]),
        auto_rejected=int(data["auto_rejected"]),
        average_score=_as_float(data.get("average_score")),
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
