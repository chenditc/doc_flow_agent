#!/usr/bin/env python3
"""
Integration Test Framework with Save and Mock Features
Provides recording/playback capabilities for tool calls in integration tests
"""

import json
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.base_tool import BaseTool


class IntegrationTestMode(Enum):
    """Test execution modes"""
    REAL = "real"      # Record tool calls and save to file
    MOCK = "mock"      # Load tool calls from file and replay
    MOCK_THEN_REAL = "mock_then_real"  # Use mock if available, otherwise execute real call and record (progressively builds cache)


@dataclass
class ToolCallRecord:
    """Record of a tool call for playback"""
    tool_id: str
    parameters: Dict[str, Any]
    output: Any
    timestamp: str
    execution_time_ms: float
    parameters_hash: str  # Hash of parameters for lookup


@dataclass
class TestSession:
    """Complete test session data"""
    test_name: str
    mode: IntegrationTestMode
    timestamp: str
    tool_calls: List[ToolCallRecord]
    metadata: Dict[str, Any] = None


class TestDataManager:
    """Manages saving and loading of test data"""
    
    def __init__(self, test_data_dir: str = "tests/integration_data"):
        self.test_data_dir = Path(test_data_dir)
        self.test_data_dir.mkdir(exist_ok=True)
    
    def _get_test_data_path(self, test_name: str) -> Path:
        """Get path for test data file"""
        return self.test_data_dir / f"{test_name}_data.json"
    
    def _hash_parameters(self, tool_id: str, parameters: Dict[str, Any]) -> str:
        """Create consistent hash of tool call parameters"""
        # Sort parameters to ensure consistent hashing
        sorted_params = json.dumps(parameters, sort_keys=True, default=str)
        call_string = f"{tool_id}:{sorted_params}"
        print("[HASH]", call_string)
        return hashlib.sha256(call_string.encode()).hexdigest()[:16]
    
    def save_test_session(self, session: TestSession) -> None:
        """Save test session to file"""
        file_path = self._get_test_data_path(session.test_name)
    
        session_data = asdict(session)
        session_data['saved_at'] = datetime.now().isoformat()
        # Convert enum to string for JSON serialization
        session_data['mode'] = session.mode.value
        
        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)
        
        print(f"✅ Saved {len(session.tool_calls)} tool calls to {file_path}")
    
    def load_test_session(self, test_name: str) -> TestSession:
        """Load test session from file"""
        file_path = self._get_test_data_path(test_name)
        
        if not file_path.exists():
            raise FileNotFoundError(
                f"No recorded data found for test '{test_name}'. "
                f"Run the test in REAL mode first to generate test data."
            )
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Convert back to dataclass
        tool_calls = [ToolCallRecord(**call) for call in data['tool_calls']]
        session = TestSession(
            test_name=data['test_name'],
            mode=IntegrationTestMode(data['mode']),  # This should now work with string values
            timestamp=data['timestamp'],
            tool_calls=tool_calls,
            metadata=data.get('metadata', {})
        )
        
        print(f"📁 Loaded {len(session.tool_calls)} tool calls from {file_path}")
        return session
    
    def create_tool_call_record(self, tool_id: str, parameters: Dict[str, Any], 
                               output: Any, execution_time_ms: float) -> ToolCallRecord:
        """Create a tool call record"""
        return ToolCallRecord(
            tool_id=tool_id,
            parameters=parameters,
            output=output,
            timestamp=datetime.now().isoformat(),
            execution_time_ms=execution_time_ms,
            parameters_hash=self._hash_parameters(tool_id, parameters)
        )


