---
doc_id: tools/bash
description: Execute any bash command or script in a sandbox environment. If user not mention which environment specifically, assume user meant for this environment.
tool:
  tool_id: CLI
  parameters:
    command: "{command}"
    id: "{shell_id}"
    exec_dir: "{exec_dir}"
    async_mode: "{async_mode}"
    timeout: "{timeout}"
input_description:
  command: The bash command or script to be executed in the sandbox environment. If not explicitly specified by user, use empty string ''.
  shell_id: The unique identifier of the shell environment to execute the command in. If not explicitly specified by user, use empty string ''.
  exec_dir: The directory path within the shell environment where the command should be executed. If not explicitly specified by user, use '/'.
  async_mode: Whether to execute the command asynchronously. Accepts 'true' or 'false'. If not explicitly specified by user, use 'false'.
  timeout: The maximum time in seconds to wait for the command to complete. If not explicitly specified by user, use 1200 seconds.
input_json_path:
  task_description: $.current_task
output_description: a object with stdout and stderr which store the output of stdout and stderr during execution.
skip_new_task_generation: true
---



