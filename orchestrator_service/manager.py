"""Execution manager for orchestrating doc engine jobs."""

import asyncio
import json
import os
import posixpath
import shlex
import signal
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

import httpx
from agent_sandbox import AsyncSandbox, Sandbox
from agent_sandbox.core.api_error import ApiError
from loguru import logger

from .models import Job
from .settings import JOBS_DIR, TRACES_DIR, MAX_PARALLEL_JOBS, JOB_SHUTDOWN_TIMEOUT

SANDBOX_WORKDIR = PurePosixPath(os.getenv("SANDBOX_WORKDIR", "/app"))
SANDBOX_TRACES_DIR = SANDBOX_WORKDIR / "traces"
SANDBOX_JOBS_DIR = SANDBOX_WORKDIR / "jobs"
REMOTE_ARTIFACT_TIMEOUT = float(os.getenv("REMOTE_ARTIFACT_TIMEOUT", "60.0"))


@dataclass
class RunnerStartInfo:
    """Metadata captured immediately after a runner starts."""

    pid: Optional[int] = None
    sandbox_session_id: Optional[str] = None


@dataclass
class RunnerResult:
    """Outcome of a runner once execution completes."""

    exit_code: int
    log_output: Optional[str] = None


class BaseRunner:
    """Minimal interface for execution backends."""

    async def start(self) -> RunnerStartInfo:
        raise NotImplementedError

    async def wait(self) -> RunnerResult:
        raise NotImplementedError

    def cancel(self) -> bool:
        raise NotImplementedError


class SubprocessRunner(BaseRunner):
    """Run a job locally using subprocess and stream output to a log file."""

    def __init__(self, command: List[str], *, log_path: Path, env: Dict[str, str], cwd: Path):
        self.command = command
        self.log_path = log_path
        self.environment = env
        self.working_directory = cwd
        self._process: Optional[subprocess.Popen] = None
        self._log_file = None

    async def start(self) -> RunnerStartInfo:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = open(self.log_path, 'w', encoding='utf-8')
        try:
            self._process = subprocess.Popen(
                self.command,
                stdout=self._log_file,
                stderr=subprocess.STDOUT,
                cwd=self.working_directory,
                env=self.environment,
            )
        except OSError:
            self._close_log_file()
            raise
        return RunnerStartInfo(pid=self._process.pid)

    async def wait(self) -> RunnerResult:
        if not self._process:
            raise RuntimeError("SubprocessRunner.wait called before start")
        loop = asyncio.get_running_loop()
        exit_code = await loop.run_in_executor(None, self._process.wait)
        self._close_log_file()
        return RunnerResult(exit_code=exit_code)

    def cancel(self) -> bool:
        if not self._process:
            return False
        try:
            os.kill(self._process.pid, signal.SIGTERM)
            if self._process.poll() is not None:
                self._close_log_file()
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _close_log_file(self):
        if self._log_file and not self._log_file.closed:
            self._log_file.flush()
            self._log_file.close()
        self._log_file = None


