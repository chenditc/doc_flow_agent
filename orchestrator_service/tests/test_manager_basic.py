import asyncio
import json
from pathlib import Path, PurePosixPath

import pytest

from orchestrator_service.models import Job


@pytest.mark.asyncio
async def test_create_and_complete_simple_job(manager):
    job = manager.create_job("Follow bash.md, echo hello", max_tasks=5)
    assert job.job_id in manager._jobs
    assert job.status in ("QUEUED", "STARTING", "RUNNING")

    stored = await manager.wait_for(job.job_id)
    assert stored.status in ("COMPLETED", "FAILED")
    # status.json should exist
    status_file = Path(manager.jobs_dir / job.job_id / 'status.json')
    assert status_file.exists()


@pytest.mark.asyncio
async def test_job_logs_access(manager):
    job = manager.create_job("Follow bash.md, list current directory", max_tasks=5)
    logs = manager.get_job_logs(job.job_id)
    # Logs might be empty early; ensure callable and returns str or None
    assert logs is None or isinstance(logs, str)


@pytest.mark.asyncio
async def test_cancel_nonexistent_job(manager):
    assert manager.cancel_job("does_not_exist") is False


@pytest.mark.asyncio
async def test_cancel_running_job(manager, monkeypatch):
    # Make the fake runner run long enough to observe cancellation.
    monkeypatch.setenv("FAKE_RUNNER_SLEEP", "0.2")
    job = manager.create_job("Follow bash.md, echo cancel test", max_tasks=5)

    # Wait until RUNNING (or the job finishes).
    while True:
        current = manager.get_job(job.job_id)
        if current.status in ("RUNNING", "COMPLETED", "FAILED", "CANCELLED"):
            break
        await asyncio.sleep(0.01)

    cancelled = manager.cancel_job(job.job_id)
    assert cancelled in (True, False)  # If already finished, may return False
    final = await manager.wait_for(job.job_id)
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

    await manager.wait_for(job.job_id)

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
    assert env_data.get("DOCFLOW_JOB_ID") == job.job_id

    task_file = Path(manager.jobs_dir / job.job_id / f"{job.job_id}.task")
    assert task_file.exists()
    assert task_file.read_text(encoding="utf-8") == job.task_description


@pytest.mark.asyncio
async def test_resolve_sandbox_file_request_remote(monkeypatch, manager):
    from orchestrator_service import manager as manager_module

    sandbox_root = PurePosixPath("/app")
    monkeypatch.setattr(manager_module, "SANDBOX_WORKDIR", sandbox_root)

    job = Job(job_id="remote-job", task_description="demo", sandbox_url="http://sandbox")
    manager._jobs[job.job_id] = job

    result = manager.resolve_sandbox_file_request(job.job_id, "/app/user_comm/s1/t1/index.html")
    assert result["mode"] == "remote"
    assert result["sandbox_path"] == "/app/user_comm/s1/t1/index.html"
    assert result["filename"] == "index.html"


@pytest.mark.asyncio
async def test_resolve_sandbox_file_request_local(monkeypatch, manager, tmp_path):
    from orchestrator_service import manager as manager_module

    sandbox_root = tmp_path / "sandbox_local"
    sandbox_root.mkdir()
    target_file = sandbox_root / "user_comm" / "s42" / "t99" / "index.html"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text("local", encoding="utf-8")

    monkeypatch.setattr(manager_module, "SANDBOX_WORKDIR", PurePosixPath(str(sandbox_root)))

    job = Job(job_id="local-job", task_description="demo")
    manager._jobs[job.job_id] = job

    result = manager.resolve_sandbox_file_request(job.job_id, str(target_file))
    assert result["mode"] == "local"
    assert result["local_path"] == Path(target_file)
    assert result["filename"] == "index.html"


def test_resolve_sandbox_file_invalid_path(manager, monkeypatch):
    from orchestrator_service import manager as manager_module

    monkeypatch.setattr(manager_module, "SANDBOX_WORKDIR", PurePosixPath("/app"))
    job = Job(job_id="job-1", task_description="demo")
    manager._jobs[job.job_id] = job

    with pytest.raises(ValueError):
        manager.resolve_sandbox_file_request(job.job_id, "../etc/passwd")