class IntegrationTestProxy:
    """Proxy that wraps tools for recording/playback"""
    
    def __init__(self, tool: BaseTool, mode: IntegrationTestMode, data_manager: TestDataManager):
        self.tool = tool
        self.mode = mode
        self.data_manager = data_manager
        
        # Delegate attributes to wrapped tool
        self.tool_id = tool.tool_id
        
        # For mock mode, prepare lookup table
        self._mock_data: Dict[str, ToolCallRecord] = {}
        self._recorded_calls: List[ToolCallRecord] = []
        
    def load_mock_data(self, test_session: TestSession) -> None:
        """Load mock data for this tool from test session"""
        for call_record in test_session.tool_calls:
            if call_record.tool_id == self.tool_id:
                self._mock_data[call_record.parameters_hash] = call_record
        
        print(f"🎭 Loaded {len(self._mock_data)} mock responses for {self.tool_id}")

    # --- Internal helpers -------------------------------------------------
    def _build_parameters_with_sop(self, parameters: Dict[str, Any] | Any, sop_doc_body: Optional[str]) -> Dict[str, Any]:
        base = dict(parameters) if isinstance(parameters, dict) else {"params": parameters}
        base["__sop_doc_body"] = sop_doc_body
        return base

    def _record(self, parameters_with_sop: Dict[str, Any], output: Any, execution_time_ms: float) -> ToolCallRecord:
        record = self.data_manager.create_tool_call_record(
            tool_id=self.tool_id,
            parameters=parameters_with_sop,
            output=output,
            execution_time_ms=execution_time_ms,
        )
        self._recorded_calls.append(record)
        return record
    
    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None, **kwargs) -> Any:
        """Execute tool with recording/playback logic"""
        # Include sop_doc_body in hash so that calls differing by provided SOP body don't collide
        parameters_for_hash = self._build_parameters_with_sop(parameters, sop_doc_body)
        param_hash = self.data_manager._hash_parameters(self.tool_id, parameters_for_hash)

        # Backward compatibility: previously some tools (notably LLMTool) embedded retry control
        # keys inside the parameters dict. Existing MOCK recordings may include those keys, so the
        # new explicit-arg calls would miss the hash. If we are in MOCK / MOCK_THEN_REAL and miss,
        # attempt an alternate hash including legacy keys synthesized from kwargs.
        legacy_hash = None
        if self.tool_id == "LLM" and param_hash not in getattr(self, "_mock_data", {}):
            legacy_params = dict(parameters_for_hash)
            if "max_retries" in kwargs:
                legacy_params["max_retries"] = kwargs.get("max_retries")
            if "validators" in kwargs:
                # Validators were functions; we can't serialize them deterministically, so just store count
                legacy_params["validators"] = f"__len__:{len(kwargs.get('validators') or [])}"
            if "retry_strategies" in kwargs:
                legacy_params["retry_strategies"] = [type(s).__name__ for s in (kwargs.get("retry_strategies") or [])]
            legacy_hash = self.data_manager._hash_parameters(self.tool_id, legacy_params)
            if legacy_hash in getattr(self, "_mock_data", {}):
                param_hash = legacy_hash  # use legacy record
            elif self.mode in (IntegrationTestMode.MOCK, IntegrationTestMode.MOCK_THEN_REAL):
                # Final heuristic: if only a single mock record exists for LLM, reuse it (API evolution tolerance)
                mock_data = getattr(self, "_mock_data", {})
                if len(mock_data) == 1:
                    param_hash = next(iter(mock_data.keys()))
        
        if self.mode == IntegrationTestMode.REAL:
            return await self._execute_real(parameters, param_hash, sop_doc_body=sop_doc_body, **kwargs)
        elif self.mode == IntegrationTestMode.MOCK:
            return await self._execute_mock(parameters, param_hash, sop_doc_body=sop_doc_body, **kwargs)
        else:  # MOCK_THEN_REAL
            # Try mock first
            if param_hash in self._mock_data:
                result = await self._execute_mock(parameters, param_hash, sop_doc_body=sop_doc_body, **kwargs)
            else:
                # Fallback to real execution and record (acts like REAL for this call)
                print(f"🌀 [MOCK_THEN_REAL] Cache miss for {self.tool_id} (hash={param_hash}), executing real call...")
                result = await self._execute_real(parameters, param_hash, sop_doc_body=sop_doc_body, **kwargs)
            # Ensure we have the last recorded call in mock cache (both real and mock paths now recorded)
            if self._recorded_calls:
                self._mock_data[param_hash] = self._recorded_calls[-1]
            return result
    
    async def _execute_real(self, parameters: Dict[str, Any], param_hash: str, sop_doc_body: Optional[str] = None, **kwargs) -> Any:
        """Execute tool in real mode and record the result"""
        print(f"🔴 [REAL] {self.tool_id}: {str(parameters)[:100]}...")
        
        start_time = asyncio.get_event_loop().time()
        try:
            result = await self.tool.execute(parameters, sop_doc_body=sop_doc_body, **kwargs)
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            record_params = self._build_parameters_with_sop(parameters, sop_doc_body)
            self._record(record_params, result, execution_time)
            print(f"✅ [REAL] {self.tool_id}: Recorded response ({execution_time:.1f}ms)")
            return result
            
        except Exception as e:
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            record_params = self._build_parameters_with_sop(parameters, sop_doc_body)
            self._record(record_params, {"error": str(e), "error_type": type(e).__name__}, execution_time)
            print(f"❌ [REAL] {self.tool_id}: Recorded error ({execution_time:.1f}ms)")
            raise
    
    async def _execute_mock(self, parameters: Dict[str, Any], param_hash: str, sop_doc_body: Optional[str] = None, **kwargs) -> Any:
        """Execute tool in mock mode using recorded data; also record playback in MOCK_THEN_REAL for completeness"""
        print(f"🎭 [MOCK] {self.tool_id}: {str(parameters)}...")
        
        if param_hash not in self._mock_data:
            raise ValueError(
                f"No mock data {self.tool_id}:'{param_hash}'. "
                "Use environment variable INTEGRATION_TEST_MODE=real to run the test in REAL mode first to generate mock data."
            )
        
        record = self._mock_data[param_hash]
        
        # Reconstruct error or return value. Always re-record in MOCK_THEN_REAL to produce full session output sequence.
        start_time = asyncio.get_event_loop().time()
        try:
            if isinstance(record.output, dict) and "error" in record.output:
                # Record playback of error (0ms-ish) only when in MOCK_THEN_REAL to keep pure MOCK sessions lean
                if self.mode == IntegrationTestMode.MOCK_THEN_REAL:
                    elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
                    params_with_sop = self._build_parameters_with_sop(parameters, sop_doc_body)
                    self._record(params_with_sop, record.output, elapsed)
                error_type = record.output.get("error_type", "Exception")
                error_message = record.output["error"]
                if error_type == "ValueError":
                    raise ValueError(error_message)
                elif error_type == "RuntimeError":
                    raise RuntimeError(error_message)
                else:
                    raise Exception(f"{error_type}: {error_message}")
            # Success path
            if self.mode == IntegrationTestMode.MOCK_THEN_REAL:
                elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
                params_with_sop = self._build_parameters_with_sop(parameters, sop_doc_body)
                self._record(params_with_sop, record.output, elapsed)
            # If validators provided (new explicit retry path), manually apply them to mock output
            validators = kwargs.get("validators") or []
            if validators:
                response = dict(record.output)  # shallow copy
                for v in validators:
                    try:
                        res = v(response)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as ve:
                        # In mock mode we won't retry; just propagate to mimic live behavior
                        raise ve
                print(f"✅ [MOCK] {self.tool_id}: Applied validators to recorded response")
                return response
            print(f"✅ [MOCK] {self.tool_id}: Returned recorded response")
            return record.output
        finally:
            # For pure MOCK we do not append playback records to avoid duplicating data when saving again from real runs.
            pass
    
    def get_recorded_calls(self) -> List[ToolCallRecord]:
        """Get all recorded calls from this proxy"""
        return self._recorded_calls.copy()

    # --- Delegation helpers -------------------------------------------------
    def get_result_validation_hint(self) -> str:  # noqa: D401 - simple delegation
        """Delegate to underlying tool's result validation hint.

        Some engine logic (e.g. task output parsing) expects every tool object
        to implement get_result_validation_hint(). The proxy previously lacked
        this attribute causing AttributeError during integration tests when the
        engine accessed self.tools[tool_id].get_result_validation_hint().
        """
        # Gracefully handle tools that might not implement the method
        if hasattr(self.tool, "get_result_validation_hint"):
            return self.tool.get_result_validation_hint()  # type: ignore
        return "(no validation hint provided)"

    def __getattr__(self, name: str):  # Fallback delegation for future needs
        # Avoid recursion for special attributes
        if name in {"tool", "mode", "data_manager", "tool_id"}:
            raise AttributeError(name)
        return getattr(self.tool, name)


