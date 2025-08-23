---
description: 生成小红书的干货贴执行计划
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  human_setup: 小红书的账号人设
  post_target_audience: 干货贴的对象
output_description: 干货贴的生成方案
---
## parameters.prompt

请根据下面的小红书账号人设对下面的样本流程进行微调，生成一个小红书的干货贴生成流程，便于后续给 Agent 执行。

账号人设：{human_setup}

干货贴的对象：{post_target_audience}

样本流程：
1. 根据文档 bash.md， 执行 date 命令获取当前的时间。
2. 使用 llm.md，参考当前的时间，生成10个适合用来做干货贴的主题。
3. 使用 llm.md，给前面生成出来的10个干货贴主题，分别生成标题和正文，每个干货贴主题应当是一个独立的生成任务。