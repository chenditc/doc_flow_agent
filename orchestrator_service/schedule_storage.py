"""Persistence helpers for schedules stored under `schedules/`.

Mirrors the existing "jobs/<job_id>/{request.json,status.json}" convention but uses
atomic JSON writes to avoid partial files during crashes.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

from .schedule_models import ScheduledJobSpec, ScheduledJobStatus
from .settings import SCHEDULES_DIR


def _atomic_write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass
        temp_path.replace(path)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


@dataclass(frozen=True)
class ScheduleStore:
    schedules_dir: Path = SCHEDULES_DIR

    def schedule_dir(self, schedule_id: str) -> Path:
        normalized = (schedule_id or "").strip()
        if not normalized:
            raise ValueError("schedule_id is required")
        return self.schedules_dir / normalized

    def spec_path(self, schedule_id: str) -> Path:
        return self.schedule_dir(schedule_id) / "spec.json"

    def status_path(self, schedule_id: str) -> Path:
        return self.schedule_dir(schedule_id) / "status.json"

    def list_schedule_ids(self) -> Iterable[str]:
        if not self.schedules_dir.exists():
            return []
        result = []
        for child in self.schedules_dir.iterdir():
            if child.is_dir():
                result.append(child.name)
        return sorted(result)

    def load_spec(self, schedule_id: str) -> ScheduledJobSpec:
        path = self.spec_path(schedule_id)
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        spec = ScheduledJobSpec.from_dict(data)
        spec.validate_basic()
        return spec

    def load_status(self, schedule_id: str) -> ScheduledJobStatus:
        path = self.status_path(schedule_id)
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return ScheduledJobStatus.from_dict(data)

    def save_spec(self, spec: ScheduledJobSpec) -> None:
        spec.validate_basic()
        path = self.spec_path(spec.schedule_id)
        _atomic_write_json(path, spec.to_dict())

    def save_status(self, schedule_id: str, status: ScheduledJobStatus) -> None:
        path = self.status_path(schedule_id)
        _atomic_write_json(path, status.to_dict())

    def load_status_if_present(self, schedule_id: str) -> Optional[ScheduledJobStatus]:
        path = self.status_path(schedule_id)
        if not path.exists():
            return None
        return self.load_status(schedule_id)

