---
description: 生成小红书图文任务
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  topic_list: 一个列表包含了建议生成的小红书图文的主题，一个主题一行
output_description: 生成的一系列任务，每一个任务是一条撰写小红书图文的具体内容要求
---
## parameters.prompt

### Objective
请为下面的主题生成一系列小红书图文撰写的任务，每个主题生成一个，例如： `<new task to execute>[生成任务x] 请根据 write_xiaohongshu_single_post.md 撰写一个吸引人的小红书图文。小红书的账号人设：xxx
，贴子的对象：xxxx，小红书帖子的主题：xxxx，当前帖子需要重点刺激的受众情感共鸣点：xxxx</new task to execute>`

需要展开的主题：

```
{topic_list}
```