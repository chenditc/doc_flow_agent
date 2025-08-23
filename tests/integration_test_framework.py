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
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute tool with recording/playback logic"""
        param_hash = self.data_manager._hash_parameters(self.tool_id, parameters)
        
        if self.mode == IntegrationTestMode.REAL:
            return await self._execute_real(parameters, param_hash)
        else:  # MOCK mode
            return await self._execute_mock(parameters, param_hash)
    
    async def _execute_real(self, parameters: Dict[str, Any], param_hash: str) -> Any:
        """Execute tool in real mode and record the result"""
        print(f"🔴 [REAL] {self.tool_id}: {str(parameters)[:100]}...")
        
        start_time = asyncio.get_event_loop().time()
        try:
            result = await self.tool.execute(parameters)
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Record the call
            record = self.data_manager.create_tool_call_record(
                tool_id=self.tool_id,
                parameters=parameters,
                output=result,
                execution_time_ms=execution_time
            )
            self._recorded_calls.append(record)
            
            print(f"✅ [REAL] {self.tool_id}: Recorded response ({execution_time:.1f}ms)")
            return result
            
        except Exception as e:
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Record the error
            record = self.data_manager.create_tool_call_record(
                tool_id=self.tool_id,
                parameters=parameters,
                output={"error": str(e), "error_type": type(e).__name__},
                execution_time_ms=execution_time
            )
            self._recorded_calls.append(record)
            
            print(f"❌ [REAL] {self.tool_id}: Recorded error ({execution_time:.1f}ms)")
            raise
    
    async def _execute_mock(self, parameters: Dict[str, Any], param_hash: str) -> Any:
        """Execute tool in mock mode using recorded data"""
        print(f"🎭 [MOCK] {self.tool_id}: {str(parameters)[:100]}...")
        
        if param_hash not in self._mock_data:
            raise ValueError(
                f"No mock data found for {self.tool_id} with parameters hash '{param_hash}'. "
                "Use environment variable INTEGRATION_TEST_MODE=real to run the test in REAL mode first to generate mock data."
            )
        
        record = self._mock_data[param_hash]
        
        # Check if recorded call had an error
        if isinstance(record.output, dict) and "error" in record.output:
            error_type = record.output.get("error_type", "Exception")
            error_message = record.output["error"]
            
            # Recreate the original exception type if possible
            if error_type == "ValueError":
                raise ValueError(error_message)
            elif error_type == "RuntimeError":
                raise RuntimeError(error_message)
            else:
                raise Exception(f"{error_type}: {error_message}")
        
        print(f"✅ [MOCK] {self.tool_id}: Returned recorded response")
        return record.output
    
    def get_recorded_calls(self) -> List[ToolCallRecord]:
        """Get all recorded calls from this proxy"""
        return self._recorded_calls.copy()


class IntegrationTestBase:
    """Base class for integration tests with save/mock capabilities"""
    
    def __init__(self, test_name: str, mode: IntegrationTestMode = None, load_data: bool = True):
        self.test_name = test_name
        self.mode = mode or IntegrationTestMode.REAL  # Default to REAL mode
        self.data_manager = TestDataManager()
        self.proxies: List[IntegrationTestProxy] = []
        self.test_session: Optional[TestSession] = None
        
        # Load existing data if in mock mode and load_data is True
        if self.mode == IntegrationTestMode.MOCK and load_data:
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
        if self.mode == IntegrationTestMode.MOCK and self.test_session:
            proxy.load_mock_data(self.test_session)
        
        self.proxies.append(proxy)
        return proxy
    
    def save_test_data(self) -> None:
        """Save all recorded tool calls to file"""
        if self.mode != IntegrationTestMode.REAL:
            print("⚠️  Not saving data - not in REAL mode")
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
    return IntegrationTestMode.REAL


def print_test_mode_info(mode: IntegrationTestMode) -> None:
    """Print information about current test mode"""
    if mode == IntegrationTestMode.REAL:
        print("🔴 Running in REAL mode - tool calls will be executed and recorded")
    else:
        print("🎭 Running in MOCK mode - using recorded tool call responses")
