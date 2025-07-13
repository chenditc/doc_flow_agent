# Integration Test Framework with Save/Mock Features

This framework provides recording and playback capabilities for integration tests, allowing you to test complex workflows with external dependencies while maintaining fast, deterministic test execution.

## Key Features

- **📹 Automatic Recording**: Tool calls are automatically recorded during real mode execution
- **🎭 Mock Playback**: Recorded data is replayed exactly during mock mode
- **❌ Clear Error Messages**: Helpful guidance when mock data is missing
- **📊 Test Data Management**: Easy saving/loading of test interaction data

## Quick Start

### 1. Run Tests in Real Mode (Record Data)

```bash
# Record tool interactions
source .venv/bin/activate && INTEGRATION_TEST_MODE=REAL python -m pytest tests/test_integration_minimal.py -v

# Or export environment variable first
source .venv/bin/activate
export INTEGRATION_TEST_MODE=REAL
python -m pytest tests/test_integration_minimal.py -v
```

This will:
- Execute actual tool calls (LLM, CLI, etc.)
- Record all inputs/outputs automatically
- Save data to `tests/integration_data/`

### 2. Run Tests in Mock Mode (Use Recorded Data)

```bash
# Use recorded data for fast testing
source .venv/bin/activate && INTEGRATION_TEST_MODE=MOCK python -m pytest tests/test_integration_minimal.py -v

# Or export environment variable first
source .venv/bin/activate
export INTEGRATION_TEST_MODE=MOCK
python -m pytest tests/test_integration_minimal.py -v
```

This will:
- Load recorded tool call responses
- Skip actual LLM/CLI execution
- Run tests deterministically and fast

### 3. Manage Test Data

```bash
# View recorded data info
ls -la tests/integration_data/

# View specific test data
cat tests/integration_data/doc_execute_engine_test_basic_document_execution_data.json | jq .

# Clean all recorded data
rm -rf tests/integration_data/*.json
```

## Framework Components

### IntegrationTestBase

Base class for creating integration tests with save/mock capabilities.

```python
from integration_test_framework import IntegrationTestBase, TestMode, get_test_mode

class TestMyIntegration(unittest.TestCase):
    def setUp(self):
        self.test_mode = get_test_mode()
        self.integration_test = IntegrationTestBase(
            test_name="my_integration_test",
            mode=self.test_mode
        )
        
        # Wrap your tools
        self.llm_tool = self.integration_test.wrap_tool(LLMTool())
        self.cli_tool = self.integration_test.wrap_tool(CLITool())
    
    def tearDown(self):
        # Save data if in real mode
        if self.test_mode == TestMode.REAL:
            self.integration_test.save_test_data()
```

### IntegrationTestProxy

Transparent proxy that wraps tools for recording/playback.

```python
# Create proxy (usually done by IntegrationTestBase)
proxy = IntegrationTestProxy(original_tool, mode, data_manager)

# Use exactly like original tool
result = await proxy.execute({"prompt": "Hello world"})
```

### TestDataManager

Handles saving and loading of test data files.

```python
manager = TestDataManager("tests/integration_data")
manager.save_test_session(session)
session = manager.load_test_session("test_name")
```

## Writing Integration Tests

### Basic Pattern

```python
class TestMyFeature(unittest.TestCase):
    def setUp(self):
        # Get test mode from environment
        self.test_mode = get_test_mode()
        
        # Initialize framework
        self.integration_test = IntegrationTestBase(
            test_name="my_feature_test",
            mode=self.test_mode
        )
        
        # Wrap tools that your code uses
        self.llm_tool = self.integration_test.wrap_tool(LLMTool())
        
        # Create your system under test with wrapped tools
        self.my_system = MySystem(llm_tool=self.llm_tool)
    
    def tearDown(self):
        # Save recorded data
        if self.test_mode == TestMode.REAL:
            self.integration_test.save_test_data()
    
    async def test_my_workflow(self):
        # Your test logic here
        result = await self.my_system.do_something()
        
        # Assertions work the same in both modes
        self.assertIsNotNone(result)
```

### Testing Error Scenarios

The framework automatically records and replays errors:

