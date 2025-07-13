#!/usr/bin/env python3
"""
Test Tools Summary
==================

This directory contains comprehensive unit tests for all tools in the doc_flow_agent project.

Test Coverage Summary:
- test_base_tool.py: 13 test cases covering abstract base class functionality
- test_cli_tool.py: 12 test cases covering command execution with subprocess mocking
- test_json_path_generator.py: 23 test cases covering JSON path generation logic
- test_user_communicate_tool.py: 17 test cases covering user input/output formatting

Key Testing Features:
- Comprehensive parameter validation testing
- Async function testing with proper asyncio handling
- Mocking of external dependencies (subprocess, LLM calls, user input)
- Error handling and edge case coverage
- Unicode and special character support testing
- Integration with existing test suite

Running Tests:
```bash
# Run all tool tests
source .venv/bin/activate
python -m pytest tests/test_tools/ -v

# Run specific tool test
python -m pytest tests/test_tools/test_base_tool.py -v

# Run all tests (including tool tests)
python -m pytest tests/ -v
```

All tests follow the unittest framework and are compatible with pytest.
Each test file is self-contained and can be run independently.
"""
