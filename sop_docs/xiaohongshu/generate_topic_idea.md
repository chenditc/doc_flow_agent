---
description: 生成小红书的图文主题
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_json_path:
  task_description: $.current_task
input_description:
  direction: 小红书的图文内容方向，例如生活经验分享、理财产品评测等
  post_target_audience: 小红书图文的受众
  post_num: 需要几个图文主题，一个数字
  current_date: 当前时间
output_description: 小红书图文的主题列表
---
## parameters.prompt

### Objective
{task_description}

### Guidance
1. 先分析对于受众{post_target_audience}，他们的痛点有什么，列出{post_num}个不同的痛点。最好是与当前时间{current_date}有关的，时令、季节、特殊时间节点相关的。
2. 针对每一个痛点，分析可能什么样的帖子会导致他们愿意点击、阅读、讨论。
3. 针对每一个可能的帖子类型，提出一个图文主题。每一个图文主题要标注序号。