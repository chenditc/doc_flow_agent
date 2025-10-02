---
description: Use to collect user input through dynamically generated web forms. The LLM will analyze the instruction and create appropriate form fields (text, radio buttons, checkboxes, etc.) automatically.
tool:
  tool_id: WEB_USER_COMMUNICATE
  parameters:
    instruction: "{instruction}"
    timeout_seconds: 1800
    poll_interval: 2.0
input_description:
  instruction: Natural language description of what input you need from the user. Be specific about the type of information needed.
output_description: JSON object containing the user's response, form URL, and status information.
---