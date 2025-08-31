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

请根据下面的小红书账号人设以及样本流程，生成一个具体的，给 Agent 执行的任务列表。

账号人设：{human_setup}

干货贴的对象：{post_target_audience}

样本流程：
1. 根据文档 bash.md， 执行 date 命令获取当前的时间。
2. 根据文档 generate_topic_idea.md，参考当前的时间，生成10个适合用来做干货贴的主题。
3. 根据文档 generate_post_task_list.md，把每一个主题生成一个具体的撰写干货贴的任务并要求完成。
4. 根据文档 merge_xiaohongshu_result.md，把生成出来的10个干货帖子整理合并成一个完整的文档。