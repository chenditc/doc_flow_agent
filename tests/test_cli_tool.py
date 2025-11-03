import unittest
import asyncio
import os
import sys
import json
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.cli_tool import CLITool
from tools.llm_tool import LLMTool
from integration_test_framework import (
    IntegrationTestBase,
    IntegrationTestMode,
    get_test_mode,
    print_test_mode_info,
)


class TestCLITool(unittest.TestCase):
    """Integration tests for CLITool supporting both explicit and generated command modes."""

    def setUp(self):
        self.test_mode = get_test_mode()
        print_test_mode_info(self.test_mode)
        test_name = f"cli_tool_{self._testMethodName}"
        self.integration_test = IntegrationTestBase(
            test_name=test_name,
            mode=self.test_mode
        )
        self.llm_tool = self.integration_test.wrap_tool(LLMTool())
        self.tool = CLITool(llm_tool=self.llm_tool)

    def tearDown(self):
        if self.test_mode == IntegrationTestMode.REAL or self.test_mode == IntegrationTestMode.MOCK_THEN_REAL:
            self.integration_test.save_test_data()

    def test_explicit_command(self):
        async def run_test():
            # If sandbox URL is provided in env, don't mock; otherwise, mock HTTP call
            sandbox_env = os.getenv("WORKSPACE_SANDBOX_URL") or os.getenv("DEFAULT_WORKSPACE_SANDBOX_URL")
            if sandbox_env:
                params = {"command": "echo 'hello world'"}
                result = await self.tool.execute(params)
                # We cannot guarantee exact output in real env; at least assert keys exist
                self.assertIn("stdout", result)
                self.assertIn("returncode", result)
            else:
                with patch.dict(os.environ, {"DEFAULT_WORKSPACE_SANDBOX_URL": "http://localhost:8080"}, clear=False):
                    class FakeResp:
                        def __init__(self, status: int, body: dict):
                            self.status_code = status
                            self._body = body
                        def json(self):
                            return self._body
                        async def aread(self):
                            return json.dumps(self._body).encode()

                    # Conform to new API schema
                    fake_body = {
                        "success": True,
                        "message": "ok",
                        "data": {"session_id": "s1", "command": "echo", "status": "finished", "output": "hello world\n", "console": [], "exit_code": 0},
                    }
                    with patch("tools.cli_tool.httpx.AsyncClient.post", new=AsyncMock(return_value=FakeResp(200, fake_body))):
                        params = {"command": "echo 'hello world'"}
                        result = await self.tool.execute(params)
                        self.assertIn("hello world", result["stdout"])  # Check mocked stdout
                        self.assertEqual(result["returncode"], 0)
        asyncio.run(run_test())

    def test_generated_command(self):
        # Use a lightweight fake LLM to avoid external dependency for this unit-style test
        class FakeLLMTool:
            tool_id = "LLM"

            async def execute(self, parameters):
                # Always return a safe echo command via tool call schema
                return {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "fake-1",
                            "name": "generate_command",
                            "arguments": {"command": "echo 'CLI Test Success'"}
                        }
                    ]
                }

        fake_tool = CLITool(llm_tool=FakeLLMTool())

        async def run_test():
            sandbox_env = os.getenv("WORKSPACE_SANDBOX_URL") or os.getenv("DEFAULT_WORKSPACE_SANDBOX_URL")
            if sandbox_env:
                params = {"task_description": "Print the phrase CLI Test Success"}
                result = await fake_tool.execute(params)
                self.assertEqual(result.get("executed_command"), "echo 'CLI Test Success'")
                self.assertIn("stdout", result)
                self.assertIn("returncode", result)
            else:
                with patch.dict(os.environ, {"DEFAULT_WORKSPACE_SANDBOX_URL": "http://localhost:8080"}, clear=False):
                    class FakeResp:
                        def __init__(self, status: int, body: dict):
                            self.status_code = status
                            self._body = body
                        def json(self):
                            return self._body
                        async def aread(self):
                            return json.dumps(self._body).encode()

                    fake_body = {
                        "success": True,
                        "message": "ok",
                        "data": {"session_id": "s1", "command": "echo", "status": "finished", "output": "CLI Test Success\n", "console": [], "exit_code": 0},
                    }
                    with patch("tools.cli_tool.httpx.AsyncClient.post", new=AsyncMock(return_value=FakeResp(200, fake_body))):
                        params = {
                            "task_description": "Print the phrase CLI Test Success"
                        }
                        result = await fake_tool.execute(params)
                        self.assertEqual(result.get("executed_command"), "echo 'CLI Test Success'")
                        self.assertIn("CLI Test Success", result["stdout"])
                        self.assertEqual(result["returncode"], 0)
        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
