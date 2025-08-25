import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--pg-host", action="store", default="localhost", help="Postgres host for tests")
    parser.addoption("--pg-port", action="store", default=5432, type=int, help="Postgres port for tests")
    parser.addoption("--pg-user", action="store", default="digitalsec_username", help="Postgres user for tests")
    parser.addoption(
        "--pg-password", action="store", default="digitalsec_password", help="Postgres password for tests"
    )
    parser.addoption("--pg-db", action="store", default="test_digitalsec", help="Postgres database for tests")
