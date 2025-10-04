---
description: 生成小红书的干货贴执行计划
tool:
  tool_id: TEMPLATE
input_description:
  human_setup: 小红书的账号人设
  post_target_audience: 干货贴的对象
output_description: 干货贴的生成方案
result_validation_rule: 只要能提供若干篇符合该人设的小红书笔记即可，用户会自行选择合适的进行发送。
---
## Execution Plan

<new task to execute>
1. 根据文档 bash.md 调用 bash 获取当前的时间。
2. 根据文档 llm.md，参考当前的时间，思考10个面向的对象{post_target_audience}在该时间点有可能会机器他们情感共鸣的话题。每个话题要明确共鸣的情感是什么，例如焦虑、兴奋、好奇。
3. 根据文档 generate_post_task_list.md，把每一个话题写成一个帖子。人设：{human_setup}。面向对象：{post_target_audience}。
4. 根据文档 web_user_communicate.md，把生成出来的10个帖子和首图图片发送给用户。
</new task to execute>