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


_ci_completed = 0


def pytest_runtest_logreport(report):
    """Bounded public CI timing breadcrumbs; never print test parameters or data."""
    global _ci_completed
    if not os.environ.get("AIGENTICS_CI_PROGRESS"):
        return
    if report.when == "call" or report.when == "setup" and report.skipped:
        _ci_completed += 1
        if _ci_completed % 100 == 0:
            print(f"\nCI test progress: {_ci_completed} test calls completed", flush=True)
    if report.duration >= 10:
        phase = report.when if report.when in ("setup", "call", "teardown") else "unknown"
        print(
            f"\nCI slow test phase: {phase} took {report.duration:.1f}s; {_ci_completed} calls completed",
            flush=True,
        )
