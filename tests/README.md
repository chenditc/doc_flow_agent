# README

Contains unit tests for doc flow agent components.

## Running Tests

## Embedding cache (SOP vector search)

Some unit tests (SOP vector search) rely on the on-disk embedding cache in `.cache/embeddings/<model>.json`.

- The default model for tests is `text-embedding-ada-002` (set in `tests/conftest.py`).
- Cache misses call the real embeddings endpoint and append to the JSON via `utils/embedding_utils.py`.

### Regenerating the cache

If `.cache/embeddings/text-embedding-ada-002.json` is missing/outdated, regenerate it by running pytest with a higher timeout and `OPENAI_API_KEY` set:

```bash
export OPENAI_API_KEY=...
# optional: export OPENAI_API_BASE=...
python -m pytest --timeout=0
```

This will recreate/update `.cache/embeddings/text-embedding-ada-002.json` automatically during the run.

### Run all tests:
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

### Run all tests in mock mode (fast):
```bash
source .venv/bin/activate && INTEGRATION_TEST_MODE=MOCK python -m pytest tests/ -v
```

### Run specific test file:
```bash
source .venv/bin/activate
python -m pytest tests/test_sop_document.py -v
```

### Run specific test class:
```bash
source .venv/bin/activate
python -m pytest tests/test_sop_document.py::TestSOPDocumentLoader -v
```

### Run integration tests only:
```bash
# Fast mock mode (default)
source .venv/bin/activate && INTEGRATION_TEST_MODE=MOCK python -m pytest tests/test_integration_minimal.py -v

# Real mode (slower, records new data)
source .venv/bin/activate && INTEGRATION_TEST_MODE=REAL python -m pytest tests/test_integration_minimal.py -v
```

### Using unittest directly:
```bash
source .venv/bin/activate
python tests/test_sop_document.py
```

## Writing Tests for New Modules

### 1. Create test file
Create `test_your_module.py` in the tests directory:

```python
#!/usr/bin/env python3
import unittest
import sys
import os
from unittest.mock import patch, AsyncMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from your_module import YourClass

class TestYourClass(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.instance = YourClass()
    
    def test_your_method(self):
        """Test basic functionality"""
        result = self.instance.your_method()
        self.assertEqual(result, expected_value)

if __name__ == '__main__':
    unittest.main()
```

### 2. Mocking external dependencies

For LLM calls:
```python
def test_with_llm_mock(self):
    mock_llm = AsyncMock()
    mock_llm.execute.return_value = "mocked response"
    
    with patch('tools.llm_tool.LLMTool', return_value=mock_llm):
        result = asyncio.run(self.instance.async_method())
        self.assertEqual(result, expected_value)
```

For file operations:
```python
def test_with_file_mock(self):
    with patch('builtins.open', mock_open(read_data="test data")):
        result = self.instance.read_file("test.txt")
        self.assertEqual(result, "test data")
```

### 3. Testing async functions
```python
import asyncio

def test_async_method(self):
    async def run_test():
        result = await self.instance.async_method()
        return result
    
    result = asyncio.run(run_test())
    self.assertEqual(result, expected_value)
```

## Test Improvement Plan

### Components Requiring Integration/End-to-End Testing

#### Complex Orchestration Components - Use integration tests instead of unittest
- **`doc_execute_engine.py` (DocExecuteEngine class)** - Complex async workflow management, heavy external dependencies, state management across operations
- **`tracing.py` (ExecutionTracer class)** - File I/O operations, complex state management, integration requirements
- **`tracing_wrappers.py`** - Decorator/wrapper patterns requiring real tool instances and tracing system integration

#### Testing Strategy for Integration Components
- Use temporary directories and controlled test environments
- Mock external dependencies (LLM responses, file system, user input)
- Use `pytest-asyncio` for async integration tests
- Test complete workflows with known SOP documents
- Focus on end-to-end behavior rather than isolated unit behavior

### Current Status
- ✅ `sop_document.py` - Already has comprehensive unittest coverage
- ✅ `utils.py` - Complete unittest coverage for JSON path manipulation functions
- ✅ `tests/test_tools/` - Complete unittest coverage for all tools (65 test cases)
- ✅ **Integration Test Framework** - Save/mock framework for complex workflow testing
- 🔲 ~35% of remaining components suitable for unittest approach
- 🔲 ~30% of components better suited for integration testing approach

## Integration Testing with Save/Mock Framework

For complex components like `DocExecuteEngine`, `ExecutionTracer`, and workflow orchestration, we now have a sophisticated integration test framework with recording and playback capabilities.

### Quick Start
```bash
# Record actual tool interactions
source .venv/bin/activate && INTEGRATION_TEST_MODE=REAL python -m pytest tests

# Run fast tests with recorded data
source .venv/bin/activate && INTEGRATION_TEST_MODE=MOCK python -m pytest tests

# Run specific integration test
source .venv/bin/activate && INTEGRATION_TEST_MODE=MOCK python -m pytest tests/test_integration_minimal.py -v

# View recorded test data
ls -la tests/integration_data/
```

### Environment Variables
- `INTEGRATION_TEST_MODE=REAL` - Record actual tool interactions (slower, requires API keys)
- `INTEGRATION_TEST_MODE=MOCK` - Use recorded data for fast testing (default if not set)
- `INTEGRATION_TEST_MODE=MOCK_THEN_REAL` - Hybrid: replay when cached; on cache miss, run real call and add it so subsequent identical calls in same test become deterministic. Use this to organically grow/update recorded datasets.

### Key Features
- **📹 Automatic Recording**: Tool calls recorded during real execution
- **🎭 Mock Playbook**: Exact reproduction using recorded data
- **🔧 Minimal Code Changes**: Same tool interface for both modes
- **📊 Test Data Management**: Easy saving/loading of interaction data

See [INTEGRATION_TEST_FRAMEWORK.md](INTEGRATION_TEST_FRAMEWORK.md) for complete documentation.

### Legacy Script (Deprecated)
> **Note**: The `run_integration_tests.sh` script is deprecated. Please use the direct command line approach above for better maintainability.