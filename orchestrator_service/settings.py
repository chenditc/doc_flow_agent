"""Configuration settings for orchestrator service."""

from pathlib import Path

# Directory settings
JOBS_DIR = Path("jobs")
TRACES_DIR = Path("traces")
SCHEDULES_DIR = Path("schedules")

# Execution settings
MAX_PARALLEL_JOBS = 2
DEFAULT_MAX_TASKS = 50

# Timeout settings (in seconds)
JOB_STARTUP_TIMEOUT = 30
JOB_SHUTDOWN_TIMEOUT = 10