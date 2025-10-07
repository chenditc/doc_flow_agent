#!/usr/bin/env python3
"""Tests for skip_new_task_generation flag in SOP documents and task propagation"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from doc_execute_engine import DocExecuteEngine, Task, PendingTask
from sop_document import SOPDocument

@pytest.mark.asyncio
async def test_skip_new_task_generation_flag_propagation():
    engine = DocExecuteEngine(enable_tracing=False)

    # Create a fake SOPDocument with skip flag true
    sop_doc = SOPDocument(
        doc_id="tools/llm",
        description="Test LLM tool",
        aliases=[],
        tool={"tool_id": "LLM", "parameters": {"prompt": "Hello"}},
        input_json_path={},
        output_json_path="$.test_output",
        body="",
        parameters={},
        input_description={},
        output_description="Test output",
        result_validation_rule="",
        skip_new_task_generation=True
    )

    pending = PendingTask(description="Follow llm.md to say hello")

    # Patch loader to return our sop_doc
    with patch.object(engine, 'load_sop_document', return_value=sop_doc):
        # Patch parser to return doc id directly
        with patch.object(engine.sop_parser, 'parse_sop_doc_id_from_description', AsyncMock(return_value=(sop_doc.doc_id, ""))):
            task = await engine.create_task_from_description(pending)

    assert task.skip_new_task_generation is True

@pytest.mark.asyncio
async def test_execute_task_skips_generation_when_flag_true():
    engine = DocExecuteEngine(enable_tracing=False)

    # Prepare task directly (bypass SOP parsing complexity)
    task = Task(
        task_id="skip-task",
        description="Skip new task generation test",
        sop_doc_id="tools/llm",
        tool={"tool_id": "LLM", "parameters": {"prompt": "Test"}},
        input_json_path={},
        output_json_path="$.skip_test_output",
        output_description="Skip test output",
        result_validation_rule="",
        skip_new_task_generation=True
    )

    # Stub tool execution to return predictable output for first call and evaluation tool call
    async def fake_llm_execute(params, **kwargs):
        # If tools schema includes evaluate_and_summarize_subtree, return tool call result
        tools = params.get("tools") or []
        for t in tools:
            if isinstance(t, dict) and t.get("function", {}).get("name") == "evaluate_and_summarize_subtree":
                return {
                    "tool_calls": [
                        {
                            "name": "evaluate_and_summarize_subtree",
                            "arguments": {
                                "requirements_met": True,
                                "summary": "Completed",
                                "deliverable_output_path": ["$.skip_test_output"]
                            }
                        }
                    ],
                    "content": "Evaluation complete"
                }
        return {"content": "Done"}
    engine.tools["LLM"].execute = AsyncMock(side_effect=fake_llm_execute)

    # Patch parse_new_tasks_from_output to ensure it would produce tasks if called
    with patch.object(engine, 'parse_new_tasks_from_output', AsyncMock(return_value=[PendingTask(description="Should not appear")])) as mock_parse:
        new_tasks = await engine.execute_task(task)

    # Should skip calling parse_new_tasks_from_output
    mock_parse.assert_not_called()
    assert new_tasks == []
    assert engine.last_task_output == {"content": "Done"}

if __name__ == "__main__":
    pytest.main([__file__])
