# Tools Directory

This directory contains all the tools used by the Doc Flow Agent. Each tool is implemented as a separate Python file that inherits from the `BaseTool` class.

## Architecture

### Base Tool Class
All tools inherit from `BaseTool` which provides:
- Common interface with `execute()` method
- Parameter validation with `validate_parameters()`
- Consistent error handling
- Tool identification with `tool_id`

### Built-in Tools

#### LLMTool (`llm_tool.py`)
- **Tool ID**: `LLM`
- **Purpose**: Large Language Model interactions (currently mocked)
- **Required Parameters**: `prompt`
- **Returns**: JSON with structured response

#### CLITool (`cli_tool.py`) 
- **Tool ID**: `CLI`
- **Purpose**: Execute command line interface commands
- **Required Parameters**: `command`
- **Returns**: Command output as string

#### UserCommunicateTool (`user_communicate_tool.py`)
- **Tool ID**: `USER_COMMUNICATE`
- **Purpose**: Interactive communication with users for input/feedback
- **Required Parameters**: `message` (message to send to user)
- **Returns**: JSON with user's reply
- **Usage**: Supports multiline input; users can end input with Ctrl+D/Ctrl+Z or by typing `###END###`

#### WordCountTool (`word_count_tool.py`)
- **Tool ID**: `WORD_COUNT`
- **Purpose**: Count words, characters, lines in text
- **Required Parameters**: `text`
- **Returns**: JSON with text statistics

## Creating a New Tool

### 1. Create the Tool File

Create a new Python file in the `tools/` directory:

```python
#!/usr/bin/env python3
"""
Your Custom Tool for Doc Flow Agent
"""

from typing import Dict, Any
import json

from .base_tool import BaseTool


class YourCustomTool(BaseTool):
    """Description of what your tool does"""
    
    def __init__(self):
        super().__init__("YOUR_TOOL_ID")  # Unique identifier
    
    async def execute(self, parameters: Dict[str, Any]) -> str:
        """Execute your tool with given parameters
        
        Args:
            parameters: Dictionary containing required parameters
            
        Returns:
            JSON string with tool output
            
        Raises:
            ValueError: If required parameters are missing
        """
        # Validate required parameters
        self.validate_parameters(parameters, ['param1', 'param2'])
        
        # Get parameters
        param1 = parameters.get('param1')
        param2 = parameters.get('param2')
        
        # Your tool logic here
        result = do_something(param1, param2)
        
        # Return structured result
        return json.dumps({
            "data": {
                "result": result
            }
        }, ensure_ascii=False)
```

### 2. Register the Tool

Add your tool to `__init__.py`:

```python
from .your_custom_tool import YourCustomTool

__all__ = ['BaseTool', 'LLMTool', 'CLITool', 'WordCountTool', 'UserCommunicateTool', 'YourCustomTool']
```

### 3. Use the Tool

In your engine code:

```python
from tools import YourCustomTool

# Register the tool
engine = DocExecuteEngine()
custom_tool = YourCustomTool()
engine.register_tool(custom_tool)

# Use in a task
task = Task(
    task_id="custom-task",
    description="Use custom tool",
    sop_doc_id="custom/task",
    tool={
        "tool_id": "YOUR_TOOL_ID",
        "parameters": {
            "param1": "value1",
            "param2": "value2"
        }
    },
    input_json_path={},
    output_json_path={}
)
```

## Tool Guidelines

1. **Inherit from BaseTool**: Always extend the `BaseTool` class
2. **Unique Tool ID**: Choose a descriptive, unique `tool_id`
3. **Parameter Validation**: Use `validate_parameters()` for required params
4. **Async Methods**: All `execute()` methods should be async
5. **JSON Output**: Return structured JSON strings when possible
6. **Error Handling**: Raise appropriate exceptions with clear messages
7. **Documentation**: Include comprehensive docstrings

## Integration with SOP Documents

Tools are referenced in SOP documents like this:

```yaml
tool:
  tool_id: "YOUR_TOOL_ID"
  parameters:
    param1: "{input_variable}"
    param2: "static_value"
```

The engine will:
1. Load the tool instance by `tool_id`
2. Resolve input variables from context
3. Call `tool.execute(parameters)`
4. Parse the JSON result and update context

## Testing Your Tool

Use the `tool_system_demo.py` script as a template to test your new tool:

```bash
python tool_system_demo.py
```
