from datetime import datetime
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Depends, Query

from app.models import AnalyticsFilters, AnalyticsTimeWindow
from app.service_layer.analytics import A_AnalyticsService

from .schemas import (
    AnalyticsOverviewResponse,
    ForwardedSummaryResponse,
    RoutesSummaryResponse,
)

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverviewResponse)
@inject
async def get_overview(
    time_from: datetime | None = Query(default=None, alias="timeFrom"),
    time_to: datetime | None = Query(default=None, alias="timeTo"),
    sender_id: UUID | None = Query(default=None, alias="senderId"),
    recipient_id: UUID | None = Query(default=None, alias="recipientId"),
    analytics_service: Injected[A_AnalyticsService] = Depends(),
) -> AnalyticsOverviewResponse:
    filters = AnalyticsFilters(
        time_from=time_from,
        time_to=time_to,
        sender_id=sender_id,
        recipient_id=recipient_id,
    )
    overview = await analytics_service.get_overview(filters=filters)
    return AnalyticsOverviewResponse.model_validate(overview)


@router.get("/routes/summary", response_model=RoutesSummaryResponse)
@inject
async def get_routes_summary(
    window: AnalyticsTimeWindow = Query(default=AnalyticsTimeWindow.HOUR),
    bucket_limit: int | None = Query(default=None, ge=1, le=336),
    time_from: datetime | None = Query(default=None, alias="timeFrom"),
    time_to: datetime | None = Query(default=None, alias="timeTo"),
    sender_id: UUID | None = Query(default=None, alias="senderId"),
    recipient_id: UUID | None = Query(default=None, alias="recipientId"),
    analytics_service: Injected[A_AnalyticsService] = Depends(),
) -> RoutesSummaryResponse:
    filters = AnalyticsFilters(
        time_from=time_from,
        time_to=time_to,
        sender_id=sender_id,
        recipient_id=recipient_id,
    )
    summary = await analytics_service.get_routes_summary(
        window=window,
        bucket_limit=bucket_limit,
        filters=filters,
    )
    return RoutesSummaryResponse.model_validate(summary)


@router.get("/routes/predictions", response_model=ForwardedSummaryResponse)
@inject
async def get_forwarded_summary(
    window: AnalyticsTimeWindow = Query(default=AnalyticsTimeWindow.HOUR),
    bucket_limit: int | None = Query(default=None, ge=1, le=336),
    time_from: datetime | None = Query(default=None, alias="timeFrom"),
    time_to: datetime | None = Query(default=None, alias="timeTo"),
    sender_id: UUID | None = Query(default=None, alias="senderId"),
    recipient_id: UUID | None = Query(default=None, alias="recipientId"),
    analytics_service: Injected[A_AnalyticsService] = Depends(),
) -> ForwardedSummaryResponse:
    filters = AnalyticsFilters(
        time_from=time_from,
        time_to=time_to,
        sender_id=sender_id,
        recipient_id=recipient_id,
    )
    summary = await analytics_service.get_forwarded_summary(
        window=window,
        bucket_limit=bucket_limit,
        filters=filters,
    )
    return ForwardedSummaryResponse.model_validate(summary)
