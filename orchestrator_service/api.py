"""FastAPI application for orchestrator service."""

import json
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from agent_sandbox.core.api_error import ApiError

from .manager import ExecutionManager
from .models import Job


# Request/Response models
class SubmitJobRequest(BaseModel):
    task_description: str = Field(..., min_length=1, max_length=10000)
    max_tasks: Optional[int] = Field(default=50, ge=1, le=1000)
    env_vars: Optional[Dict[str, str]] = Field(default=None)
    sandbox_url: Optional[str] = Field(default=None, description="Remote sandbox base URL; if omitted and DEFAULT_SANDBOX_URL is set, sandbox will be used")

    @validator("env_vars")
    def validate_env_vars(cls, value: Optional[Dict[str, str]]):
        if value is None:
            return value
        invalid_keys = [key for key in value.keys() if not isinstance(key, str) or not key]
        if invalid_keys:
            raise ValueError("Environment variable keys must be non-empty strings")
        return value


class SubmitJobResponse(BaseModel):
    job_id: str
    status: str


class JobResponse(BaseModel):
    job_id: str
    task_description: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    trace_files: List[str]
    max_tasks: Optional[int]
    error: Optional[dict] = None
    env_vars: Dict[str, str] = Field(default_factory=dict)
    sandbox_url: Optional[str] = None


class CancelJobResponse(BaseModel):
    job_id: str
    status: str
    cancelled: bool


class TraceSyncResponse(BaseModel):
    trace_id: str
    job_id: str
    synced: bool
    job_status: str
    is_terminal: bool


# Initialize FastAPI app and manager
app = FastAPI(
    title="Doc Flow Agent Orchestrator",
    description="API for managing concurrent document execution tasks",
    version="1.0.0"
)

manager = ExecutionManager()


@app.post("/jobs", response_model=SubmitJobResponse)
async def submit_job(request: SubmitJobRequest):
    """Submit a new job for execution."""
    job = manager.create_job(
        task_description=request.task_description,
        max_tasks=request.max_tasks,
        env_vars=request.env_vars,
        sandbox_url=request.sandbox_url,
    )
    return SubmitJobResponse(job_id=job.job_id, status=job.status)


@app.get("/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of results")
):
    """List all jobs with optional filtering."""
    jobs = manager.list_jobs()
    
    # Filter by status if specified
    if status:
        jobs = [job for job in jobs if job.status == status]
    
    # Apply limit if specified (after filtering, ordering already descending)
    if limit:
        jobs = jobs[:limit]
    
    # Convert to response format
    return [
        JobResponse(
            job_id=job.job_id,
            task_description=job.task_description,
            status=job.status,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.finished_at.isoformat() if job.finished_at else None,
            trace_files=job.trace_files,
            max_tasks=job.max_tasks,
            error=job.error,
            env_vars=job.env_vars,
            sandbox_url=job.sandbox_url,
        )
        for job in jobs
    ]


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get details of a specific job."""
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(
        job_id=job.job_id,
        task_description=job.task_description,
        status=job.status,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        trace_files=job.trace_files,
        max_tasks=job.max_tasks,
        error=job.error,
        env_vars=job.env_vars,
        sandbox_url=job.sandbox_url,
    )


@app.post("/jobs/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(job_id: str):
    """Cancel a running job."""
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    cancelled = manager.cancel_job(job_id)
    
    return CancelJobResponse(
        job_id=job_id,
        status=job.status,
        cancelled=cancelled
    )


@app.get("/jobs/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    tail: Optional[int] = Query(None, ge=1, le=10000, description="Number of lines from end")
):
    """Get job execution logs."""
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    logs = manager.get_job_logs(job_id, tail_lines=tail)
    if logs is None:
        raise HTTPException(status_code=404, detail="Logs not found")
    
    return {"job_id": job_id, "logs": logs}


@app.post("/traces/{trace_id}/sync", response_model=TraceSyncResponse)
async def sync_trace_file(trace_id: str, force: bool = Query(False, description="Force download even if file exists locally")):
    """Request a trace file refresh from remote sandbox (if applicable)."""
    normalized = trace_id.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Trace ID is required")
    if normalized.endswith(".json"):
        normalized = normalized[:-5]
    trace_filename = f"{normalized}.json"
    job_id = normalized
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trace not associated with any known job")
    try:
        synced = await manager.sync_trace_file(
            trace_filename,
            job_id=job.job_id,
            force=force or job.status in ("RUNNING", "STARTING"),
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to sync trace: {exc}") from exc
    job_status = job.status or "UNKNOWN"
    is_terminal = job_status in ("COMPLETED", "FAILED", "CANCELLED")
    return TraceSyncResponse(
        trace_id=normalized,
        job_id=job.job_id,
        synced=synced,
        job_status=job_status,
        is_terminal=is_terminal,
    )


@app.get("/sandbox/{job_id}/{requested_path:path}")
async def get_sandbox_file(
    job_id: str,
    requested_path: str,
):
    """Proxy file download requests from sandbox workdir via orchestrator."""
    try:
        resolution = manager.resolve_sandbox_file_request(job_id, requested_path)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    media_type, _ = mimetypes.guess_type(resolution["filename"])

    if resolution["mode"] == "local":
        return FileResponse(
            path=str(resolution["local_path"]),
            filename=resolution["filename"],
            media_type=media_type or "application/octet-stream",
        )

    async def empty_stream():  # pragma: no cover - trivial
        if False:
            yield b""

    stream_iter = manager.stream_remote_sandbox_file(
        resolution["job"],
        resolution["sandbox_path"],
    )
    try:
        first_chunk = await stream_iter.__anext__()
    except StopAsyncIteration:
        await stream_iter.aclose()
        return StreamingResponse(
            empty_stream(),
            media_type=media_type or "application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=\"{resolution['filename']}\""},
        )
    except FileNotFoundError:
        await stream_iter.aclose()
        raise HTTPException(status_code=404, detail="File not found")
    except ApiError as exc:
        await stream_iter.aclose()
        raise HTTPException(status_code=502, detail=f"Sandbox download failed: {exc}")

    async def stream_file():
        try:
            yield first_chunk
            async for chunk in stream_iter:
                yield chunk
        finally:
            await stream_iter.aclose()

    return StreamingResponse(
        stream_file(),
        media_type=media_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{resolution['filename']}\""},
    )


@app.get("/jobs/{job_id}/context")
async def get_job_context(job_id: str, refresh: bool = Query(False, description="Force refresh from sandbox if running")):
    """Get job execution context."""
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        await manager.sync_job_context(
            job_id,
            force=refresh or job.status in ("RUNNING", "STARTING"),
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"Failed to sync context: {exc}") from exc

    context_file = manager.jobs_dir / job_id / "context.json"
    if not context_file.exists():
        raise HTTPException(status_code=404, detail="Context not found")
    
    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            context = json.load(f)
        return {"job_id": job_id, "context": context}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read context: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    jobs = manager.list_jobs()
    active_jobs = len([job for job in jobs if job.status in ("QUEUED", "STARTING", "RUNNING")])
    
    return {
        "status": "ok",
        "active_jobs": active_jobs,
        "total_jobs": len(jobs)
    }
