---
description: General Large Language Model Text Generation
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  current_task: The task we are trying to accomplish, not include the information LLM don't understand (eg. Follow doc xxx)
output_description: The output of large language model
---
## parameters.prompt

Please complete the following task, reply using same language as following task:

{current_task}