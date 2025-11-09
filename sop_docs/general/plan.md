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
requires_planning_metadata: true
input_description:
  task_description: Complex task that needs to be broken down into multiple steps
  related_context: All related context that might be helpful to clarify the task or be used during task execution. Need to include additional explanation on how it's related.
input_json_path:
  task_description: "$.['current_task']"
output_description: A breakdown of the task into multiple clear, actionable substeps
---
## parameters.prompt

### Objective
You are given a complex task that needs to be broken down into multiple manageable sub task. Please analyze the task and create a plan. Use the language as the original task

For each sub task, explicitly mark it using the format:
<new_task_to_execute>
...
</new_task_to_execute>

### Guidelines for Task Breakdown:
1. **Each sub task should be atomic**: One clear goal to achieve.
2. **Include all necessary context**: Each step should contain enough information to be understood independently, if you don't have these information right now, use a vague description. Eg. If you don't know the content format in a paper, do not say "extract line xx-xx", say "extract the introduction part of the paper".
3. **Maintain logical order**: Steps should flow logically
4. **An agent will be execute these tasks on behalf of the user**: Make sure the task description has enough information for agent.
5. **Use declarative task description**: Just declare what needs to be achieved as sub goal, do not use "If xxx, then xxx". Specify what needs to achieve, not "how" to achieve.
6. **Limit sub task count**: Do not plan too much detail tasks, plan 2-6 sub tasks. 
7. **Each sub task must be necessary**: Give out reason first, then your plan. Only plan necessary task, less tasks is better.
8. **Avoid user interaction**: Avoid user interaction when possible, only involve user feedback if you can't proceed without it.

### Task Info:

<COMPLEX_TASK_TO_BREAK_DOWN>
{task_description}
</COMPLEX_TASK_TO_BREAK_DOWN>

<CONTEXT_INFORMATION_RELATED_TO_THIS_TASK>
{related_context}
</CONTEXT_INFORMATION_RELATED_TO_THIS_TASK>

### Tool References For Planning
Use the following tool SOPs when deciding which capability should execute each sub task. Always reference the exact `doc_id` when describing a follow-up action.

<AVAILABLE_TOOLS_FOR_PLANNING>
{available_tool_docs_xml}
</AVAILABLE_TOOLS_FOR_PLANNING>

### Additional Tool Suggestions From Similarity Search
Consider these when the direct tool list does not contain an obvious match.

<VECTOR_RECOMMENDED_TOOLS>
{vector_tool_suggestions_xml}
</VECTOR_RECOMMENDED_TOOLS>

Please break down this task into clear, actionable substeps. Think through the logical sequence and create comprehensive steps that will lead to successful completion of the overall task.
