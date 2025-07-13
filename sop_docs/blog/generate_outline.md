---
doc_id: blo## parameters.prompt
Please generate a clear 3-5 section outline for the topic [{title}] to help with article writing. The outline should start with an intriguing, thought-provoking opening that captures attention, possibly by presenting a counterintuitive fact from daily life.

If you are not familiar with this topic, you can simply return [{title}] as a single section.

If the topic [{title}] might be controversial, suggest that the user refer to "doc/more_info.md" for further research after generating the outline.rate_outline
description: Generate blog outline structure
aliases:
  - create outline
  - blog outline  
  - write outline
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  title: The title of the blog for which to generate an outline
output_description: A structured blog outline based on the title and writing purpose
---
## parameters.prompt
请为主题【{title}】生成一个清晰的3-5小节大纲，帮助撰写文章。大纲的开头一定要离奇、吸引人思考，可以通过提出一个生活中的反常识事实来实现。

如果你对这个主题不熟悉，你可以只返回【{title}】作为单个小节。

如果主题【{title}】有可能引起争议，在生成完大纲后建议用户参考文档 “doc/more_info.md” 进行进一步调研。