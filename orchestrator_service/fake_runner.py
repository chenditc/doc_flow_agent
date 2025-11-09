"""A very small runner used only for fast orchestration tests.

It simulates work by sleeping briefly and writing a deterministic context.json.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from orchestrator_service.env_file import load_env_file


async def main_async(job_id: str, task: str, sleep: float, context_file: str | None):
    await asyncio.sleep(sleep)
    if context_file:
        context_path = Path(context_file)
        job_dir = context_path.parent
    else:
        base_dir = os.getenv("ORCHESTRATOR_JOBS_DIR")
        job_root = Path(base_dir) if base_dir else Path("jobs")
        job_dir = job_root / job_id
        context_path = job_dir / "context.json"
    job_dir.mkdir(parents=True, exist_ok=True)
    request_env = {}
    request_file = job_dir / "request.json"
    if request_file.exists():
        try:
            request_data = json.loads(request_file.read_text(encoding="utf-8"))
            requested = request_data.get("env_vars") or {}
            request_env = {key: os.environ.get(key) for key in requested.keys()}
        except (OSError, json.JSONDecodeError):
            request_env = {}
    context = {"fake_runner": True, "task": task, "status": "done", "env_vars": request_env}
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FAKE RUNNER completed job {job_id}")


def _load_task_description(task_arg: Optional[str], task_file: Optional[str]) -> str:
    if task_file:
        try:
            return Path(task_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Failed to read task description file {task_file}: {exc}") from exc
    if task_arg is not None:
        return task_arg
    raise ValueError("Either --task-file or --task must be provided")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--task", required=False)
    parser.add_argument("--task-file", required=False)
    parser.add_argument("--max-tasks", required=False)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--trace-file", required=False, help="Pre-created trace session file (ignored by fake runner)")
    parser.add_argument("--context-file", required=False, help="Path to persist job context JSON (optional)")
    parser.add_argument("--env-file", required=False, help="Path to JSON file containing environment variables")
    args = parser.parse_args()
    load_env_file(args.env_file)
    # Allow environment variable override for even faster tests
    sleep_override = os.getenv("FAKE_RUNNER_SLEEP")
    if sleep_override:
        try:
            args.sleep = float(sleep_override)
        except ValueError:
            pass
    task_text = _load_task_description(args.task, args.task_file)
    asyncio.run(main_async(args.job_id, task_text, args.sleep, args.context_file))


if __name__ == "__main__":  # pragma: no cover
    main()
