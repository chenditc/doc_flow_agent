---
description: 生成小红书的小红书贴执行计划
tool:
  tool_id: TEMPLATE
input_description:
  human_setup: 小红书的账号人设
  post_target_audience: 小红书贴的对象
  num_posts: 需要撰写的帖子数量，如果未明确说明，则填2.
input_json_path:
  human_setup: $.blog_human_setup
  post_target_audience: $.blog_post_target_audience
output_description: 小红书贴的生成方案
result_validation_rule: 只要能提供符合该人设的小红书笔记并成功发送给用户即可。
---
## Execution Plan

<new task to execute>
1. 根据文档 bash.md 调用 bash 获取当前的时间。
2. 根据文档 llm.md，参考当前的时间，思考{num_posts}个面向的对象{post_target_audience}在该时间点有可能会机器他们情感共鸣的话题。每个话题要明确共鸣的情感是什么，例如焦虑、兴奋、好奇。
3. 根据文档 generate_post_task_list.md，把每一个话题写成一个帖子，每个帖子要配一张图片。人设：{human_setup}。面向对象：{post_target_audience}。
4. 根据文档 web_result_delivery.md，把生成出来的{num_posts}个帖子和所有相关图片发送给用户。
</new task to execute>