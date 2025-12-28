---
description: Generate and execute python code. It has access to data stored in context dictionary, usually reference by json path.
tool:
  tool_id: PYTHON_EXECUTOR
input_json_path:
  task_description: $.current_task
input_description:
  related_context_content: A dict contains all related information which might be needed for python code.
skip_new_task_generation: true
output_description: "The tool returns an object containing the generated Python code, its return value, any standard output or error messages, and exception details if errors occurred during execution. Example: {\"python_code\": \"print('Hello World')\", \"return_value\": \"None\", \"stdout\": \"Hello World\\n\", \"stderr\": \"\", \"exception\": null}"
---



