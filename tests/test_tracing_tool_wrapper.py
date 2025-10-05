import pytest

from tracing_wrappers import TracingToolWrapper
from tracing import ExecutionTracer
from tools.base_tool import BaseTool


class DummyTool(BaseTool):
    tool_id = "DUMMY"

    def __init__(self):
        self.custom_attribute = "custom-value"
        self.invocations = 0

    async def execute(self, parameters, sop_doc_body=None):  # pragma: no cover - trivial
        self.invocations += 1
        return {"echo": parameters}

    def get_result_validation_hint(self):  # pragma: no cover - trivial
        return "hint"


class DummyTracer(ExecutionTracer):
    def __init__(self):  # type: ignore[no-untyped-def]
        # Bypass parent init if heavy; store logs in memory
        self.tool_calls = []

    def log_tool_call(self, **data):  # type: ignore[no-untyped-def]
        self.tool_calls.append(data)


@pytest.mark.asyncio
async def test_attribute_delegation():
    tool = DummyTool()
    tracer = DummyTracer()
    wrapper = TracingToolWrapper(tool, tracer)

    # Attribute defined only on underlying tool
    assert wrapper.custom_attribute == "custom-value"

    # Method defined on wrapper should still work
    assert wrapper.get_result_validation_hint() == "hint"

    # Execute still functions
    result = await wrapper.execute({"k": 1})
    assert result == {"echo": {"k": 1}}
    assert tool.invocations == 1

    # Ensure tracing recorded
    assert tracer.tool_calls, "Expected a tool call to be logged"  # at least one entry
