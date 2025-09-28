"""Execution manager for orchestrating doc engine jobs."""

import asyncio
import json
import os
import signal
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import Job
from .settings import JOBS_DIR, TRACES_DIR, MAX_PARALLEL_JOBS, JOB_SHUTDOWN_TIMEOUT


class ExecutionManager:
    """Manages concurrent execution of doc engine jobs.

    Testability hooks:
    - jobs_dir / traces_dir can be overridden (useful for isolated temp dirs in tests)
    - ORCHESTRATOR_RUNNER_MODULE environment variable can override the runner module
      (default: orchestrator_service.runner) enabling a lightweight fake runner in tests.
    """

    def __init__(self, max_parallel: int = MAX_PARALLEL_JOBS, *, jobs_dir: Optional[Path] = None, traces_dir: Optional[Path] = None):
        self.jobs_dir = jobs_dir or JOBS_DIR
        self.traces_dir = traces_dir or TRACES_DIR
        self.max_parallel = max_parallel

        self.jobs_dir.mkdir(exist_ok=True)
        self.traces_dir.mkdir(exist_ok=True)
        self._jobs: Dict[str, Job] = {}
        # Track asyncio tasks for launched jobs so tests can await completion deterministically
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._sem = asyncio.Semaphore(max_parallel)

        self._load_existing_jobs()

    def _load_existing_jobs(self):
        if not self.jobs_dir.exists():
            return
        for job_dir in self.jobs_dir.iterdir():
            if not job_dir.is_dir():
                continue
            status_file = job_dir / "status.json"
            if not status_file.exists():
                continue
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                job = Job.from_dict(data)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                print(f"Failed to load job from {job_dir}: {e}")
                continue
            self._jobs[job.job_id] = job
            if job.status == "RUNNING" and job.pid:
                try:
                    os.kill(job.pid, 0)
                except (ProcessLookupError, PermissionError):
                    job.status = "FAILED"
                    job.finished_at = datetime.now(timezone.utc)
                    job.error = {"message": "Process terminated unexpectedly"}
                    self._persist_status(job)

    def create_job(self, task_description: str, max_tasks: Optional[int] = None) -> Job:
        job_id = uuid.uuid4().hex[:16]
        job = Job(job_id=job_id, task_description=task_description, max_tasks=max_tasks or 50)
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(exist_ok=True)
        request_data = {"task_description": task_description, "max_tasks": job.max_tasks, "created_at": job.created_at.isoformat()}
        with open(job_dir / "request.json", 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        self._jobs[job_id] = job
        self._persist_status(job)
        # Only create task if event loop is running (for API usage)
        try:
            t = asyncio.create_task(self._launch_job(job))
            self._tasks[job_id] = t
        except RuntimeError:
            pass  # No event loop running, caller will handle async launch
        return job

    async def create_job_async(self, task_description: str, max_tasks: Optional[int] = None) -> Job:
        """Async version for proper test usage."""
        job_id = uuid.uuid4().hex[:16]
        job = Job(job_id=job_id, task_description=task_description, max_tasks=max_tasks or 50)
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(exist_ok=True)
        request_data = {"task_description": task_description, "max_tasks": job.max_tasks, "created_at": job.created_at.isoformat()}
        with open(job_dir / "request.json", 'w', encoding='utf-8') as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        self._jobs[job_id] = job
        self._persist_status(job)
        t = asyncio.create_task(self._launch_job(job))
        self._tasks[job_id] = t
        return job

    def _persist_status(self, job: Job):
        job_dir = self.jobs_dir / job.job_id
        # Defensive: ensure directory exists (tests may clean aggressively or race conditions)
        job_dir.mkdir(parents=True, exist_ok=True)
        status_file = job_dir / "status.json"
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(job.to_dict(), f, ensure_ascii=False, indent=2)

    async def _launch_job(self, job: Job):
        async with self._sem:
            try:
                await self._execute_job(job)
            except OSError as e:
                job.status = "FAILED"
                job.finished_at = datetime.now(timezone.utc)
                job.error = {"message": str(e), "type": type(e).__name__}
                self._persist_status(job)
                print(f"Job {job.job_id} failed to start: {e}")

    async def _execute_job(self, job: Job):
        job.status = "STARTING"
        job.started_at = datetime.now(timezone.utc)
        self._persist_status(job)
        # Pre-generate a trace filename so clients can discover it immediately.
        # Use same pattern: session_<timestamp>_<shortid>.json (shortid from job id for determinism in context of job)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trace_filename = f"session_{timestamp}_{job.job_id[:8]}.json"
        trace_path = self.traces_dir / trace_filename
        try:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.touch(exist_ok=True)
        except OSError as e:
            print(f"Warning: failed to precreate trace file {trace_path}: {e}")
        # Record early so API returns it during RUNNING
        if trace_filename not in job.trace_files:
            job.trace_files.append(trace_filename)
            self._persist_status(job)
        runner_module = os.getenv("ORCHESTRATOR_RUNNER_MODULE", "orchestrator_service.runner")
        import sys
        cmd = [
            sys.executable, "-m", runner_module,
            "--job-id", job.job_id,
            "--task", job.task_description,
            "--max-tasks", str(job.max_tasks),
            "--trace-file", trace_filename
        ]
        job_dir = self.jobs_dir / job.job_id
        log_path = job_dir / "engine_stdout.log"
        try:
            with open(log_path, 'w', encoding='utf-8') as log_file:
                proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, cwd=Path.cwd())
        except OSError as e:
            raise e
        job.pid = proc.pid
        job.status = "RUNNING"
        self._persist_status(job)
        loop = asyncio.get_running_loop()
        exit_code = await loop.run_in_executor(None, proc.wait)
        job.finished_at = datetime.now(timezone.utc)
        if exit_code == 0 and job.status != "CANCELLED":
            job.status = "COMPLETED"
        elif job.status != "CANCELLED":
            job.status = "FAILED"
            job.error = {"exit_code": exit_code}
        self._persist_status(job)
        print(f"Job {job.job_id} finished with status {job.status}")
    # Task is done; keep entry for introspection (not deleting) so wait_for still works

    def list_jobs(self) -> List[Job]:
        # Return jobs ordered by creation time (most recent first) to make UI display intuitive
        # Sorting here centralizes ordering so all callers (API, tests) see consistent order.
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.status not in ("RUNNING", "STARTING"):
            return False
        if job.pid:
            try:
                os.kill(job.pid, signal.SIGTERM)
                job.status = "CANCELLED"
                job.finished_at = datetime.now(timezone.utc)
                self._persist_status(job)
                return True
            except (ProcessLookupError, PermissionError):
                job.status = "CANCELLED"
                job.finished_at = datetime.now(timezone.utc)
                self._persist_status(job)
                return True
        return False

    def get_job_logs(self, job_id: str, tail_lines: Optional[int] = None) -> Optional[str]:
        job_dir = self.jobs_dir / job_id
        log_file = job_dir / "engine_stdout.log"
        if not log_file.exists():
            return None
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                if tail_lines:
                    lines = f.readlines()
                    return ''.join(lines[-tail_lines:])
                return f.read()
        except (OSError, UnicodeDecodeError):
            return None

    async def wait_for(self, job_id: str, timeout: float = 5.0) -> Optional[Job]:
        """Await completion of a job (COMPLETED / FAILED / CANCELLED) or timeout.

        Returns the current Job object (may still be RUNNING/QUEUED if timeout reached).
        """
        job = self.get_job(job_id)
        if not job:
            return None
        task = self._tasks.get(job_id)
        if not task:  # Possibly created via sync path without event loop
            # Poll fallback
            end = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < end and job.status not in ("COMPLETED", "FAILED", "CANCELLED"):
                await asyncio.sleep(0.05)
            return job
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return self.get_job(job_id)

    async def wait_for_all(self, timeout: float = 5.0):
        """Await completion (or timeout) of all known jobs."""
        tasks = [self.wait_for(jid, timeout=timeout) for jid in list(self._jobs.keys())]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)