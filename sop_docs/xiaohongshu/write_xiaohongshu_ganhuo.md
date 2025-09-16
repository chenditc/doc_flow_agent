---
description: 生成小红书的干货贴执行计划
tool:
  tool_id: TEMPLATE
input_description:
  human_setup: 小红书的账号人设
  post_target_audience: 干货贴的对象
output_description: 干货贴的生成方案
---
## Execution Plan

1. 根据文档 bash.md 调用 bash 获取当前的时间。
2. 根据文档 generate_topic_idea.md，参考当前的时间，生成10个适合用来做干货贴的主题。人设：{human_setup}。面向对象：{post_target_audience}。
3. 根据文档 generate_post_task_list.md，把每一个主题写成一个具体的干货贴。人设：{human_setup}。面向对象：{post_target_audience}。
4. 根据文档 merge_xiaohongshu_result.md，把生成出来的10个干货帖子整理合并成一个完整的文档。

完成第4步后即可获得小红书干货贴。