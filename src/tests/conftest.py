import sys
from pathlib import Path

import pytest

from tests import TEST_CORE_PATH

sys.path.append(str(Path(__file__).resolve().parents[1]))


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("pg")
    group.addoption(
        "--pg-container-image",
        action="store",
        default="pgvector/pgvector:pg17",
        help="Docker image for Postgres testcontainers",
    )
    group.addoption(
        "--pg-shared-init-scripts",
        action="store",
        default=TEST_CORE_PATH / "../../deployment/init-scripts",
        help="Absolute path to init scripts dir for the shared Postgres container "
        "(mounted to /docker-entrypoint-initdb.d). Optional.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "sep_database: use a separate PostgreSQL database for this test",
    )
