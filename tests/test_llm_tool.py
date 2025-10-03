import os
import asyncio
from tools.llm_tool import LLMTool


def test_llm_tool_model_override(monkeypatch):
    """Ensure passing 'model' in parameters overrides LLMTool.model.

    We monkeypatch the AsyncOpenAI client's streaming create method to capture the
    model argument actually used in the API call without performing any network IO.

    Expected (after feature is implemented): second call uses override model.
    Currently FAILS because execute() ignores parameters['model'].
    """
    # Ensure we are in mock integration mode so _test_connection short-circuits
    monkeypatch.setenv("INTEGRATION_TEST_MODE", "MOCK")

    tool = LLMTool()

    captured_models: list[str] = []

    class DummyDelta:
        def __init__(self, content):
            self.content = content

    class DummyChoice:
        def __init__(self, content):
            self.delta = DummyDelta(content)

    class DummyChunk:
        def __init__(self, content):
            self.choices = [DummyChoice(content)]

    class DummyStream:
        def __init__(self):
            self._parts = ["Test ", "content"]
            self._i = 0
        def __aiter__(self):
            return self
        async def __anext__(self):
            if self._i >= len(self._parts):
                raise StopAsyncIteration
            part = self._parts[self._i]
            self._i += 1
            return DummyChunk(part)

    async def fake_create(**kwargs):  # type: ignore
        captured_models.append(kwargs.get("model"))
        return DummyStream()

    # Patch the underlying OpenAI create method
    monkeypatch.setattr(tool.client.chat.completions, "create", fake_create)

    async def run():
        await tool.execute({"prompt": "Hello"})  # should use default tool.model
        await tool.execute({"prompt": "Hi", "model": "custom-model-123"})  # should use override

    # Prefer asyncio.run to avoid DeprecationWarning about no current loop
    # If already inside an event loop (rare in pytest default), fallback to creating a new loop
    try:
        asyncio.run(run())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(run())
            finally:
                loop.close()
        else:
            raise

    assert len(captured_models) == 2, "Should have captured two model invocations"
    assert captured_models[0] == tool.model, "First call should use default model"
    # This assertion will FAIL until feature implemented (currently uses tool.model again)
    assert captured_models[1] == "custom-model-123", (
        f"Expected override model 'custom-model-123' but got '{captured_models[1]}' - override feature missing"
    )
