
---
design_version: 0.1
title: "Agent 文档层面设计规范"
description: |
  本文档定义了面向 Agent 的「任务文档」格式标准，支持以纯文本 Markdown + YAML Front Matter 存储。
  所有 Agent 的行为都通过加载、解释这些文档来执行。
author: "chenditc@gmail.com"
created: 2025-07-12
---

# Agent 文档层面设计规范

本设计旨在定义一种「可组合、可索引、易维护」的任务文档格式，所有 Agent 的执行逻辑都通过这些文档来解释，真正实现**“文档即流程，文档即代码”**的理念。

---

## 🌟 设计核心思想

✅ 每个文档只承担「单一职责」  
✅ 文档间通过「路径」互相引用，实现组合  
✅ 支持四大类型：plan、execute、validate、error_handler  
✅ 支持结构化参数和提示模板  
✅ 全部以 **Markdown + YAML Front Matter** 存储

---

## 📜 文档通用结构

所有文档统一的基本格式：

```markdown
---
task_id: 唯一ID路径
task_type: 类型（plan / execute / validate / error_handler）
description: 人类可读描述
tool:             # 如果需要调用外部工具
  tool_id: 工具唯一ID
  parameters:     # 模板参数
    - name: xxx
      value: 取自上下文的JSONPath
input:            # 需要从上下文中读取的输入
  变量名: JSONPath
output:           # 生成结果要写回的上下文位置
  JSONPath: JSONPath
error_handling:   # （可选）定义错误处理的策略
  on_failure:
    retry: 3
    replan: true
---

## parameters.prompt
这里是prompt模板，支持{变量}占位符
````

---

## ✅ 字段说明

| 字段              | 说明                                                  |
| --------------- | --------------------------------------------------- |
| task\_id        | 文档的唯一标识路径，用于引用                                      |
| task\_type      | 文档类型，可选值：plan / execute / validate / error\_handler |
| description     | 纯文本描述                                               |
| tool            | 可选，用于 execute / validate 类型的调用元信息                   |
| input           | 声明要从上下文中读取的变量映射                                     |
| output          | 声明生成结果要写回上下文的位置                                     |
| error\_handling | 定义失败时的重试/重规划策略                                      |

---

## ✅ 文档类型定义与示例

---

### ① Plan 文档

* 作用：将一个高阶任务拆解为多个子任务
* 特点：定义「拆解步骤」列表，每个子任务引用另一个文档

```markdown
---
task_id: blog/generate_blog
task_type: plan
description: 生成一篇完整的博客
plan_steps:
  - task_id: blog/generate_outline
  - task_id: blog/write_paragraphs
  - task_id: blog/generate_images
---

## Plan Details
本计划将用户的【写博客】需求拆解为三个步骤：生成大纲、写段落、配图。
```

---

### ② Execute 文档

* 作用：调用LLM或外部工具
* 特点：定义工具、输入/输出路径、参数模板

```markdown
---
task_id: blog/generate_outline
task_type: execute
description: 生成博客大纲
tool:
  tool_id: LLM
  parameters:
    - name: prompt
      value: "{parameters.prompt}"
input:
  title: "$.标题"
  user_ask: "$.用户原始输入"
output:
  "$.大纲": "$"
---

## parameters.prompt
请为主题【{title}】生成一个清晰的3-5小节大纲。这是为【{user_ask}】服务的。如果你对这个主题不熟悉，你可以只返回【{title}】作为小节。
```

---

### ③ Validate 文档

* 作用：对生成内容进行检查
* 特点：通常也会调用LLM或脚本进行判定
* 支持指定错误类型，并在错误处理里定义分支

```markdown
---
task_id: blog/validate_outline
task_type: validate
description: 校验生成的大纲
tool:
  tool_id: validate_script
  parameters:
    - name: input
      value: "$.大纲"
input:
  outline: "$.大纲"
output:
  "$.校验结果": "$"
error_handling:
  on_failure:
    retry: 2
    replan: false
    error_routing:
      "不够详细": "blog/handle_outline_not_detailed"
      "主题不相关": "blog/handle_outline_wrong_topic"
---

