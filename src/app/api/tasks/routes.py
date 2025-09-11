from datetime import timedelta

from aioinject import Injected, inject
from loguru import logger
from sqlalchemy import select

from app.models import ProcessStatus, Route
from app.service_layer import AUnitOfWork
from app.utils.timestamps import now_with_tz


@inject
async def check_stale_investigations(
        investigation_timeout: float,
        uow: Injected[AUnitOfWork]
) -> None:
    async with uow as uow_ctx:
        stmt = select(Route.id).where(
            Route.status == ProcessStatus.IN_PROGRESS,
            Route.started_at < now_with_tz() - timedelta(seconds=investigation_timeout),
        )
        raw = await uow_ctx.session.execute(stmt)
        result = raw.all()
        logger.info("Handling investigation cancellations due to timeout", count=len(result))
        for (rid,) in result:
            await uow_ctx.routes.update_status(rid, ProcessStatus.TIMEOUT)
