"""Data models for scheduled jobs (CronJob-like schedules).

These models are intentionally lightweight and mirror the existing `Job` dataclass
approach in `orchestrator_service.models` to keep persistence and review simple.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass
class ScheduledJobTemplate:
    """Template used to create a run (a normal job) from a schedule."""

    task_description: str
    max_tasks: int = 50
    env_vars: Dict[str, str] = field(default_factory=dict)
    sandbox_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_description": self.task_description,
            "max_tasks": self.max_tasks,
            "env_vars": dict(self.env_vars or {}),
            "sandbox_url": self.sandbox_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledJobTemplate":
        return cls(
            task_description=str(data.get("task_description") or ""),
            max_tasks=int(data.get("max_tasks") or 50),
            env_vars={str(k): str(v) for k, v in (data.get("env_vars") or {}).items()},
            sandbox_url=data.get("sandbox_url"),
        )


@dataclass
class ScheduledJobSpec:
    """User intent for a schedule, persisted to `spec.json`."""

    schedule_id: str
    name: str
    cron: str
    timezone: str = "UTC"
    suspend: bool = False
    job_template: ScheduledJobTemplate = field(default_factory=lambda: ScheduledJobTemplate(task_description=""))

    def validate_basic(self) -> None:
        if not (self.schedule_id or "").strip():
            raise ValueError("schedule_id is required")
        if not (self.name or "").strip():
            raise ValueError("name is required")
        if not (self.cron or "").strip():
            raise ValueError("cron is required")
        if not (self.timezone or "").strip():
            raise ValueError("timezone is required")
        if not (self.job_template.task_description or "").strip():
            raise ValueError("job_template.task_description is required")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "name": self.name,
            "cron": self.cron,
            "timezone": self.timezone,
            "suspend": bool(self.suspend),
            "job_template": self.job_template.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledJobSpec":
        job_template = ScheduledJobTemplate.from_dict(data.get("job_template") or {})
        return cls(
            schedule_id=str(data.get("schedule_id") or ""),
            name=str(data.get("name") or ""),
            cron=str(data.get("cron") or ""),
            timezone=str(data.get("timezone") or "UTC"),
            suspend=bool(data.get("suspend") or False),
            job_template=job_template,
        )


@dataclass
class ScheduledJobStatus:
    """Runtime status for a schedule, persisted to `status.json`."""

    last_job_id: Optional[str] = None
    last_scheduled_for: Optional[datetime] = None
    last_started_at: Optional[datetime] = None
    last_finished_at: Optional[datetime] = None
    last_status: Optional[str] = None
    next_scheduled_for: Optional[datetime] = None
    pending: bool = False
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_job_id": self.last_job_id,
            "last_scheduled_for": self.last_scheduled_for.isoformat() if self.last_scheduled_for else None,
            "last_started_at": self.last_started_at.isoformat() if self.last_started_at else None,
            "last_finished_at": self.last_finished_at.isoformat() if self.last_finished_at else None,
            "last_status": self.last_status,
            "next_scheduled_for": self.next_scheduled_for.isoformat() if self.next_scheduled_for else None,
            "pending": bool(self.pending),
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledJobStatus":
        return cls(
            last_job_id=data.get("last_job_id"),
            last_scheduled_for=_parse_datetime(data.get("last_scheduled_for")),
            last_started_at=_parse_datetime(data.get("last_started_at")),
            last_finished_at=_parse_datetime(data.get("last_finished_at")),
            last_status=data.get("last_status"),
            next_scheduled_for=_parse_datetime(data.get("next_scheduled_for")),
            pending=bool(data.get("pending") or False),
            last_error=data.get("last_error"),
        )

