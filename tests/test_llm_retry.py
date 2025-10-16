import pytest
import asyncio

from tools.llm_tool import LLMTool
from tools.retry_strategies import SimpleRetryStrategy, AppendValidationHintStrategy

class MockLLMTool(LLMTool):
    def __init__(self, responses):
        # Do not call parent network init; monkeypatch minimal attributes
        self.model = "mock-model"
        self.small_model = self.model
        self._responses = iter(responses)
    async def _raw_llm_call(self, parameters):  # override network call
        try:
            content = next(self._responses)
        except StopIteration:
            content = "FINAL"
        return {"content": content, "tool_calls": []}

@pytest.mark.asyncio
async def test_retry_success_second_attempt():
    # First attempt invalid JSON, second valid
    tool = MockLLMTool([
        "not json",
        "[\"a\", \"b\"]"  # valid JSON list second attempt
    ])
    def validator(resp):
        import json
        try:
            arr = json.loads(resp['content'])
        except Exception as e:
            raise ValueError("invalid json") from e
        if not isinstance(arr, list):
            raise ValueError("not list")
    result = await tool.execute(
        {"prompt": "test"},
        max_retries=1,
        validators=[validator],
        retry_strategies=[SimpleRetryStrategy()],
    )
    assert result['content'].startswith('["a"')

@pytest.mark.asyncio
async def test_retry_exhaust_all_strategies_fail():
    tool = MockLLMTool(["bad", "still bad", "nope"])
    def validator(resp):
        raise ValueError("always bad")
    with pytest.raises(ValueError):
        await tool.execute(
            {"prompt": "test"},
            max_retries=1,
            validators=[validator],
            retry_strategies=[SimpleRetryStrategy(), AppendValidationHintStrategy()],
        )

@pytest.mark.asyncio
async def test_append_hint_changes_prompt():
    # Capture prompts by inspecting strategy internal hints indirectly
    collected = []
    class CaptureTool(MockLLMTool):
        async def _raw_llm_call(self, parameters):
            collected.append(parameters['prompt'])
            return await super()._raw_llm_call(parameters)
    tool = CaptureTool(["bad", "bad again", "[\"ok\"]"])  # valid JSON third response
    def validator(resp):
        import json
        try:
            arr = json.loads(resp['content'])
        except Exception:
            raise ValueError("invalid json")
        if not isinstance(arr, list):
            raise ValueError("not list")
    await tool.execute(
        {"prompt": "BASE"},
        max_retries=2,
        validators=[validator],
        retry_strategies=[AppendValidationHintStrategy(), SimpleRetryStrategy()],
    )
    # Expect at least two prompts; second should contain Previous Response
    assert len(collected) >= 3
    # Second prompt should include appended hint from first failure
    assert '<Previous Invalid Response>' in collected[1]
