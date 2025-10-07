---
description: General Large Language Model Text Generation
tool:
  tool_id: LLM
  parameters:
    prompt: "{prompt_for_llm}"
input_description:
  prompt_for_llm: The prompt sending to LLM to complete the task, the prompt should be clear, concise, including all necessary information for LLM to generate output. Usally in markdown form, contains sections like "## Objective", "## Guidance" and etc.
output_description: The output of large language model
result_validation_rule: As long as the result is not a rejection, consider the result as valid. Rejection result might looks like "Sorry, I can't complete your request", or empty output.
---
