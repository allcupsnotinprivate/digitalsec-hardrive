import asyncio
from datetime import timedelta
from typing import Any
from uuid import UUID

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from loguru import logger
from sqlalchemy import select

from app.configs import Settings
from app.container import container
from app.models import ProcessStatus, Route
from app.service_layer import ARoutesService, AUnitOfWork
from app.utils.timestamps import now_with_tz

# NOTE: import is necessary for correct registration of celery
from app.worker import celery_app  # noqa: F401


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def investigate_route(
    self: Any,
    route_id: str,
    sender_id: str | None,
    allow_recovery: bool = False,
) -> None:
    async def _run() -> None:
        async with container.context() as ctx:
            routes_service = await ctx.resolve(ARoutesService)  # type: ignore[type-abstract]
            use_recovery = allow_recovery or self.request.retries > 0
            await routes_service.investigate(
                id=UUID(route_id),
                sender_id=UUID(sender_id) if sender_id else None,
                allow_recovery=use_recovery,
            )

    try:
        asyncio.run(_run())
    except SoftTimeLimitExceeded:
        logger.warning("Investigation timed out", route_id=route_id)
        asyncio.run(_mark_timeout(UUID(route_id)))
        raise


async def _mark_timeout(route_id: UUID) -> None:
    async with container.context() as ctx:
        uow = await ctx.resolve(AUnitOfWork)  # type: ignore[type-abstract]
        async with uow as uow_ctx:
            await uow_ctx.routes.update_status(route_id, ProcessStatus.TIMEOUT)


@shared_task
def check_stale_investigations() -> None:
    with container.sync_context() as ctx:
        settings: Settings = ctx.resolve(Settings)

    async def _run() -> None:
        timeout = settings.internal.router.investigation_timeout
        # TODO: statement to present as a method in the repository
        async with container.context() as ctx:
            uow = await ctx.resolve(AUnitOfWork)  # type: ignore[type-abstract]
            async with uow as uow_ctx:
                stmt = select(Route.id).where(
                    Route.status == ProcessStatus.IN_PROGRESS,
                    Route.started_at < now_with_tz() - timedelta(seconds=timeout),
                )
                result = await uow_ctx.session.execute(stmt)
                for (rid,) in result.all():
                    await uow_ctx.routes.update_status(rid, ProcessStatus.TIMEOUT)

    asyncio.run(_run())
