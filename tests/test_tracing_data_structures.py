import pytest
from tracing import ExecutionStatus, LLMCall, ToolCall, SopResolutionPhase, JsonPathGeneration, TaskCreationPhase, TaskExecutionPhase, ContextUpdatePhase

def test_execution_status_enum():
    assert ExecutionStatus.STARTED.value == "started"
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert ExecutionStatus.FAILED.value == "failed"
    assert ExecutionStatus.INTERRUPTED.value == "interrupted"
    assert ExecutionStatus.RETRYING.value == "retrying"

def test_llm_call_dataclass():
    llm = LLMCall(tool_call_id="id1", prompt="p", response="r", start_time="t1", end_time="t2", model="gpt", token_usage={"input": 10})
    assert llm.tool_call_id == "id1"
    assert llm.prompt == "p"
    assert llm.response == "r"
    assert llm.start_time == "t1"
    assert llm.end_time == "t2"
    assert llm.model == "gpt"
    assert llm.token_usage["input"] == 10

def test_tool_call_dataclass():
    tc = ToolCall(tool_call_id="tcid", tool_id="tid", parameters={"a": 1}, output="out", start_time="t1", end_time="t2", status=ExecutionStatus.COMPLETED, error=None)
    assert tc.tool_call_id == "tcid"
    assert tc.tool_id == "tid"
    assert tc.parameters["a"] == 1
    assert tc.output == "out"
    assert tc.status == ExecutionStatus.COMPLETED
    assert tc.error is None

def test_sop_resolution_phase():
    phase = SopResolutionPhase(start_time="t1")
    assert phase.status == ExecutionStatus.STARTED
    assert phase.start_time == "t1"
    assert phase.end_time is None

def test_json_path_generation():
    jpath = JsonPathGeneration(field_name="f", description="desc")
    assert jpath.field_name == "f"
    assert jpath.description == "desc"
    assert jpath.llm_calls == []
    assert jpath.generated_path is None
    assert jpath.extracted_value is None
    assert jpath.error is None

def test_task_creation_phase():
    tcp = TaskCreationPhase(start_time="t1")
    assert tcp.status == ExecutionStatus.STARTED
    assert tcp.start_time == "t1"
    assert isinstance(tcp.input_field_extractions, dict)
    assert tcp.output_path_generation is None
    assert tcp.error is None

def test_task_execution_phase():
    tep = TaskExecutionPhase(start_time="t1")
    assert tep.status == ExecutionStatus.STARTED
    assert tep.start_time == "t1"
    assert tep.error is None

def test_context_update_phase():
    cup = ContextUpdatePhase(start_time="t1")
    assert cup.status == ExecutionStatus.STARTED
    assert cup.start_time == "t1"
    assert isinstance(cup.updated_paths, list)
    assert isinstance(cup.removed_temp_keys, list)
    assert cup.error is None
