---
description: 生成小红书图文任务
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  topic_list: 一个列表包含了建议生成的小红书图文的主题，一个主题一行
output_description: 一系列任务，包含小红书的
---
## parameters.prompt

### Objective
请为下面的主题生成一系列小红书图文撰写的任务，例如： `[生成任务x] 请根据 write_xiaohongshu_single_post.md  撰写一个吸引人的小红书图文。`

需要展开的主题：

```
{topic_list}
```