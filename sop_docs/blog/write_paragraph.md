---
doc_id: blog/write_paragraph
description: Generate paragraph content for blog outline
aliases:
  - generate paragraph
  - write paragraph
  - create content
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  title: The main title of the blog post
  user_ask: Original user request for the blog content
  outline: The outline structure to write paragraphs for
output_description: Generated paragraph content for the blog sections
---

## parameters.prompt
Please write detailed content for the section [{section_title}] of the blog post about [{topic}].

整体大纲如下：
{outline}

请生成800-1200字的高质量内容，要求：
1. 内容充实、逻辑清晰
2. 语言流畅、易于理解
3. 包含具体例子和数据支撑

请按照以下JSON格式返回：
```json
{
  "new_task": ["继续下一节内容"],
  "段落内容": "这里是生成的段落内容..."
}
```
