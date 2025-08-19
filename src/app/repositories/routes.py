import abc
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessStatus, Route
from app.repositories import ARepository
from app.utils.timestamps import now_with_tz


class ARoutesRepository(ARepository[Route, UUID], abc.ABC):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Route)

    @abc.abstractmethod
    async def update_status(self, route_id: UUID, status: ProcessStatus) -> Route:
        raise NotImplementedError


class RoutesRepository(ARoutesRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def update_status(self, route_id: UUID, status: ProcessStatus) -> Route:
        stmt_update = update(self.model_class).where(self.model_class.id == route_id).values(status=status)

        if status == ProcessStatus.IN_PROGRESS:
            stmt_update = stmt_update.values(started_at=now_with_tz())
        elif status in (status.FAILED, status.COMPLETED):
            stmt_update = stmt_update.values(completed_at=now_with_tz())

        stmt_update = stmt_update.execution_options(synchronize_session="fetch")

        await self.session.execute(stmt_update)

        stmt_select = select(self.model_class).where(self.model_class.id == route_id)
        result = await self.session.execute(stmt_select)
        route = result.scalars().one()

        return route
