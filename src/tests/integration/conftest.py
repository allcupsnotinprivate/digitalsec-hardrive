import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.postgres import PostgresDatabase


@pytest_asyncio.fixture(scope="session")
async def database(pytestconfig) -> PostgresDatabase:
    db = PostgresDatabase(
        user=pytestconfig.getoption("--pg-user"),
        password=pytestconfig.getoption("--pg-password"),
        host=pytestconfig.getoption("--pg-host"),
        port=pytestconfig.getoption("--pg-port"),
        database=pytestconfig.getoption("--pg-db"),
        automigrate=True,
    )
    await db.startup()
    yield db  # noqa
    await db.shutdown()


@pytest_asyncio.fixture
async def session(database: PostgresDatabase) -> AsyncSession:
    async with database.get_session() as session_:
        trans = await session_.begin()
        yield session_  # noqa
        await trans.rollback()
