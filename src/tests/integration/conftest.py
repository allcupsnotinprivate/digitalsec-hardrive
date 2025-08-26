from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer

from app.infrastructure.database.postgres import PostgresDatabase

INIT_SQL = Path(__file__).resolve().parents[3] / "deployment" / "init-scripts" / "init_pgvector.sql"


def _start_container(pytestconfig: pytest.Config) -> PostgresContainer:
    image = pytestconfig.getoption("--pg-container-image")
    container = PostgresContainer(image).with_volume_mapping(str(INIT_SQL), "/docker-entrypoint-initdb.d/init.sql")
    container.start()
    return container


@pytest.fixture(scope="session")
def pg_container(pytestconfig: pytest.Config) -> Generator[PostgresContainer]:
    container = _start_container(pytestconfig)
    yield container
    container.stop()


@pytest_asyncio.fixture(scope="session")
async def shared_database(pg_container: PostgresContainer) -> AsyncGenerator[PostgresDatabase]:
    db = PostgresDatabase(
        user=pg_container.username,
        password=pg_container.password,
        host=pg_container.get_container_host_ip(),
        port=int(pg_container.get_exposed_port(pg_container.port)),
        database=pg_container.dbname,
        automigrate=True,
    )
    await db.startup()
    yield db
    await db.shutdown()


@pytest_asyncio.fixture
async def database(
    request: pytest.FixtureRequest,
    pytestconfig: pytest.Config,
    shared_database: PostgresDatabase,
) -> AsyncGenerator[PostgresDatabase]:
    if request.node.get_closest_marker("sep_database"):
        container = _start_container(pytestconfig)
        db = PostgresDatabase(
            user=container.username,
            password=container.password,
            host=container.get_container_host_ip(),
            port=int(container.get_exposed_port(container.port)),
            database=container.dbname,
            automigrate=True,
        )
        await db.startup()
        try:
            yield db
        finally:
            await db.shutdown()
            container.stop()
    else:
        yield shared_database


@pytest_asyncio.fixture
async def session(database: PostgresDatabase) -> AsyncGenerator[AsyncSession]:
    async with database.get_session() as session_:
        yield session_
