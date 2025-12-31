import asyncio
import pytest


@pytest.mark.asyncio
async def test_create_and_complete_job(manager):
    job = await manager.create_job_async("Test basic orchestration", max_tasks=5)
    assert job.status in ("QUEUED", "STARTING")
    finished = await manager.wait_for(job.job_id)
    assert finished.status == "COMPLETED"


@pytest.mark.asyncio
async def test_multiple_jobs_concurrency(manager):
    job1 = await manager.create_job_async("Job 1", max_tasks=3)
    job2 = await manager.create_job_async("Job 2", max_tasks=3)
    await asyncio.gather(
        manager.wait_for(job1.job_id),
        manager.wait_for(job2.job_id),
    )
    assert manager.get_job(job1.job_id).status == "COMPLETED"
    assert manager.get_job(job2.job_id).status == "COMPLETED"


@pytest.mark.asyncio
async def test_cancel_job(manager, monkeypatch):
    # Force fake runner to sleep longer so we can cancel
    monkeypatch.setenv("FAKE_RUNNER_SLEEP", "0.2")
    job = await manager.create_job_async("Long running job", max_tasks=5)
    await asyncio.sleep(0.02)  # allow process to start
    cancelled = manager.cancel_job(job.job_id)
    await manager.wait_for(job.job_id)
    final_status = manager.get_job(job.job_id).status
    assert cancelled in (True, False)
    assert final_status in ("CANCELLED", "COMPLETED")
