---
description: Execute any bash command or script in a sandbox environment. Ideal for file operations, system commands, running scripts, and installing packages in this environment. If user not mention which environment specifically, assume user meant for this environment.
tool:
  tool_id: CLI
input_json_path:
  task_description: $.current_task
output_description: a object with stdout and stderr which store the output of stdout and stderr during execution.
skip_new_task_generation: true
---

