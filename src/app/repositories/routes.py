import abc
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

from app.models import ProcessStatus, Route
from app.repositories import ARepository
from app.utils.timestamps import now_with_tz


class ARoutesRepository(ARepository[Route, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Route)

    @abc.abstractmethod
    async def update_status(self, route_id: UUID, status: ProcessStatus) -> Route:
        raise NotImplementedError

    @abc.abstractmethod
    async def search(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        sender_id: UUID | None,
        status: ProcessStatus | None,
        started_from: datetime | None,
        started_to: datetime | None,
        completed_from: datetime | None,
        completed_to: datetime | None,
    ) -> tuple[list[Route], int]:
        raise NotImplementedError


class RoutesRepository(ARoutesRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def update_status(self, route_id: UUID, status: ProcessStatus) -> Route:
        stmt_update = update(self.model_class).where(self.model_class.id == route_id).values(status=status)

        if status == ProcessStatus.IN_PROGRESS:
            stmt_update = stmt_update.values(started_at=now_with_tz(), completed_at=None)
        elif status == ProcessStatus.PENDING:
            stmt_update = stmt_update.values(started_at=None, completed_at=None)
        elif status in (status.FAILED, status.COMPLETED, status.TIMEOUT):
            stmt_update = stmt_update.values(completed_at=now_with_tz())

        stmt_update = stmt_update.execution_options(synchronize_session="fetch")

        await self.session.execute(stmt_update)

        stmt_select = select(self.model_class).where(self.model_class.id == route_id)
        result = await self.session.execute(stmt_select)
        route = result.scalars().one()

        return route

    async def search(
        self,
        *,
        page: int,
        page_size: int,
        document_id: UUID | None,
        sender_id: UUID | None,
        status: ProcessStatus | None,
        started_from: datetime | None,
        started_to: datetime | None,
        completed_from: datetime | None,
        completed_to: datetime | None,
    ) -> tuple[list[Route], int]:
        filters: list[Any] = []
        if document_id:
            filters.append(self.model_class.document_id == document_id)
        if sender_id:
            filters.append(self.model_class.sender_id == sender_id)
        if status:
            filters.append(self.model_class.status == status)
        if started_from:
            filters.append(self.model_class.started_at >= started_from)
        if started_to:
            filters.append(self.model_class.started_at <= started_to)
        if completed_from:
            filters.append(self.model_class.completed_at >= completed_from)
        if completed_to:
            filters.append(self.model_class.completed_at <= completed_to)

        count_stmt = select(func.count()).select_from(self.model_class).where(*filters)
        total_result = await self.session.execute(count_stmt)
        total = int(total_result.scalar_one())

        stmt = (
            select(self.model_class)
            .where(*filters)
            .order_by(self.model_class.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        routes = list(result.scalars().all())
        return routes, total
