import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator_service.manager import ExecutionManager


@pytest.fixture()
def temp_env(monkeypatch):
    base = Path(tempfile.mkdtemp(prefix="orchestrator_test_"))
    jobs_dir = base / "jobs"
    traces_dir = base / "traces"
    jobs_dir.mkdir()
    traces_dir.mkdir()
    monkeypatch.setenv("ORCHESTRATOR_RUNNER_MODULE", "orchestrator_service.fake_runner")
    monkeypatch.setenv("FAKE_RUNNER_SLEEP", "0.01")
    yield jobs_dir, traces_dir
    shutil.rmtree(base, ignore_errors=True)


@pytest_asyncio.fixture
async def manager(temp_env):
    jobs_dir, traces_dir = temp_env
    mgr = ExecutionManager(max_parallel=2, jobs_dir=jobs_dir, traces_dir=traces_dir)
    try:
        yield mgr
    finally:
        # Ensure background job tasks don't leak between tests (pytest-asyncio strict mode).
        # Only manage real asyncio Tasks; do not poll on `_jobs` because some tests
        # register synthetic Job objects without runners/tasks.
        pending = [t for t in getattr(mgr, "_tasks", {}).values() if not t.done()]
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


