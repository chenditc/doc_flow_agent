

## 目录

1️⃣ 概述与设计原则
2️⃣ 系统架构与组件
3️⃣ 核心概念定义

* 任务
* 文档(SOP)
* 上下文

4️⃣ 文档（SOP）格式规范
5️⃣ 任务结构设计
6️⃣ 上下文数据结构
7️⃣ 文档存储与索引设计
8️⃣ 执行流程设计
9️⃣ 工具调用规范
1️⃣0️⃣ 附录：示例

---

## 1️⃣ 概述与设计原则

本框架的目标是：

* 极简核心代码逻辑
* 把流程逻辑和领域知识**全部转移到文档（SOP）里**
* 允许**逐步从「通用流程」到「细化领域流程」演进**

**设计原则：**

✅ 文档最小职责
✅ 文档可组合、可引用
✅ Agent是一个「文档解释器」
✅ 领域知识注入通过文档，不改动代码

---

## 2️⃣ 系统架构与组件

整体架构分为以下部分：

```
┌────────────────────────────┐
│         User Input          │
│ e.g. “写一篇关于AI的博客”  │
└─────────────┬────────────────┘
              │
              ▼
┌────────────────────────────┐
│        任务编译器            │
│ - 语义搜索SOP文档             │
│ - 解析任务描述 → 格式化任务    │
└─────────────┬────────────────┘
              │
              ▼
┌────────────────────────────┐
│       执行引擎 (主循环)       │
│ - 任务栈管理                 │
│ - 文档解析                   │
│ - 工具调用                   │
│ - 校验/失败策略              │
└─────────────┬────────────────┘
              │
              ▼
┌────────────────────────────┐
│         上下文存储            │
│ - 所有中间结果                │
│ - 支持JsonPath查询            │
└────────────────────────────┘
```

---

## 3️⃣ 核心概念定义

### ✅ 3.1 任务（Task）

* Agent的最小执行单元
* 定义了：

  * 做什么（description）
  * 用哪个SOP文档
  * 输入/输出在上下文的位置
  * 工具调用参数

---

### ✅ 3.2 文档（SOP）

* 人类可读可写的**任务指引**
* 定义了如何把「自然语言任务描述」转化成可执行任务
* 也定义工具调用、校验、错误处理

---

### ✅ 3.3 上下文

* 一个多层次JSON对象
* 存储所有任务的输入/输出
* 每个任务声明自己的input\_path和output\_path
* 通过JsonPath或类似语法读取写入

---

## 4️⃣ 文档（SOP）格式规范

### ✅ 文件格式

* Markdown文件
* 前置YAML（front matter）+ 正文

---

### ✅ 示例格式

```markdown
---
doc_id: blog/generate_outline
description: 生成博客大纲
aliases:
  - 撰写大纲
  - 博客大纲
tool:
  tool_id: LLM
  parameters:
    - prompt: {parameters.prompt}
input:
  title: "$.标题"
  user_ask: "$.用户原始输入"
output:
  data_keys: ["outline"]
---

## parameters.prompt
请为主题【{title}】生成一个清晰的3-5小节大纲。这是为【{user_ask}】服务的。如果你对这个主题不熟悉，你可以只返回【{title}】作为小节。
```

---

### ✅ 支持字段

| 字段              | 说明                   |
| --------------- | -------------------- |
| doc\_id         | 文档唯一标识               |
| description     | 文档简介                 |
| aliases         | 可能匹配的任务短语            |
| tool            | 调用的工具信息（ID、参数模板）     |
| input           | 上下文输入字段映射（json path） |
| output          | 期望写入的上下文位置或键         |
| error\_handlers | 校验失败后指定的处理文档ID       |

---

### ✅ 文档类别

虽然所有文档结构类似，但**语义上可以分为：**

* **Plan 文档**：会输出多个 new\_task
* **Execute 文档**：调用工具，产生 output
* **Validate 文档**：调用工具或脚本来检查结果，可能产生 error\_handler
* **ErrorHandler 文档**：规划「如何修复错误」

✅ 这些类别只是人类语义标签，系统角度都是「解释指引」！

---

## 5️⃣ 任务结构设计

所有任务遵循统一格式：

```json
{
  "task_id": "uuid",
  "description": "生成博客大纲",
  "sop_doc_id": "blog/generate_outline",
  "tool": {
     "tool_id": "LLM",
     "parameters": {
       "prompt": "..."
     }
  },
  "input": {
     "title": "$.标题",
     "user_ask": "$.用户原始输入"
  },
  "output": {
     "outline": "$.大纲"
  }
}
```

---

### ✅ 特别字段

