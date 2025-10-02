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
  related_context: All related context that might be helpful to clarify the task or be used during task execution. Need to include additional explanation on how it's related.
input_json_path:
  task_description: "$.['current_task']"
output_description: The outcome of the current task and the remaining tasks
---
## parameters.prompt

### Objective
Here is a task user wants to achieve. Please first think if you can complete the task without additional information by using one of the tool we listed below. 

Explicitly mark the new task to do using format, eg.：
<new_task_to_execute>
...
</new_task_to_execute>

#### Case 1
If you can complete the task in one go without additional information by using one of the tools. The tool already have all the input it needs. Generate one <new_task_to_execute> object.

#### Case 2
If you need additional information or the task is too big to complete in one go, please break down the task into multiple sub tasks, each sub task should be clear and include all required information. Generate multiple <new_task_to_execute> object.

#### Case 3
If there are certain tool that can be used to complete the task but it's not listed in the tools section, you can use 'user_communicate' tool to send the detailed instruction for using that tool and consider this task as completed. Generate one <new_task_to_execute> object starting with 'Follow web_user_communicate.md to xxxx'

#### Tools
 - cli tool: 
    - Functionality: You have access to my linux node and you can execute any bash command or script in a bash terminal, the tool will send back the stdout and stderr result.
    - Task description example: "<new_task_to_execute>Follow bash.md, run xxxxx</new_task_to_execute>".
 - llm tool: 
    - Functionality: You can prompt a large language model to generate text, you can make it draft content, generate plan, write code, analyze information and etc. The tool will send back text result. 
    - Task description example: "<new_task_to_execute>Follow llm.md, analyze the case study in ...</new_task_to_execute>".
 - python tool: 
    - Functionality: You can let this tool write python code and execute it. 
    - Task description example: "<new_task_to_execute>Follow python.md, call api xxx and convert numberical data into vectors.</new_task_to_execute>".
 - user_communicate tool: 
    - Functionality: You can give text to user and let user to do actual work, eg, operate machine / browser / software. The tool will collect user's feedback and let you know if the instruction has been completed. Use this tool only if previous tool doesn't satify your need
    - Task description example: "<new_task_to_execute>Follow web_user_communicate.md, ask user to plugin network cabel</new_task_to_execute>".

<USER_TASK_WANT_TO_COMPLETE>
{task_description}
</USER_TASK_WANT_TO_COMPLETE>

<CONTEXT_INFORMATION_RELATED_TO_THIS_TASK>
{related_context}
</CONTEXT_INFORMATION_RELATED_TO_THIS_TASK>