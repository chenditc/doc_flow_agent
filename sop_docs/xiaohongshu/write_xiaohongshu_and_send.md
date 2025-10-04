---
description: 生成小红书的帖子的执行计划
tool:
  tool_id: TEMPLATE
input_description:
  human_setup: 小红书的账号人设
  post_target_audience: 贴子的对象
  topic: 小红书帖子的主题
  emotion_target: 情感共鸣点
input_json_path:
  current_task: $.current_task
output_description: 贴子的生成方案
result_validation_rule: 只要能提供1篇符合该人设的小红书笔记即可。
---
## Execution Plan

<new task to execute>
1. 根据文档 write_xiaohongshu_single_post.md, 为 {human_setup} 的博主，写一篇给 {post_target_audience} 看的，关于{topic}的干货帖子，击中情感共鸣点：{emotion_target}。
2. 根据文档 web_result_delivery.md，把前面写好的帖子和图片发给用户。
</new task to execute>