class SandboxRunner(BaseRunner):
    """Run a job inside the remote sandbox shell API."""

    def __init__(
        self,
        *,
        sandbox_url: str,
        command: List[str],
        log_path: Path,
        remote_log_path: str,
        request_timeout: float = 86400.0,
        session_id: Optional[str] = None,
    ):
        self.sandbox_url = sandbox_url.rstrip("/")
        self.command = command
        self.log_path = log_path
        self.remote_log_path = remote_log_path
        self.request_timeout = request_timeout
        self._preferred_session_id = session_id
        if not self.remote_log_path:
            raise ValueError("remote_log_path is required for SandboxRunner")
        self._http_client: Optional[httpx.AsyncClient] = None
        self._sandbox_client: Optional[AsyncSandbox] = None
        self._session_id: Optional[str] = None

    async def start(self) -> RunnerStartInfo:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._http_client = httpx.AsyncClient(timeout=self.request_timeout)
        self._sandbox_client = AsyncSandbox(
            base_url=self.sandbox_url,
            timeout=self.request_timeout,
            httpx_client=self._http_client,
        )
        try:
            desired_session_id = self._preferred_session_id or uuid.uuid4().hex
            session_response = await self._sandbox_client.shell.create_session(id=desired_session_id)
            session_data = self._unwrap_response_data(session_response, context="create sandbox session")
            self._session_id = session_data.session_id
            command_string = self._wrap_with_log_redirection(self._build_command_string())
            exec_response = await self._sandbox_client.shell.exec_command(
                id=self._session_id,
                command=command_string,
                async_mode=True,
                exec_dir="/app/" # Same dir as sandbox dockerfile workdir
            )
            exec_data = self._unwrap_response_data(exec_response, context="execute sandbox command")
            if exec_data.status not in {"running"}:
                print("Unexpected sandbox exec data:", exec_data)
                raise RuntimeError(f"Unexpected sandbox exec status: {exec_data.status}")
        except (httpx.HTTPError, ApiError, RuntimeError, ValueError, TypeError):
            await self._close_client()
            raise
        return RunnerStartInfo(sandbox_session_id=self._session_id)

    async def wait(self) -> RunnerResult:
        if not self._sandbox_client or not self._session_id:
            raise RuntimeError("SandboxRunner.wait called before start")
        try:
            exit_status = await self._wait_for_completion()
            await self._download_remote_log()
        except:
            # Try to get whatever log we can on failure
            await self._download_remote_log()
        finally:
            await self._close_client()
        return RunnerResult(exit_code=exit_status)

    def cancel(self) -> bool:
        if not self._session_id:
            return False
        return self.kill_session(
            sandbox_url=self.sandbox_url,
            session_id=self._session_id,
            timeout=self.request_timeout,
        )

    async def _wait_for_completion(self) -> int:
        assert self._sandbox_client is not None
        assert self._session_id is not None
        while True:
            wait_response = await self._sandbox_client.shell.wait_for_process(
                id=self._session_id,
                seconds=20,
            )
            print("[SANDBOX WAIT] Response:", wait_response)
            wait_data = self._unwrap_response_data(wait_response, context="wait for sandbox process")
            status = wait_data.status
            if status in {"running", "no_change_timeout"}:
                await asyncio.sleep(0.5)
                continue
            if status not in {"completed", "terminated", "hard_timeout"}:
                raise RuntimeError(f"Unexpected sandbox wait status: {status}")
            break

        view_response = await self._sandbox_client.shell.view(id=self._session_id)
        view_data = self._unwrap_response_data(view_response, context="retrieve sandbox output")
        exit_code = view_data.exit_code if view_data.exit_code is not None else 1
        return exit_code

    async def _download_remote_log(self):
        if not self._sandbox_client:
            return
        try:
            stream = await self._sandbox_client.file.download_file(path=self.remote_log_path)
        except (httpx.HTTPError, ApiError, ValueError, TypeError):
            return
        temp_path = self.log_path.parent / f"{self.log_path.name}.tmp"
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, 'wb') as temp_file:
                async for chunk in stream:
                    temp_file.write(chunk)
            temp_path.replace(self.log_path)
        except (OSError, httpx.HTTPError, ApiError, ValueError, TypeError):
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    async def _close_client(self):
        http_client = self._http_client
        self._http_client = None
        self._sandbox_client = None
        if http_client:
            await http_client.aclose()

    def _build_command_string(self) -> str:
        return shlex.join(self.command)

    def _wrap_with_log_redirection(self, command: str) -> str:
        log_path = shlex.quote(self.remote_log_path)
        log_dir = shlex.quote(str(PurePosixPath(self.remote_log_path).parent))
        tee_pipeline = (
            "set -o pipefail; "
            f"( {command} ) 2>&1 | tee -a {log_path}"
        )
        return (
            f"mkdir -p {log_dir} && "
            f": > {log_path} && "
            f"chmod 600 {log_path} && "
            f"bash -lc {shlex.quote(tee_pipeline)}"
        )

    @staticmethod
    def _format_console_output(console_records, aggregated_output: str) -> str:
        if not console_records:
            return aggregated_output
        output_lines: List[str] = []
        for record in console_records:
            if isinstance(record, dict):
                ps1 = record.get("ps1", "")
                issued_command = record.get("command", "")
                record_output = record.get("output", "")
            else:
                ps1 = getattr(record, "ps1", "")
                issued_command = getattr(record, "command", "")
                record_output = getattr(record, "output", "")
            if ps1 or issued_command:
                output_lines.append(f"{ps1}{issued_command}")
            if record_output:
                output_lines.append(record_output)
        if aggregated_output:
            output_lines.append(aggregated_output)
        return "\n".join(output_lines)

    @staticmethod
    def kill_session(*, sandbox_url: str, session_id: str, timeout: float = 30.0) -> bool:
        base_url = sandbox_url.rstrip("/")
        try:
            with httpx.Client(timeout=timeout) as http_client:
                client = Sandbox(
                    base_url=base_url,
                    timeout=timeout,
                    httpx_client=http_client,
                )
                response = client.shell.kill_process(id=session_id)
            if response.success is False or response.data is None:
                return False
            return True
        except (httpx.HTTPError, ApiError, ValueError, TypeError):
            return False

    @staticmethod
    def view_session(*, sandbox_url: str, session_id: str, timeout: float = 30.0) -> Optional[str]:
        base_url = sandbox_url.rstrip("/")
        try:
            with httpx.Client(timeout=timeout) as http_client:
                client = Sandbox(
                    base_url=base_url,
                    timeout=timeout,
                    httpx_client=http_client,
                )
                response = client.shell.view(id=session_id)
            if response.success is False or response.data is None:
                return None
            console_records = response.data.console
            aggregated_output = response.data.output or ""
            return SandboxRunner._format_console_output(console_records, aggregated_output)
        except (httpx.HTTPError, ApiError, ValueError, TypeError):
            return None

    @staticmethod
    def tail_remote_log(
        *,
        sandbox_url: str,
        log_path: str,
        tail_lines: Optional[int] = None,
        timeout: float = 30.0,
    ) -> Optional[str]:
        if not log_path:
            return None
        base_url = sandbox_url.rstrip("/")
        num_lines = tail_lines if tail_lines and tail_lines > 0 else None
        quoted_path = shlex.quote(log_path)
        if num_lines is None:
            command = f"cat {quoted_path}"
        else:
            command = f"tail -n {num_lines} {quoted_path}"
        http_client: Optional[httpx.Client] = None
        client: Optional[Sandbox] = None
        session_id: Optional[str] = None
        try:
            http_client = httpx.Client(timeout=timeout)
            client = Sandbox(
                base_url=base_url,
                timeout=timeout,
                httpx_client=http_client,
            )
            response = client.shell.exec_command(
                command=command,
                async_mode=False,
                timeout=timeout,
            )
            data = SandboxRunner._unwrap_response_data(response, context="tail remote log")
            session_id = getattr(data, "session_id", None)
            if getattr(data, "status", None) != "completed":
                return None
            if data.exit_code not in (0, None):
                return None
            return SandboxRunner._format_console_output(data.console, data.output or "")
        except (httpx.HTTPError, ApiError, RuntimeError, ValueError, TypeError):
            return None
        finally:
            if session_id and client is not None:
                try:
                    client.shell.kill_process(id=session_id)
                except (httpx.HTTPError, ApiError, ValueError, TypeError):
                    pass
            if http_client:
                http_client.close()

    @staticmethod
    def _unwrap_response_data(response: Any, *, context: str):
        if response is None:
            raise RuntimeError(f"Sandbox 【{context}】 returned no response object")
        if getattr(response, "success", None) is False:
            message = getattr(response, "message", "unknown error")
            raise RuntimeError(f"Sandbox 【{context}】 failed: {message}")
        data = getattr(response, "data", None)
        if data is None:
            raise RuntimeError(f"Sandbox 【{context}】 returned empty data")
        return data


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
        self._runners: Dict[str, BaseRunner] = {}
        self._lock = asyncio.Lock()
        self._sem = asyncio.Semaphore(max_parallel)
        self._remote_artifact_timeout = REMOTE_ARTIFACT_TIMEOUT

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

    def _resolve_sandbox_url(self, requested_sandbox_url: Optional[str]) -> Optional[str]:
        requested = (requested_sandbox_url or "").strip()
        candidate = requested or os.getenv("DEFAULT_SANDBOX_URL", "").strip()
        if not candidate:
            return None
        return candidate.rstrip("/")

    def _build_remote_sandbox_log_path(self, job_id: str) -> str:
        base_dir = PurePosixPath("/tmp/doc_engine_logs")
        return str(base_dir / f"{job_id}.log")

    def _build_remote_trace_path(self, trace_filename: str) -> str:
        return str(SANDBOX_TRACES_DIR / trace_filename)

    def _build_remote_context_path(self, job_id: str) -> str:
        return str(SANDBOX_JOBS_DIR / job_id / "context.json")

    def _build_remote_task_path(self, job_id: str) -> str:
        return str(SANDBOX_JOBS_DIR / job_id / f"{job_id}.task")

    def _build_remote_env_path(self, job_id: str) -> str:
        return str(SANDBOX_JOBS_DIR / job_id / f"{job_id}.env.json")

    @staticmethod
    def _normalize_env(env: Dict[str, Any]) -> Dict[str, str]:
        return {str(key): str(value) for key, value in env.items()}

    def _normalize_requested_sandbox_path(self, requested_path: str) -> PurePosixPath:
        """Ensure the user-provided sandbox path is an absolute, normalized path under SANDBOX_WORKDIR."""
        cleaned = (requested_path or "").strip()
        if not cleaned:
            raise ValueError("Path is required")
        if not cleaned.startswith("/"):
            cleaned = "/" + cleaned

        candidate = PurePosixPath(cleaned)
        if not candidate.is_absolute():
            raise ValueError(f"Path must be absolute: {cleaned}")

        normalized = PurePosixPath(posixpath.normpath(str(candidate)))
        if normalized != candidate:
            raise ValueError("Path must be normalized and cannot include traversal segments")

        if not str(normalized).startswith(str(SANDBOX_WORKDIR)):
            raise ValueError("Path must reside within the sandbox workdir")

        if normalized == SANDBOX_WORKDIR:
            raise ValueError("Path must reference a file within the sandbox workdir")

        return normalized

    def resolve_sandbox_file_request(self, job_id: str, requested_path: str) -> Dict[str, Any]:
        """Resolve how to serve a sandbox file for a job."""

        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"Job {job_id} not found")

        sandbox_path = self._normalize_requested_sandbox_path(requested_path)

        if job.sandbox_url:
            return {
                "mode": "remote",
                "job": job,
                "sandbox_path": str(sandbox_path),
                "filename": sandbox_path.name,
            }

        local_path = Path(str(sandbox_path))
        if not local_path.exists() or not local_path.is_file():
            raise FileNotFoundError(f"File not found: {sandbox_path}")

        return {
            "mode": "local",
            "local_path": local_path,
            "filename": local_path.name,
        }

    async def stream_remote_sandbox_file(self, job: Job, sandbox_path: str):
        """Stream a remote sandbox file directly from the sandbox service."""

        http_client = httpx.AsyncClient(timeout=self._remote_artifact_timeout)
        sandbox_client = AsyncSandbox(
            base_url=job.sandbox_url.rstrip("/"),
            timeout=self._remote_artifact_timeout,
            httpx_client=http_client,
        )
        try:
            async for chunk in sandbox_client.file.download_file(path=sandbox_path):
                yield chunk
        except ApiError as exc:
            if exc.status_code == 404:
                raise FileNotFoundError(sandbox_path) from exc
            raise
        finally:
            await http_client.aclose()

    async def sync_job_context(self, job_id: str, *, force: bool = False) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        local_path = self.jobs_dir / job_id / "context.json"
        if not job.sandbox_url:
            return local_path.exists()
        should_download = force or not local_path.exists() or job.status in ("RUNNING", "STARTING")
        if not should_download:
            return True
        remote_path = self._build_remote_context_path(job_id)
        return await self._async_download_remote_file(
            sandbox_url=job.sandbox_url,
            remote_path=remote_path,
            local_path=local_path,
        )

    async def sync_trace_file(
        self,
        trace_filename: str,
        *,
        job_id: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        resolved_job_id = job_id
        if not resolved_job_id:
            resolved_job_id = trace_filename[:-5] if trace_filename.endswith(".json") else trace_filename
        job = self._jobs.get(resolved_job_id or "")
        if not job:
            return False
        local_path = self.traces_dir / trace_filename
        if not job.sandbox_url:
            return local_path.exists()
        should_download = force or not local_path.exists() or job.status in ("RUNNING", "STARTING")
        if not should_download:
            return True
        remote_path = self._build_remote_trace_path(trace_filename)
        success = await self._async_download_remote_file(
            sandbox_url=job.sandbox_url,
            remote_path=remote_path,
            local_path=local_path,
        )
        return success

    @staticmethod
    def _download_sandbox_file_to_local(
        *,
        sandbox_url: str,
        remote_path: str,
        local_path: Path,
        timeout: float,
    ) -> bool:
        """Download a remote sandbox file and atomically write it to local_path."""
        base_url = sandbox_url.rstrip("/")
        temp_path = local_path.parent / f".{local_path.name}.tmp"
        http_client: Optional[httpx.Client] = None
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            http_client = httpx.Client(timeout=timeout)
            client = Sandbox(
                base_url=base_url,
                timeout=timeout,
                httpx_client=http_client,
            )
            stream = client.file.download_file(path=remote_path)
            with open(temp_path, "wb") as temp_file:
                for chunk in stream:
                    temp_file.write(chunk)
            temp_path.replace(local_path)
            return True
        except (OSError, httpx.HTTPError, ApiError, ValueError, TypeError) as exc:
            logger.debug(
                f"Failed to download remote file {remote_path} from sandbox {base_url}: {exc}"
            )
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        finally:
            if http_client:
                http_client.close()

    async def _async_download_remote_file(
        self,
        *,
        sandbox_url: str,
        remote_path: str,
        local_path: Path,
    ) -> bool:
        return await asyncio.to_thread(
            self._download_sandbox_file_to_local,
            sandbox_url=sandbox_url,
            remote_path=remote_path,
            local_path=local_path,
            timeout=self._remote_artifact_timeout,
        )

    def _create_local_task_file(self, job_id: str, task_description: str) -> Path:
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        task_path = job_dir / f"{job_id}.task"
        task_path.write_text(task_description, encoding="utf-8")
        try:
            os.chmod(task_path, 0o600)
        except OSError:
            pass
        return task_path

    def _create_local_env_file(self, job_id: str, env: Dict[str, str]) -> Path:
        env_path = self.jobs_dir / job_id / "env.json"
        env_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_env = self._normalize_env(env)
        with open(env_path, "w", encoding="utf-8") as env_file:
            json.dump(normalized_env, env_file, ensure_ascii=False, indent=2)
        try:
            os.chmod(env_path, 0o600)
        except OSError:
            pass
        return env_path

    async def _upload_task_description_file(
        self,
        *,
        sandbox_url: str,
        job_id: str,
        task_description: str,
    ) -> str:
        remote_path = self._build_remote_task_path(job_id)
        http_client = httpx.AsyncClient(timeout=self._remote_artifact_timeout)
        sandbox_client = AsyncSandbox(
            base_url=sandbox_url.rstrip("/"),
            timeout=self._remote_artifact_timeout,
            httpx_client=http_client,
        )
        try:
            upload_response = await sandbox_client.file.upload_file(
                file=(f"{job_id}.task", task_description.encode("utf-8"), "text/plain"),
                path=remote_path,
            )
        finally:
            await http_client.aclose()
        if upload_response.success is False:
            message = upload_response.message or "sandbox upload failed"
            raise RuntimeError(f"Sandbox task upload failed: {message}")
        upload_data = upload_response.data
        if not upload_data or not upload_data.success:
            raise RuntimeError("Sandbox task upload returned no data")
        return upload_data.file_path or remote_path

    async def _upload_env_file(
        self,
        *,
        sandbox_url: str,
        job_id: str,
        env: Dict[str, str],
    ) -> str:
        remote_path = self._build_remote_env_path(job_id)
        normalized_env = self._normalize_env(env)
        payload = json.dumps(normalized_env, ensure_ascii=False).encode("utf-8")
        http_client = httpx.AsyncClient(timeout=self._remote_artifact_timeout)
        sandbox_client = AsyncSandbox(
            base_url=sandbox_url.rstrip("/"),
            timeout=self._remote_artifact_timeout,
            httpx_client=http_client,
        )
        try:
            upload_response = await sandbox_client.file.upload_file(
                file=(f"{job_id}.env.json", payload, "application/json"),
                path=remote_path,
            )
        finally:
            await http_client.aclose()
        if upload_response.success is False:
            message = upload_response.message or "sandbox upload failed"
            raise RuntimeError(f"Sandbox env upload failed: {message}")
        upload_data = upload_response.data
        if not upload_data or not upload_data.success:
            raise RuntimeError("Sandbox env upload returned no data")
        return upload_data.file_path or remote_path

    def _create_runner(
        self,
        job: Job,
        command: List[str],
        env: Dict[str, str],
        log_path: Path,
        remote_log_path: Optional[str] = None,
    ) -> BaseRunner:
        if job.sandbox_url:
            if not remote_log_path:
                raise ValueError("remote_log_path must be provided for sandbox jobs")
            return SandboxRunner(
                sandbox_url=job.sandbox_url,
                command=command,
                log_path=log_path,
                remote_log_path=remote_log_path,
                session_id=job.job_id,
            )
        return SubprocessRunner(
            command=command,
            log_path=log_path,
            env=env,
            cwd=Path.cwd(),
        )

    def create_job(
        self,
        task_description: str,
        max_tasks: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
        sandbox_url: Optional[str] = None,
    ) -> Job:
        job_id = uuid.uuid4().hex[:16]
        job_env = dict(env_vars or {})
        resolved_sandbox_url = self._resolve_sandbox_url(sandbox_url)
        job = Job(
            job_id=job_id,
            task_description=task_description,
            max_tasks=max_tasks or 50,
            env_vars=job_env,
            sandbox_url=resolved_sandbox_url,
        )
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(exist_ok=True)
        request_data = {
            "task_description": task_description,
            "max_tasks": job.max_tasks,
            "created_at": job.created_at.isoformat(),
            "env_vars": job.env_vars,
            "sandbox_url": resolved_sandbox_url,
        }
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

    async def create_job_async(
        self,
        task_description: str,
        max_tasks: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
        sandbox_url: Optional[str] = None,
    ) -> Job:
        """Async version for proper test usage."""
        job_id = uuid.uuid4().hex[:16]
        job_env = dict(env_vars or {})
        resolved_sandbox_url = self._resolve_sandbox_url(sandbox_url)
        job = Job(
            job_id=job_id,
            task_description=task_description,
            max_tasks=max_tasks or 50,
            env_vars=job_env,
            sandbox_url=resolved_sandbox_url,
        )
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(exist_ok=True)
        request_data = {
            "task_description": task_description,
            "max_tasks": job.max_tasks,
            "created_at": job.created_at.isoformat(),
            "env_vars": job.env_vars,
            "sandbox_url": resolved_sandbox_url,
        }
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
            except (OSError, httpx.HTTPError, RuntimeError, ValueError, TypeError) as e:
                job.status = "FAILED"
                job.finished_at = datetime.now(timezone.utc)
                job.error = {"message": str(e), "type": type(e).__name__}
                self._persist_status(job)
                print(f"Job {job.job_id} failed to start: {e}")

    async def _execute_job(self, job: Job):
        if job.sandbox_url and not job.sandbox_log_path:
            job.sandbox_log_path = self._build_remote_sandbox_log_path(job.job_id)
        job.status = "STARTING"
        job.started_at = datetime.now(timezone.utc)
        self._persist_status(job)
        # Pre-generate a trace filename so clients can discover it immediately.
        # Use deterministic naming so trace IDs match job IDs (job_id.json).
        trace_filename = f"{job.job_id}.json"
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
        job_dir = self.jobs_dir / job.job_id
        task_file_arg: Optional[str] = None
        if job.sandbox_url:
            task_file_arg = await self._upload_task_description_file(
                sandbox_url=job.sandbox_url,
                job_id=job.job_id,
                task_description=job.task_description,
            )
        else:
            task_file_arg = str(self._create_local_task_file(job.job_id, job.task_description))
        if not task_file_arg:
            raise RuntimeError("Failed to prepare task description file")
        env = os.environ.copy()
        env.update(job.env_vars)
        env.setdefault("ORCHESTRATOR_JOBS_DIR", str(self.jobs_dir))
        env["DOCFLOW_JOB_ID"] = job.job_id
        if job.sandbox_url:
            env_file_arg = await self._upload_env_file(
                sandbox_url=job.sandbox_url,
                job_id=job.job_id,
                env=env,
            )
        else:
            env_file_arg = str(self._create_local_env_file(job.job_id, env))
        if not env_file_arg:
            raise RuntimeError("Failed to prepare environment file")
        cmd = [
            "python", "-u", "-m", runner_module,
            "--job-id", job.job_id,
            "--task-file", task_file_arg,
            "--max-tasks", str(job.max_tasks),
            "--trace-file", trace_filename,
            "--context-file", str(job_dir / "context.json"),
            "--env-file", env_file_arg,
        ]
        log_path = job_dir / "engine_stdout.log"

        remote_log_path = job.sandbox_log_path if job.sandbox_url else None
        runner = self._create_runner(job, cmd, env, log_path, remote_log_path=remote_log_path)
        self._runners[job.job_id] = runner
        runner_result: Optional[RunnerResult] = None
        try:
            start_info = await runner.start()
            job.pid = start_info.pid
            job.sandbox_session_id = start_info.sandbox_session_id
            job.status = "RUNNING"
            self._persist_status(job)
            print(f"Job {job.job_id} started with PID {job.pid} sandbox_session_id={job.sandbox_session_id}")
            runner_result = await runner.wait()
        finally:
            self._runners.pop(job.job_id, None)

        if job.sandbox_url:
            await self.sync_job_context(job.job_id, force=True)
            for tf in job.trace_files:
                await self.sync_trace_file(tf, job_id=job.job_id, force=True)

        if runner_result.log_output is not None:
            with open(log_path, 'w', encoding='utf-8') as log_file:
                log_file.write(runner_result.log_output)

        exit_code = runner_result.exit_code if runner_result else 1
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
        runner = self._runners.get(job_id)
        cancelled = False
        if runner:
            cancelled = runner.cancel()
        elif job.pid:
            try:
                os.kill(job.pid, signal.SIGTERM)
                cancelled = True
            except (ProcessLookupError, PermissionError):
                cancelled = True
        elif job.sandbox_url and job.sandbox_session_id:
            cancelled = SandboxRunner.kill_session(
                sandbox_url=job.sandbox_url,
                session_id=job.sandbox_session_id,
                timeout=30.0,
            )

        if cancelled:
            job.status = "CANCELLED"
            job.finished_at = datetime.now(timezone.utc)
            self._persist_status(job)
        return cancelled

    def get_job_logs(self, job_id: str, tail_lines: Optional[int] = None) -> Optional[str]:
        logger.info("get_job_logs request job_id=%s tail_lines=%s", job_id, tail_lines)
        job_dir = self.jobs_dir / job_id
        log_file = job_dir / "engine_stdout.log"

        job = self._jobs.get(job_id)
        if job and job.sandbox_url and job.sandbox_log_path and job.status in ("STARTING", "RUNNING"):
            logger.debug(
                "Attempting sandbox tail job_id=%s status=%s session=%s remote_log=%s",
                job_id,
                job.status,
                job.sandbox_session_id,
                job.sandbox_log_path,
            )
            remote_output = SandboxRunner.tail_remote_log(
                sandbox_url=job.sandbox_url,
                log_path=job.sandbox_log_path,
                tail_lines=tail_lines,
                timeout=30.0,
            )
            if remote_output is not None:
                return remote_output
            logger.warning("Sandbox tail returned None for job_id=%s", job_id)

        if not log_file.exists():
            logger.debug("Local log file missing for job_id=%s path=%s", job_id, log_file)
            return None
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                if tail_lines:
                    lines = f.readlines()
                    return ''.join(lines[-tail_lines:])
                return f.read()
        except (OSError, UnicodeDecodeError) as exc:
            logger.exception("Failed reading log file for job_id=%s path=%s", job_id, log_file)
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
