---
description: 合并展示小红书生成结果
tool:
  tool_id: PYTHON_EXECUTOR
  parameters:
    task_description: "请把小红书生成的帖子排版成清晰、适合阅读的 markdown 格式，保留帖子的内容不变，不要进行删减。"
input_description:
  related_context_content: 在之前生成出来的小红书帖子，一个列表，每个元素是一个帖子的内容，包含首图设计、正文等。
output_description: 交付给用户的小红书帖子
---