## parameters.prompt
请检查以下大纲是否与主题一致，且足够详细。如不符合，请给出错误类型。
```

---

### ④ Error Handler 文档

* 作用：当出现特定错误类型时，定义如何继续拆解或改进
* 特点：本质上是「Plan」的特例

```markdown
---
task_id: blog/handle_outline_not_detailed
task_type: plan
description: 处理大纲不够详细的问题
plan_steps:
  - task_id: blog/analyze_outline
  - task_id: blog/refine_outline
---

## Plan Details
如果大纲不够详细，先分析现有内容，再生成更细的子小节。
```

---

## ✅ Error Handling 设计模式

✅ 每个 validate 文档可定义 **error\_routing**：

```yaml
error_handling:
  on_failure:
    retry: 2
    replan: false
    error_routing:
      "错误类型A": "对应的ErrorHandler文档ID"
      "错误类型B": "对应的ErrorHandler文档ID"
```

⭐️ 解释：

* 如果校验失败 → 先retry
* retry耗尽 → 触发error\_routing
* 具体错误类型 → 转到相应ErrorHandler文档，生成新的子任务

---

## ✅ Tool 调用规范

任何文档里都可以使用`tool`字段：

```yaml
tool:
  tool_id: LLM
  parameters:
    - name: prompt
      value: "{parameters.prompt}"
```

⭐️ Agent执行时：

* 解析prompt模板
* 从上下文input\_path取值
* 填充后调用工具

---

## ✅ 输入输出路径

统一用 **JSONPath** 约定：

```yaml
input:
  title: "$.用户输入.标题"
output:
  "$.生成的大纲": "$"
```

* 输入阶段 → 从上下文里解析
* 输出阶段 → 写入上下文

---

## ✅ 任务流转与执行器模型

⭐️ Agent 主循环处理：
1️⃣ 从任务栈取任务
2️⃣ 加载文档 → 解释字段
3️⃣ 如果是plan → 生成子任务，入栈
4️⃣ 如果是execute → 调用工具，写回上下文
5️⃣ 如果是validate → 校验结果
6️⃣ 失败 → 按error\_handling策略生成新任务

---

## ✅ 存储和索引设计

⭐️ 存储

* 文件系统 / Git 仓库
* 每个文档单独一个md文件
* 文档ID = 文件路径

⭐️ 索引

* 精确索引：通过路径ID加载
* 语义索引：通过向量数据库模糊检索
* 标签和领域信息可选附加

---

## ✅ 推荐目录结构

```
/sop/
  blog/
    generate_blog.md
    generate_outline.md
    validate_outline.md
    handle_outline_not_detailed.md
```

---

## ✅ 示例：最简单的 Execute 文档

```markdown
---
task_id: blog/write_paragraph
task_type: execute
description: 生成一个段落
tool:
  tool_id: LLM
  parameters:
    - name: prompt
      value: "{parameters.prompt}"
input:
  section_title: "$.大纲[0]"
output:
  "$.段落[0]": "$"
---

## parameters.prompt
请根据标题【{section_title}】生成一个至少300字的博客段落。
```

---

## ✅ 示例：最简单的 Validate 文档

```markdown
---
task_id: blog/validate_paragraph
task_type: validate
description: 检查段落长度和主题
tool:
  tool_id: LLM
  parameters:
    - name: prompt
      value: "{parameters.prompt}"
input:
  paragraph: "$.段落[0]"
output:
  "$.校验结果": "$"
error_handling:
  on_failure:
    retry: 2
    error_routing:
      "过短": "blog/handle_paragraph_too_short"
---

## parameters.prompt
请检查以下段落是否超过300字并与主题一致，如不符合请返回错误类型。
```

---

## ✅ 示例：Error Handler 文档

```markdown
---
task_id: blog/handle_paragraph_too_short
task_type: plan
description: 解决段落过短的问题
plan_steps:
  - task_id: blog/expand_paragraph
---

## Plan Details
当段落过短时，先分析现有内容，再尝试扩展。
```

---

## ✅ 结尾总结

⭐️ 这个文档规范旨在：

✅ 让每个文档最小、单一职责
✅ 通过路径引用任意组合
✅ 错误处理可以通过error\_handler进行分支
✅ 所有生成步骤都支持LLM + prompt调用

Agent只需解释这些文档，即可灵活运行任何复杂的工作流。

---