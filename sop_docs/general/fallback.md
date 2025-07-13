---
doc_id: general/fallback
description: General task execution fallback
aliases:
  - general task execution
  - fallback task
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  task_description: Current task user wants to complete
  related_context: All related context that might be helpful to clarify the task or be used during task execution.
input_json_path:
  task_description: "$.['current_task']"
output_description: The outcome of the current task and the remaining tasks
---
## parameters.prompt

### Objective
Here is a task user wants to achieve. Please first think if you can complete the task without additional information by using one of the tool we listed below. 

Explicitly mark the new task to do using format, eg.：
<new_task_to_execute_1>
...
</new_task_to_execute_1>

<new_task_to_execute_2>
...
</new_task_to_execute_2>

#### Case 1
If you can complete the task in one go without additional information by using one of the tools. The tool already have all the input it needs. Generate one new_task_to_execute_1 object.

#### Case 2
If you need additional information or the task is too big to complete in one go, please break down the task into multiple sub tasks, each sub task should be clear and include all required information. Generate multiple new_task_to_execute_x object.

#### Case 3
If there are certain tool that can be used to complete the task but it's not listed in the tools section, you can use 'user_communicate' tool to send the detailed instruction for using that tool and consider this task as completed. Generate one new_task_to_execute_1 object starting with 'Follow user_communicate.md to xxxx'

#### Tools
 1. cli tool: 
    - Functionality: You have a ubuntu 24.04 sandbox and you can execute any command in a bash terminal, you just need to provide the bash command as input, the tool will send back the stdout and stderr result. 
    - Input for tool: A comprehensive bash command or script.
    - Trigger prefix: To use cli tool, add this to the task description: "Follow sop_docs/tools/bash.md,".
 2. llm tool: 
    - Functionality: You can prompt a large language model to generate text, you can make it draft content, generate plan, generate code and etc. The tool will send back text result. 
    - Input for tool: A detailed instruction prompt for llm.
    - Trigger prefix: To use llm tool, add this to the task description: "Follow sop_docs/tools/llm.md,".
 3. user_communicate tool: 
    - Functionality: You can give text to user and let user to do actual work, eg, operate machine / browser / software. The tool will collect user's feedback and let you know if the instruction has been completed. 
    - Input for tool: A prepared message to send to user.
    - Trigger prefix: To use user_communicate tool, add this to the task description: "Follow sop_docs/tools/user_communicate.md,". 

#### Sub task requirement
 - Each sub task description will be fan out to different domain expert to execute, domain expert doesn't know the context of the task, so make sure the task description contains all information.
 - You can rephrase the sub task to make it sounds natural and professional.

<USER_TASK>
{task_description}
</USER_TASK>

<TASK_CONTEXT>
{related_context}
</TASK_CONTEXT>