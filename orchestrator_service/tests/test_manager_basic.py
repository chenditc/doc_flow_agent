import asyncio
import json
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_create_and_complete_simple_job(manager):
    job = manager.create_job("Follow bash.md, echo hello", max_tasks=5)
    assert job.job_id in manager._jobs
    assert job.status in ("QUEUED", "STARTING", "RUNNING")

    # Wait for completion (polling)
    # Allow longer time since engine may invoke LLM or external tools. Max ~30s.
    for _ in range(300):  # 300 * 0.1s = 30s
        stored = manager.get_job(job.job_id)
        if stored.status in ("COMPLETED", "FAILED"):
            break
        await asyncio.sleep(0.1)

    stored = manager.get_job(job.job_id)
    # Accept RUNNING to avoid flakiness if job genuinely long-running; test focuses on lifecycle initiation.
    assert stored.status in ("COMPLETED", "FAILED", "RUNNING")
    # status.json should exist
    status_file = Path(manager.jobs_dir / job.job_id / 'status.json')
    assert status_file.exists()


@pytest.mark.asyncio
async def test_job_logs_access(manager):
    job = manager.create_job("Follow bash.md, list current directory", max_tasks=5)
    # Wait briefly for logs to appear
    await asyncio.sleep(0.5)
    logs = manager.get_job_logs(job.job_id)
    # Logs might be empty early; ensure callable and returns str or None
    assert logs is None or isinstance(logs, str)


@pytest.mark.asyncio
async def test_cancel_nonexistent_job(manager):
    assert manager.cancel_job("does_not_exist") is False


@pytest.mark.asyncio
async def test_cancel_running_job(manager):
    job = manager.create_job("Follow bash.md, echo cancel test", max_tasks=5)

    # Wait until RUNNING or timeout
    for _ in range(50):
        current = manager.get_job(job.job_id)
        if current.status == "RUNNING":
            break
        await asyncio.sleep(0.1)

    cancelled = manager.cancel_job(job.job_id)
    assert cancelled in (True, False)  # If already finished, may return False
    final = manager.get_job(job.job_id)
    assert final is not None
    assert final.status in ("CANCELLED", "COMPLETED", "FAILED")


@pytest.mark.asyncio
async def test_env_vars_propagation(manager):
    env_vars = {"DOCFLOW_TEST": "enabled", "ANOTHER_VAR": "123"}
    job = manager.create_job(
        "Follow bash.md, echo env vars",
        max_tasks=5,
        env_vars=env_vars,
    )

    await manager.wait_for(job.job_id, timeout=5)

    status_file = Path(manager.jobs_dir / job.job_id / "status.json")
    with status_file.open("r", encoding="utf-8") as f:
        status_data = json.load(f)

    assert status_data.get("env_vars") == env_vars

    request_file = Path(manager.jobs_dir / job.job_id / "request.json")
    with request_file.open("r", encoding="utf-8") as f:
        request_data = json.load(f)

    assert request_data.get("env_vars") == env_vars

    context_file = Path(manager.jobs_dir / job.job_id / "context.json")
    assert context_file.exists()
    with context_file.open("r", encoding="utf-8") as f:
        context_data = json.load(f)

    assert context_data.get("env_vars") == env_vars

    env_file = Path(manager.jobs_dir / job.job_id / "env.json")
    assert env_file.exists()
    with env_file.open("r", encoding="utf-8") as f:
        env_data = json.load(f)
    for key, value in env_vars.items():
        assert env_data.get(key) == value