class IntegrationTestBase:
    """Base class for integration tests with save/mock capabilities"""
    
    def __init__(self, test_name: str, mode: IntegrationTestMode = None, load_data: bool = True):
        self.test_name = test_name
        self.mode = mode or IntegrationTestMode.REAL  # Default to REAL mode
        self.data_manager = TestDataManager()
        self.proxies: List[IntegrationTestProxy] = []
        self.test_session: Optional[TestSession] = None
        
        # Load existing data if in mock mode and load_data is True
        if self.mode in (IntegrationTestMode.MOCK, IntegrationTestMode.MOCK_THEN_REAL) and load_data:
            try:
                self.test_session = self.data_manager.load_test_session(test_name)
            except FileNotFoundError:
                # If no data file exists, continue without loading
                print(f"⚠️  No test data found for '{test_name}' - continuing without mock data")
                self.test_session = None
    
    def wrap_tool(self, tool: BaseTool) -> IntegrationTestProxy:
        """Wrap a tool with the integration test proxy"""
        proxy = IntegrationTestProxy(tool, self.mode, self.data_manager)
        
        # If in mock mode, load the mock data
        if self.mode in (IntegrationTestMode.MOCK, IntegrationTestMode.MOCK_THEN_REAL) and self.test_session:
            proxy.load_mock_data(self.test_session)
        
        self.proxies.append(proxy)
        return proxy
    
    def save_test_data(self) -> None:
        """Save all recorded tool calls to file"""
        if self.mode not in (IntegrationTestMode.REAL, IntegrationTestMode.MOCK_THEN_REAL):
            print("⚠️  Not saving data - mode does not allow writing (MOCK only)")
            return
        
        # Collect all recorded calls from all proxies
        all_calls = []
        for proxy in self.proxies:
            all_calls.extend(proxy.get_recorded_calls())
        
        if not all_calls:
            print("⚠️  No tool calls to save")
            return
        
        # Create test session
        session = TestSession(
            test_name=self.test_name,
            mode=self.mode,
            timestamp=datetime.now().isoformat(),
            tool_calls=all_calls,
            metadata={
                "total_tool_calls": len(all_calls),
                "tools_used": list(set(call.tool_id for call in all_calls))
            }
        )
        
        # Save to file
        self.data_manager.save_test_session(session)
        
        # Print summary
        tool_counts = {}
        for call in all_calls:
            tool_counts[call.tool_id] = tool_counts.get(call.tool_id, 0) + 1
        
        print(f"📊 Test Summary:")
        print(f"   Total calls: {len(all_calls)}")
        for tool_id, count in tool_counts.items():
            print(f"   {tool_id}: {count} calls")


# Utility functions for common test patterns
def get_test_mode() -> IntegrationTestMode:
    """Get test mode from environment variable"""
    mode_str = os.getenv("INTEGRATION_TEST_MODE", "mock").lower()
    if mode_str == "mock":
        return IntegrationTestMode.MOCK
    if mode_str in ("mock_then_real", "mock-then-real", "mockthenreal"):
        return IntegrationTestMode.MOCK_THEN_REAL
    return IntegrationTestMode.REAL


def print_test_mode_info(mode: IntegrationTestMode) -> None:
    """Print information about current test mode"""
    if mode == IntegrationTestMode.REAL:
        print("🔴 Running in REAL mode - tool calls will be executed and recorded")
    elif mode == IntegrationTestMode.MOCK:
        print("🎭 Running in MOCK mode - using recorded tool call responses")
    elif mode == IntegrationTestMode.MOCK_THEN_REAL:
        print("🌀 Running in MOCK_THEN_REAL mode - using recorded responses when available, otherwise executing real calls and recording them")
