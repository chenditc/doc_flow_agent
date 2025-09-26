---
doc_id: general/plan
description: Break down complex tasks into multiple manageable substeps
aliases:
  - task planning
  - task breakdown
  - multi-step task
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  task_description: Complex task that needs to be broken down into multiple steps
  related_context: All related context that might be helpful to clarify the task or be used during task execution. Need to include additional explanation on how it's related.
input_json_path:
  task_description: "$.['current_task']"
output_description: A breakdown of the task into multiple clear, actionable substeps
---
## parameters.prompt

### Objective
You are given a complex task that needs to be broken down into multiple manageable substeps. Please analyze the task and create a step-by-step plan where each step is clear, specific, and can be executed independently. Use the language as the original task

For each substep, explicitly mark it using the format:
<new_task_to_execute>
...
</new_task_to_execute>

### Guidelines for Task Breakdown:
1. **Each substep should be atomic**: One clear action per step
2. **Include all necessary context**: Each step should contain enough information to be understood independently
3. **Maintain logical order**: Steps should flow logically
4. **Complete information**: Each step must have complete information and no ambiguity. If there is missing information, do not generate full plan, just generate a task to ask user for more information. The task should provide detailed message.
5. **An agent will be execute these tasks on behalf of the user**: Make sure the task description has enough information for agent.

### Task Analysis:

<COMPLEX_TASK_TO_BREAK_DOWN>
{task_description}
</COMPLEX_TASK_TO_BREAK_DOWN>

<CONTEXT_INFORMATION_RELATED_TO_THIS_TASK>
{related_context}
</CONTEXT_INFORMATION_RELATED_TO_THIS_TASK>

Please break down this task into clear, actionable substeps. Think through the logical sequence and create comprehensive steps that will lead to successful completion of the overall task.