| 字段           | 说明         |
| ------------ | ---------- |
| description  | 人类可读的任务意图  |
| sop\_doc\_id | 指向的SOP文档ID |
| tool         | 工具调用信息     |
| input        | 上下文输入映射    |
| output       | 上下文输出映射    |

---

## 6️⃣ 上下文数据结构

* 单个**全局JSON对象**
* 所有任务读写这个「黑板」
* 支持JsonPath语法访问

✅ 示例

```json
{
  "用户原始输入": "写一篇关于环境保护的博客",
  "标题": "环境保护",
  "大纲": [
     "环境问题的现状",
     "保护环境的措施",
     "未来展望"
  ],
  "段落": [
     {"标题": "...", "文本": "..."}
  ]
}
```

✅ 好处：

* 任务之间共享信息
* 可持久化到磁盘或数据库
* 易于调试

---

## 7️⃣ 文档存储与索引设计

✅ 存储：

* 文件系统即可
* 按照`doc_id`路径存储.md文件

✅ 索引：

* 建立语义搜索索引

  * 使用embedding模型
  * 支持从用户任务描述中检索最相关的文档
* 支持路径索引

  * 文档内部可以写死指向别的文档

✅ 查询流程：

* 用户提出自然语言任务

  * 先做语义搜索找到最匹配的文档
  * 如果信心不足，用通用SOP
* Agent执行时

  * 解析new\_task里的自然语言
  * 继续语义搜索/路径索引找到对应文档

---

## 8️⃣ 执行流程设计

✅ 主循环：
1️⃣ 从任务栈取出任务
2️⃣ 加载其指向的文档
3️⃣ 解析文档：

* 输入路径 → 填充输入
* 渲染Prompt或参数
  4️⃣ 调用工具
  5️⃣ 工具输出：
* 输出文本
* 通过大模型「编译」为标准化格式：

  ```json
  {
    "new_task": ["..."],
    "data": {
      "path": "value"
    }
  }
  ```

6️⃣ 更新上下文
7️⃣ 如果有new\_task → 语义解析 → 找到SOP → 变成任务 → 入栈

---

✅ 错误处理：

* validate本身是一个普通的任务
* 如果校验失败 → 输出new\_task描述 → 解释为新的任务
* 可以通过文档链式调用error\_handler来设计复杂的纠错流程

---

✅ 任务生命周期

* plan → 产生 new\_task
* execute → 产生 output
* validate → 产生 new\_task（如果失败）

---

## 9️⃣ 工具调用规范

✅ 工具注册表

* key → 实现函数或CLI
* LLM
* CLI工具
* 本地脚本

✅ 调用约定

```json
{
  "tool_id": "LLM",
  "parameters": {
    "prompt": "..."
  }
}
```

✅ LLM工具

* 支持prompt模板
* 支持变量替换
* 支持多段markdown（用于写复杂的system提示）

✅ CLI工具

* 参数指定
* 输入/输出文件或标准IO

---

## 1️⃣0️⃣ 附录：一个完整例子

---

### 用户输入

```
写一篇关于“环境保护”的博客
```

---

### 任务编译器生成首个任务

```json
{
  "description": "生成一篇关于环境保护的博客",
  "sop_doc_id": "blog/generate_blog",
  "input": {
    "user_ask": "$.用户原始输入"
  }
}
```

---

### blog/generate\_blog.md

```markdown
---
doc_id: blog/generate_blog
description: 生成一篇博客
aliases:
  - 写博客
  - 生成博客
拆解方式:
  - 步骤1: 生成大纲，使用文档【blog/generate_outline】
  - 步骤2: 对大纲各段落生成文本，使用文档【blog/write_paragraph】
  - 步骤3: 校验文章，使用文档【blog/validate_blog】
---
```

---

### blog/generate\_outline.md

```markdown
---
doc_id: blog/generate_outline
description: 生成博客大纲
aliases:
  - 撰写大纲
tool:
  tool_id: LLM
  parameters:
    - prompt: {parameters.prompt}
input:
  title: "$.标题"
  user_ask: "$.用户原始输入"
output:
  data_keys: ["大纲"]
---

## parameters.prompt
请为主题【{title}】生成一个清晰的3-5小节大纲，帮助撰写文章，用户意图是【{user_ask】。
```

---

### Agent行为

✅ 先跑Plan文档 → 生成大纲
✅ 产生子任务：

```
new_task:
  - "为以下大纲生成段落：..."
```

✅ 语义解析找到blog/write\_paragraph.md
✅ 继续执行 → 产生段落
✅ 最后跑validate\_blog.md做校验

---

✅ 如果校验失败 → validate文档定义

```
错误处理：
  - 如果错误类型=太短 → 使用文档【blog/expand_paragraph】
```

✅ Agent继续生成「修复任务」

