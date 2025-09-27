#!/usr/bin/env python3
"""Runner script for executing doc engine jobs."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import doc_execute_engine
sys.path.insert(0, str(Path(__file__).parent.parent))

from doc_execute_engine import DocExecuteEngine


async def run_job(job_id: str, task: str, max_tasks: int, trace_file: str | None):
    """Run a single job with the doc execute engine.

    Errors are allowed to propagate so the orchestrator can mark the job failed via exit code.
    """
    engine = DocExecuteEngine(
        max_tasks=max_tasks,
        enable_tracing=True,
        trace_output_dir="traces",
        trace_session_file=trace_file
    )

    engine.load_context(load_if_exists=False)
    await engine.start(task)

    job_dir = Path("jobs") / job_id
    context_file = job_dir / "context.json"
    with open(context_file, 'w', encoding='utf-8') as f:
        json.dump(engine.context, f, ensure_ascii=False, indent=2)

    print(f"Job {job_id} completed successfully")


def main():
    """Main entry point for job runner."""
    parser = argparse.ArgumentParser(description="Run a doc engine job")
    parser.add_argument("--job-id", required=True, help="Job ID")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--max-tasks", type=int, default=50, help="Maximum number of tasks")
    parser.add_argument("--trace-file", required=False, help="Pre-created trace session file name (filename or path)")
    
    args = parser.parse_args()
    
    print(f"Starting job {args.job_id} with task: {args.task}")
    
    # Run the job
    asyncio.run(run_job(args.job_id, args.task, args.max_tasks, args.trace_file))


if __name__ == "__main__":
    main()