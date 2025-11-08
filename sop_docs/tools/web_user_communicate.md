---
description: Use to collect user input through dynamically generated web forms—ideal for getting user input, asking clarifying questions, or handling manual tasks that require human intervention. Use it very carefully and only request information when you are sure the user's input is required. The LLM will analyze the instruction and create appropriate form fields (text, radio buttons, checkboxes, etc.) automatically.
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
