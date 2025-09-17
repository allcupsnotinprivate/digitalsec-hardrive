import abc
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.elements import literal
from sqlalchemy.sql.expression import case, select, text
from sqlalchemy.sql.functions import func

from app.models import (
    Agent,
    Document,
    Forwarded,
    ForwardedBucketRow,
    ForwardedOverviewRow,
    ProcessStatus,
    Route,
    RouteBucketRow,
    RoutesOverviewRow,
)
from app.repositories import ARepository


class A_AnalyticsRepository(ARepository[None, None], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, None)  # type: ignore[arg-type]

    @abc.abstractmethod
    async def get_totals(self) -> dict[str, int]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_routes_overview(self) -> RoutesOverviewRow:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_route_buckets(
        self, *, bucket_size: timedelta, bucket_limit: int, now: datetime | None = None
    ) -> Sequence[RouteBucketRow]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_forwarded_overview(self) -> ForwardedOverviewRow:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_forwarded_buckets(
        self, *, bucket_size: timedelta, bucket_limit: int, now: datetime | None = None
    ) -> Sequence[ForwardedBucketRow]:
        raise NotImplementedError


class AnalyticsRepository(A_AnalyticsRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_totals(self) -> dict[str, int]:
        documents_count = select(func.count(Document.id)).scalar_subquery()
        routes_count = select(func.count(Route.id)).scalar_subquery()
        agents_count = select(func.count(Agent.id)).scalar_subquery()

        stmt = select(
            documents_count.label("documents_total"),
            agents_count.label("agents_total"),
            routes_count.label("routes_total"),
        )

        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "documents_total": int(row.documents_total),
            "agents_total": int(row.agents_total),
            "routes_total": int(row.routes_total),
        }

    async def get_routes_overview(self) -> RoutesOverviewRow:
        duration_seconds = func.extract("epoch", Route.completed_at - Route.started_at)
        queue_seconds = func.extract("epoch", Route.started_at - Route.created_at)
        in_progress_age = func.extract("epoch", func.now() - Route.started_at)
        pending_age = func.extract("epoch", func.now() - Route.created_at)

        stmt = select(
            func.count(Route.id),
            func.count(Route.id).filter(Route.status == ProcessStatus.PENDING),
            func.count(Route.id).filter(Route.status == ProcessStatus.IN_PROGRESS),
            func.count(Route.id).filter(Route.status == ProcessStatus.COMPLETED),
            func.count(Route.id).filter(Route.status == ProcessStatus.FAILED),
            func.count(Route.id).filter(Route.status == ProcessStatus.TIMEOUT),
            func.count(Route.id)
            .filter(Route.status == ProcessStatus.COMPLETED)
            .filter(Route.completed_at >= func.now() - text("interval '24 hours'")),
            func.avg(case((Route.status == ProcessStatus.COMPLETED, duration_seconds), else_=None)),
            func.percentile_disc(0.95).within_group(duration_seconds).filter(Route.status == ProcessStatus.COMPLETED),
            func.avg(case((Route.started_at.is_not(None), queue_seconds), else_=None)),
            func.percentile_disc(0.95).within_group(queue_seconds).filter(Route.started_at.is_not(None)),
            func.avg(case((Route.status == ProcessStatus.IN_PROGRESS, in_progress_age), else_=None)),
            func.avg(case((Route.status == ProcessStatus.PENDING, pending_age), else_=None)),
        )

        result = await self.session.execute(stmt)
        (
            total,
            pending,
            in_progress,
            completed,
            failed,
            timeout,
            completed_last_24h,
            avg_completion,
            p95_completion,
            avg_queue,
            p95_queue,
            in_progress_avg_age,
            pending_avg_age,
        ) = result.one()

        return RoutesOverviewRow(
            total=int(total or 0),
            pending=int(pending or 0),
            in_progress=int(in_progress or 0),
            completed=int(completed or 0),
            failed=int(failed or 0),
            timeout=int(timeout or 0),
            completed_last_24h=int(completed_last_24h or 0),
            avg_completion_seconds=self._as_float(avg_completion),
            p95_completion_seconds=self._as_float(p95_completion),
            avg_queue_seconds=self._as_float(avg_queue),
            p95_queue_seconds=self._as_float(p95_queue),
            in_progress_avg_age_seconds=self._as_float(in_progress_avg_age),
            pending_avg_age_seconds=self._as_float(pending_avg_age),
        )

    async def get_route_buckets(
        self, *, bucket_size: timedelta, bucket_limit: int, now: datetime | None = None
    ) -> Sequence[RouteBucketRow]:
        if bucket_limit <= 0:
            return []

        now = now or datetime.now(timezone.utc)
        step_seconds = int(bucket_size.total_seconds())
        if step_seconds <= 0:
            return []

        end_time = now.replace(microsecond=0)
        start_time = end_time - bucket_size * (bucket_limit - 1)

        series_cte = select(
            func.generate_series(
                literal(start_time),
                literal(end_time),
                text(f"interval '{step_seconds} seconds'"),
            ).label("bucket_start"),
        ).cte("time_buckets")

        duration_seconds = func.extract("epoch", Route.completed_at - Route.started_at)
        queue_seconds = func.extract("epoch", Route.started_at - Route.created_at)

        join_condition = (Route.created_at >= series_cte.c.bucket_start) & (
            Route.created_at < series_cte.c.bucket_start + text(f"interval '{step_seconds} seconds'")
        )

        stmt = (
            select(
                series_cte.c.bucket_start,
                func.count(Route.id),
                func.count(Route.id).filter(Route.status == ProcessStatus.COMPLETED),
                func.count(Route.id).filter(Route.status == ProcessStatus.IN_PROGRESS),
                func.count(Route.id).filter(Route.status == ProcessStatus.PENDING),
                func.count(Route.id).filter(Route.status == ProcessStatus.FAILED),
                func.count(Route.id).filter(Route.status == ProcessStatus.TIMEOUT),
                func.avg(case((Route.status == ProcessStatus.COMPLETED, duration_seconds), else_=None)),
                func.avg(case((Route.started_at.is_not(None), queue_seconds), else_=None)),
            )
            .select_from(series_cte)
            .join(Route, join_condition, isouter=True)
            .group_by(series_cte.c.bucket_start)
            .order_by(series_cte.c.bucket_start)
        )

        result = await self.session.execute(stmt)
        rows = []
        for (
            bucket_start,
            total,
            completed,
            in_progress,
            pending,
            failed,
            timeout,
            avg_completion,
            avg_queue,
        ) in result.all():
            rows.append(
                RouteBucketRow(
                    bucket_start=bucket_start,
                    total=int(total or 0),
                    completed=int(completed or 0),
                    in_progress=int(in_progress or 0),
                    pending=int(pending or 0),
                    failed=int(failed or 0),
                    timeout=int(timeout or 0),
                    avg_completion_seconds=self._as_float(avg_completion),
                    avg_queue_seconds=self._as_float(avg_queue),
                )
            )
        return rows

    async def get_forwarded_overview(self) -> ForwardedOverviewRow:
        stmt = select(
            func.count(Forwarded.id),
            func.count(Forwarded.id).filter(Forwarded.is_valid.is_(None)),
            func.count(Forwarded.id).filter(Forwarded.is_valid.is_(True)),
            func.count(Forwarded.id).filter(Forwarded.is_valid.is_(False)),
            func.count(func.distinct(Forwarded.route_id)),
            func.count(func.distinct(Forwarded.route_id)).filter(Forwarded.is_valid.is_(None)),
            func.count(func.distinct(Forwarded.route_id)).filter(Forwarded.is_valid.is_(False)),
            func.count(func.distinct(Forwarded.recipient_id)),
            func.count(func.distinct(Forwarded.sender_id)),
            func.avg(Forwarded.score),
            func.avg(case((Forwarded.is_valid.is_(None), Forwarded.score), else_=None)),
            func.avg(case((Forwarded.is_valid.is_(True), Forwarded.score), else_=None)),
            func.avg(case((Forwarded.is_valid.is_(False), Forwarded.score), else_=None)),
            func.min(Forwarded.created_at),
            func.max(Forwarded.created_at),
        ).where(Forwarded.route_id.is_not(None))

        result = await self.session.execute(stmt)
        (
            total_predictions,
            manual_pending,
            auto_approved,
            auto_rejected,
            routes_with_predictions,
            routes_manual_pending,
            routes_with_rejections,
            distinct_recipients,
            distinct_senders,
            avg_score,
            manual_avg_score,
            accepted_avg_score,
            rejected_avg_score,
            first_forwarded_at,
            last_forwarded_at,
        ) = result.one()

        return ForwardedOverviewRow(
            total_predictions=int(total_predictions or 0),
            manual_pending=int(manual_pending or 0),
            auto_approved=int(auto_approved or 0),
            auto_rejected=int(auto_rejected or 0),
            routes_with_predictions=int(routes_with_predictions or 0),
            routes_manual_pending=int(routes_manual_pending or 0),
            routes_with_rejections=int(routes_with_rejections or 0),
            distinct_recipients=int(distinct_recipients or 0),
            distinct_senders=int(distinct_senders or 0),
            avg_score=self._as_float(avg_score),
            manual_avg_score=self._as_float(manual_avg_score),
            accepted_avg_score=self._as_float(accepted_avg_score),
            rejected_avg_score=self._as_float(rejected_avg_score),
            first_forwarded_at=first_forwarded_at,
            last_forwarded_at=last_forwarded_at,
        )

    async def get_forwarded_buckets(
        self, *, bucket_size: timedelta, bucket_limit: int, now: datetime | None = None
    ) -> Sequence[ForwardedBucketRow]:
        if bucket_limit <= 0:
            return []

        now = now or datetime.now(timezone.utc)
        step_seconds = int(bucket_size.total_seconds())
        if step_seconds <= 0:
            return []

        end_time = now.replace(microsecond=0)
        start_time = end_time - bucket_size * (bucket_limit - 1)

        series_cte = select(
            func.generate_series(
                literal(start_time),
                literal(end_time),
                text(f"interval '{step_seconds} seconds'"),
            ).label("bucket_start"),
        ).cte("forwarded_time_buckets")

        join_condition = (Forwarded.created_at >= series_cte.c.bucket_start) & (
            Forwarded.created_at < series_cte.c.bucket_start + text(f"interval '{step_seconds} seconds'")
        )

        stmt = (
            select(
                series_cte.c.bucket_start,
                func.count(Forwarded.id),
                func.count(Forwarded.id).filter(Forwarded.is_valid.is_(None)),
                func.count(Forwarded.id).filter(Forwarded.is_valid.is_(True)),
                func.count(Forwarded.id).filter(Forwarded.is_valid.is_(False)),
                func.avg(Forwarded.score),
            )
            .select_from(series_cte)
            .join(Forwarded, join_condition & Forwarded.route_id.is_not(None), isouter=True)
            .group_by(series_cte.c.bucket_start)
            .order_by(series_cte.c.bucket_start)
        )

        result = await self.session.execute(stmt)
        rows: list[ForwardedBucketRow] = []
        for (
            bucket_start,
            total,
            manual_pending,
            auto_approved,
            auto_rejected,
            avg_score,
        ) in result.all():
            rows.append(
                ForwardedBucketRow(
                    bucket_start=bucket_start,
                    total=int(total or 0),
                    manual_pending=int(manual_pending or 0),
                    auto_approved=int(auto_approved or 0),
                    auto_rejected=int(auto_rejected or 0),
                    avg_score=self._as_float(avg_score),
                )
            )

        return rows

    @staticmethod
    def _as_float(value: Decimal | float | None) -> float | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
