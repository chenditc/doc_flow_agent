#!/usr/bin/env python3
"""Runner script for executing doc engine jobs."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from orchestrator_service.env_file import load_env_file

# Add parent directory to path so we can import doc_execute_engine
sys.path.insert(0, str(Path(__file__).parent.parent))

from doc_execute_engine import DocExecuteEngine


async def run_job(job_id: str, task: str, max_tasks: int, trace_file: str | None, context_file: str | None):
    """Run a single job with the doc execute engine.

    Errors are allowed to propagate so the orchestrator can mark the job failed via exit code.
    """
    context_path = Path(context_file) if context_file else Path("jobs") / job_id / "context.json"
    engine = DocExecuteEngine(
        max_tasks=max_tasks,
        enable_tracing=True,
        trace_output_dir="traces",
        trace_session_file=trace_file,
        context_file=context_path,
    )

    engine.load_context(load_if_exists=False)
    await engine.start(task)

    context_path.parent.mkdir(parents=True, exist_ok=True)
    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(engine.context, f, ensure_ascii=False, indent=2)

    print(f"Job {job_id} completed successfully")


def _load_task_description(task_arg: Optional[str], task_file: Optional[str]) -> str:
    """Load the task description from a file when provided."""
    if task_file:
        try:
            return Path(task_file).read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - treated as fatal
            raise RuntimeError(f"Failed to read task description file {task_file}: {exc}") from exc
    if task_arg is not None:
        return task_arg
    raise ValueError("Either --task-file or --task must be provided")


def main():
    """Main entry point for job runner."""
    parser = argparse.ArgumentParser(description="Run a doc engine job")
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--task", required=False, help="Task description (deprecated, prefer --task-file)")
    parser.add_argument("--task-file", required=False, help="Path to file containing the task description")
    parser.add_argument("--max-tasks", type=int, default=50, help="Maximum number of tasks")
    parser.add_argument("--trace-file", required=False, help="Pre-created trace session file name (filename or path)")
    parser.add_argument("--context-file", required=False, help="Path to persist job context JSON")
    parser.add_argument("--env-file", required=False, help="Path to JSON file containing environment variables")
    
    args = parser.parse_args()

    load_env_file(args.env_file)
    
    task_text = _load_task_description(args.task, args.task_file)
    print(f"Starting job {args.job_id} with task: {task_text}")
    
    # Run the job
    asyncio.run(run_job(args.job_id, task_text, args.max_tasks, args.trace_file, args.context_file))


if __name__ == "__main__":
    main()
