"""A very small runner used only for fast orchestration tests.

It simulates work by sleeping briefly and writing a deterministic context.json.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path


async def main_async(job_id: str, task: str, sleep: float):
    await asyncio.sleep(sleep)
    job_dir = Path("jobs") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    context_file = job_dir / "context.json"
    context = {"fake_runner": True, "task": task, "status": "done"}
    context_file.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"FAKE RUNNER completed job {job_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--max-tasks", required=False)
    parser.add_argument("--sleep", type=float, default=0.05)
    parser.add_argument("--trace-file", required=False, help="Pre-created trace session file (ignored by fake runner)")
    args = parser.parse_args()
    # Allow environment variable override for even faster tests
    sleep_override = os.getenv("FAKE_RUNNER_SLEEP")
    if sleep_override:
        try:
            args.sleep = float(sleep_override)
        except ValueError:
            pass
    asyncio.run(main_async(args.job_id, args.task, args.sleep))


if __name__ == "__main__":  # pragma: no cover
    main()