```python
async def test_error_handling(self):
    # This will be recorded as an error in real mode
    # And replayed as the same error in mock mode
    with self.assertRaises(RuntimeError):
        await self.cli_tool.execute({"command": "invalid-command"})
```

### Testing with DocExecuteEngine

```python
def setUp(self):
    # ... framework setup ...
    
    # Create engine
    self.engine = DocExecuteEngine()
    
    # Replace engine's tools with wrapped versions
    self.engine.tools = {
        "LLM": self.integration_test.wrap_tool(LLMTool()),
        "CLI": self.integration_test.wrap_tool(CLITool()),
        "USER_COMMUNICATE": self.integration_test.wrap_tool(UserCommunicateTool())
    }

async def test_document_execution(self):
    result = await self.engine.execute_document(
        input_data={"task": "write hello world"},
        context={}
    )
    # Verify results...
```

## Test Data Format

Recorded data is stored as JSON files in `tests/integration_data/`:

```json
{
  "test_name": "my_test",
  "mode": "real",
  "timestamp": "2025-08-20T12:34:56",
  "tool_calls": [
    {
      "tool_id": "LLM",
      "parameters": {"prompt": "Hello"},
      "output": "Hi there!",
      "timestamp": "2025-08-20T12:34:56",
      "execution_time_ms": 1234.5,
      "parameters_hash": "abc123def456"
    }
  ],
  "metadata": {
    "total_tool_calls": 1,
    "tools_used": ["LLM"]
  }
}
```

## Best Practices

### 1. Workflow for New Tests

1. **Write test** - Create integration test using the framework
2. **Run in real mode** - Execute with actual tools to record interactions
3. **Verify results** - Ensure test passes and behavior is correct
4. **Commit recorded data** - Check in the `*_data.json` files
5. **Run in mock mode** - Verify test works with recorded data
6. **CI/CD setup** - Configure CI to run in mock mode for speed

### 2. Test Organization

```
tests/
├── integration_test_framework.py     # Framework code
├── integration_data/                 # Recorded test data
│   ├── doc_engine_basic_data.json
│   └── llm_tool_complex_data.json
├── test_integration_minimal.py       # Example tests
└── test_my_feature_integration.py    # Your integration tests
```

### 3. Managing Test Data

- **Keep recorded data in version control** for reproducible tests
- **Re-record data** when tool behavior changes significantly
- **Use descriptive test names** to make data files identifiable
- **Clean old data** when tests are removed or renamed

### 4. Error Handling

When mock data is missing, you'll get helpful errors:

```
ValueError: No mock data found for LLM tool call.
Parameters: {
  "prompt": "Generate code for..."
}
Parameter hash: abc123def456
Available parameter hashes: ['def789ghi012', 'jkl345mno678']
Run the test in REAL mode first to generate mock data.
```

## Environment Variables

- `INTEGRATION_TEST_MODE=real|mock` - Override test mode
- Default mode is `real` if not specified

## Troubleshooting

### Mock Data Not Found

If you get "No mock data found" errors:
1. Run the test in REAL mode first: `source .venv/bin/activate && INTEGRATION_TEST_MODE=REAL python -m pytest tests/test_integration_minimal.py::TestDocExecuteEngineIntegration::test_basic_document_execution -v`
2. Check that recorded data file exists in `tests/integration_data/`
3. Verify test name matches between test and data file

### Tests Are Slow

If tests are running slowly:
1. Make sure you're in MOCK mode: `source .venv/bin/activate && INTEGRATION_TEST_MODE=MOCK python -m pytest tests/test_integration_minimal.py::TestDocExecuteEngineIntegration::test_basic_document_execution -v`
2. Check that `INTEGRATION_TEST_MODE=mock` is set
3. Verify mock data files are being loaded (should see loading messages)

### Inconsistent Results

If test results vary between runs:
1. In REAL mode, this is expected (external dependencies)
2. In MOCK mode, results should be identical
3. Re-record data if tool behavior has changed

## Integration with Existing Code

The framework integrates seamlessly with existing tracing infrastructure:

- Uses similar data structures as `tracing.py`
- Compatible with `tracing_wrappers.py` patterns
- Follows the `BaseTool` interface exactly
- Can be combined with existing test utilities

This design ensures minimal disruption to existing code while providing powerful testing capabilities.
