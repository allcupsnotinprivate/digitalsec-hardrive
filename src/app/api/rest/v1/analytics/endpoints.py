from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Depends, Query

from app.models import AnalyticsTimeWindow
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
    analytics_service: Injected[A_AnalyticsService] = Depends(),
) -> AnalyticsOverviewResponse:
    overview = await analytics_service.get_overview()
    return AnalyticsOverviewResponse.model_validate(overview)


@router.get("/routes/summary", response_model=RoutesSummaryResponse)
@inject
async def get_routes_summary(
    window: AnalyticsTimeWindow = Query(default=AnalyticsTimeWindow.HOUR),
    bucket_limit: int | None = Query(default=None, ge=1, le=336),
    analytics_service: Injected[A_AnalyticsService] = Depends(),
) -> RoutesSummaryResponse:
    summary = await analytics_service.get_routes_summary(window=window, bucket_limit=bucket_limit)
    return RoutesSummaryResponse.model_validate(summary)


@router.get("/routes/predictions", response_model=ForwardedSummaryResponse)
@inject
async def get_forwarded_summary(
    window: AnalyticsTimeWindow = Query(default=AnalyticsTimeWindow.HOUR),
    bucket_limit: int | None = Query(default=None, ge=1, le=336),
    analytics_service: Injected[A_AnalyticsService] = Depends(),
) -> ForwardedSummaryResponse:
    summary = await analytics_service.get_forwarded_summary(window=window, bucket_limit=bucket_limit)
    return ForwardedSummaryResponse.model_validate(summary)
