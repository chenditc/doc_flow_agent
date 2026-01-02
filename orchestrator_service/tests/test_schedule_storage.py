from datetime import datetime, timezone

import pytest

from orchestrator_service.schedule_models import ScheduledJobSpec, ScheduledJobStatus, ScheduledJobTemplate
from orchestrator_service.schedule_storage import ScheduleStore


def test_schedule_store_roundtrip_spec_and_status(tmp_path):
    store = ScheduleStore(schedules_dir=tmp_path / "schedules")

    spec = ScheduledJobSpec(
        schedule_id="sch_test_123",
        name="nightly-report",
        cron="0 2 * * *",
        timezone="UTC",
        suspend=False,
        job_template=ScheduledJobTemplate(
            task_description="Follow sop_docs/general/plan.md, do something nightly",
            max_tasks=80,
            env_vars={"OPENAI_MODEL": "gpt-4o"},
            sandbox_url=None,
        ),
    )
    status = ScheduledJobStatus(
        last_job_id="20251212-020001-deadbeef",
        last_scheduled_for=datetime(2025, 12, 12, 2, 0, 0, tzinfo=timezone.utc),
        last_started_at=datetime(2025, 12, 12, 2, 0, 1, tzinfo=timezone.utc),
        last_finished_at=datetime(2025, 12, 12, 2, 7, 18, tzinfo=timezone.utc),
        last_status="COMPLETED",
        next_scheduled_for=datetime(2025, 12, 13, 2, 0, 0, tzinfo=timezone.utc),
        pending=False,
        last_error=None,
    )

    store.save_spec(spec)
    store.save_status(spec.schedule_id, status)

    loaded_spec = store.load_spec(spec.schedule_id)
    assert loaded_spec == spec

    loaded_status = store.load_status(spec.schedule_id)
    assert loaded_status == status

    assert store.spec_path(spec.schedule_id).exists()
    assert store.status_path(spec.schedule_id).exists()

    assert list(store.list_schedule_ids()) == [spec.schedule_id]


def test_schedule_store_atomic_write_leaves_no_temp_files(tmp_path):
    store = ScheduleStore(schedules_dir=tmp_path / "schedules")
    spec = ScheduledJobSpec(
        schedule_id="sch_atomic",
        name="atomic",
        cron="* * * * *",
        timezone="UTC",
        suspend=False,
        job_template=ScheduledJobTemplate(task_description="demo"),
    )

    store.save_spec(spec)
    # rewrite (exercise replace path)
    spec.name = "atomic2"  # type: ignore[misc]  # dataclass is mutable; ok for test mutation
    store.save_spec(spec)

    schedule_dir = store.schedule_dir(spec.schedule_id)
    leftovers = sorted(p.name for p in schedule_dir.iterdir() if p.name.endswith(".tmp"))
    assert leftovers == []


def test_schedule_spec_basic_validation():
    with pytest.raises(ValueError):
        ScheduledJobSpec(
            schedule_id="",
            name="x",
            cron="* * * * *",
            job_template=ScheduledJobTemplate(task_description="demo"),
        ).validate_basic()

