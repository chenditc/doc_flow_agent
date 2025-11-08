"""Data models for job management."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


@dataclass
class Job:
    """Represents a job execution with status tracking."""
    job_id: str
    task_description: str
    status: str = "QUEUED"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    trace_files: List[str] = field(default_factory=list)
    pid: Optional[int] = None
    max_tasks: Optional[int] = 50
    error: Optional[Dict[str, Any]] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    # Optional sandbox endpoint; when set, run job in remote sandbox instead of local subprocess.
    # Note: If environment variable DEFAULT_SANDBOX_URL is present in orchestrator, it always takes precedence.
    sandbox_url: Optional[str] = None
    # Optional sandbox session id recorded when running remotely; used for remote cancellation or introspection.
    sandbox_session_id: Optional[str] = None
    # Remote log path when executing inside sandbox; used for tailing/downloading logs.
    sandbox_log_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON serialization."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat() if value else None
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create Job from dictionary."""
        # Convert datetime strings back to datetime objects
        for key in ['created_at', 'started_at', 'finished_at']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)
