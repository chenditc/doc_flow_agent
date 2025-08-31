---
description: 生成小红书的图文帖子
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  human_setup: 当前小红书博主的人设
  topic: 当前任务需要生成的小红书的图文主题
  post_target_audience: 小红书图文的受众
output_description: 小红书图文的内容
---
## parameters.prompt

### Objective
请针对于小红书图文的受众“{post_target_audience}”，撰写一个符合小红书图文：{topic}

### Guidance
小红书的图文贴需要：
- 文字内容要包含 emoji，一般出现在句首或者段首。
- 以短句为主，充分换行保持呼吸感。
- 以生活化的语气为主，同时保持一定专业度。
- 符合博主人设：{human_setup}
- 不要直接点出博主人设，只要不违反博主人设即可。

首图一般用带有 emoji 的大字图即可。

### Return Format
请返回：
1. 该图文贴的首图设计（用文字描述清楚）。
2. 该图文贴的文字内容。