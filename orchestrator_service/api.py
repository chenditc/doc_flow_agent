"""FastAPI application for orchestrator service."""

from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .manager import ExecutionManager
from .models import Job


# Request/Response models
class SubmitJobRequest(BaseModel):
    task_description: str = Field(..., min_length=1, max_length=10000)
    max_tasks: Optional[int] = Field(default=50, ge=1, le=1000)


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


class CancelJobResponse(BaseModel):
    job_id: str
    status: str
    cancelled: bool


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
        max_tasks=request.max_tasks
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
            error=job.error
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
        error=job.error
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


@app.get("/jobs/{job_id}/context")
async def get_job_context(job_id: str):
    """Get job execution context."""
    from pathlib import Path
    import json
    
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    context_file = Path("jobs") / job_id / "context.json"
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