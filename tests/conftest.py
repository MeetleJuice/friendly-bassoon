import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from aigentics.credentials import Credentials
from aigentics.store import Store


@pytest.fixture
def credentials(monkeypatch):
    value = Credentials()
    value._values = {}
    return value


@pytest.fixture
def store(tmp_path, credentials):
    result = Store(tmp_path / "data" / "test.sqlite3", credentials)
    yield result
    result.close()


def pytest_runtest_logstart(nodeid, location):
    """CI-only breadcrumb survives interpreter/Qt crashes before JUnit is written."""
    destination = os.environ.get("AIGENTICS_CI_PROGRESS")
    if destination:
        from pathlib import Path

        Path(destination).write_text(nodeid[:2000], encoding="utf-8")
