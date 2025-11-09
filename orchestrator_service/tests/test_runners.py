import os
import sys
import uuid
from pathlib import Path

import httpx
import pytest

from orchestrator_service.manager import SandboxRunner, SubprocessRunner


@pytest.mark.asyncio
async def test_subprocess_runner_executes_command(tmp_path: Path):
    log_path = tmp_path / "subprocess.log"
    runner = SubprocessRunner(
        [sys.executable, "-c", "print('subprocess ok')"],
        log_path=log_path,
        env=os.environ.copy(),
        cwd=Path.cwd(),
    )
    start_info = await runner.start()
    assert start_info.pid is not None

    result = await runner.wait()
    assert result.exit_code == 0
    assert log_path.exists()
    assert "subprocess ok" in log_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_subprocess_runner_cancel(tmp_path: Path):
    log_path = tmp_path / "subprocess_cancel.log"
    runner = SubprocessRunner(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        log_path=log_path,
        env=os.environ.copy(),
        cwd=Path.cwd(),
    )
    await runner.start()
    cancelled = runner.cancel()
    assert cancelled is True
    result = await runner.wait()
    assert result.exit_code != 0
    assert log_path.exists()


@pytest.mark.asyncio
async def test_sandbox_runner_executes_command(tmp_path: Path):
    sandbox_url = "http://localhost:8080"
    if not await _is_sandbox_available(sandbox_url):
        pytest.skip("Sandbox service is not running on localhost:8080")

    log_path = tmp_path / "sandbox.log"
    remote_log_path = f"/tmp/doc_engine_logs/test_{uuid.uuid4().hex}.log"
    runner = SandboxRunner(
        sandbox_url=sandbox_url,
        command=["echo", "sandbox ok"],
        log_path=log_path,
        remote_log_path=remote_log_path,
    )
    start_info = await runner.start()
    assert start_info.sandbox_session_id is not None

    result = await runner.wait()
    assert result.exit_code == 0
    assert result.log_output is None
    if not log_path.exists():
        pytest.skip("Sandbox log download unavailable; verify sandbox file service is reachable.")
    assert "sandbox ok" in log_path.read_text(encoding="utf-8")
    tail_output = SandboxRunner.tail_remote_log(
        sandbox_url=sandbox_url,
        log_path=remote_log_path,
        tail_lines=5,
        timeout=5.0,
    )
    if tail_output is None:
        pytest.skip("Sandbox remote log tailing unavailable; verify sandbox file service is reachable.")
    assert "sandbox ok" in tail_output


async def _is_sandbox_available(sandbox_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            response = await client.get(f"{sandbox_url}/v1/openapi.json")
            return response.status_code == 200
    except (httpx.RequestError, httpx.HTTPStatusError):
        return False
