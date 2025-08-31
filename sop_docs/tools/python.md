---
doc_id: tools/python
description: Generate and execute python code
tool:
  tool_id: PYTHON_EXECUTOR
input_json_path:
  task_description: $.current_task
input_description:
  related_context_content: All related information which might be needed for python code. 
output_description: "The tool returns an object containing the generated Python code, its return value, any standard output or error messages, and exception details if errors occurred during execution. Example: {\"generated_code\": \"print('Hello World')\", \"return_value\": \"None\", \"stdout\": \"Hello World\\n\", \"stderr\": \"\", \"exception\": null}"
---



