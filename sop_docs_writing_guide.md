# How to write executable sop docs

This guide shows how to convert workflows from visual tools like Dify, Logic App, Coze, or Python scripts into executable SOP documents that can be chained together and executed programmatically.

## Each doc is a tool use

Think about each doc as a node in "Logic App" / "Dify" / "Coze", which takes input, executes some tool and outputs values.

### Example: Converting a Dify Workflow Node

**Dify Node**: "Generate Blog Post Ideas"
- Input: topic, target_audience
- Tool: LLM 
- Output: List of blog ideas

**SOP Document Equivalent**:
```markdown
---
description: Generate creative blog post ideas for a given topic
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.prompt}"
input_description:
  topic: The main subject for blog posts
  target_audience: The intended readers
output_description: A list of creative blog post ideas with brief descriptions
---
## parameters.prompt

Please generate 5 creative blog post ideas for the topic: {topic}
Target audience: {target_audience}

Format each idea as:
- Title: [Catchy title]
- Description: [Brief description]
- Angle: [Unique perspective]
```

### Workflow Node Types and SOP Patterns

**Planning Node** (Break down complex tasks):
- Use `LLM` or `TEMPLATE` tools
- Generate execution plans
- Wrap subtasks with `<new task to execute>` tags

**Execution Node** (Perform specific actions):
- Use specialized tools (`PYTHON_EXECUTOR`, `CLI`, etc.)
- Execute single, focused operations
- Process data or interact with external systems

**Merge/Aggregate Node** (Combine results):
- Use `PYTHON_EXECUTOR` tool
- Merge multiple inputs into final output
- Format results for user consumption

## Doc Structure

Each SOP document has a standardized two-part structure that enables automatic parsing and execution:

### YAML Front Matter (Metadata)

The YAML section defines the document's behavior and tool configuration:

```yaml
---
description: Human-readable description of what this document does
aliases:                    # Optional: alternative names for this document
  - short_name
  - alternative_name
tool:
  tool_id: TOOL_NAME        # Which tool to execute (LLM, PYTHON_EXECUTOR, etc.)
  parameters:               # Tool-specific parameters
    param1: "value"
    param2: "{parameters.section_name}"  # Reference to markdown section
input_json_path:            # Optional: JSON path mappings for input data
  field1: "$.path.to.input"
output_json_path: "$.path.to.output"  # Optional: JSON path for output
input_description:          # Documentation for expected inputs
  field1: Description of what this input should contain
output_description: Description of what this document outputs
---
```

### Markdown Body (Content)

The markdown section contains the actual content, organized into named sections:

```markdown
## parameters.prompt
This section contains the LLM prompt template with {variable} placeholders.

## parameters.script  
This section might contain Python code for PYTHON_EXECUTOR tool.

## Additional Section
Any section starting with ## can be referenced in the YAML parameters.
```

### Document Loading and Parsing Process

The system processes SOP documents through several stages:

1. **File Discovery**: `SOPDocumentLoader` scans the `sop_docs` directory recursively for `.md` files

2. **Content Parsing**: 
   - Separates YAML front matter from markdown body using `---` delimiters
   - Parses YAML metadata using `yaml.safe_load()`
   - Extracts markdown sections using regex pattern `^## (.+?)\n(.*?)(?=^## |\Z)`

3. **Parameter Resolution**:
   - Finds references like `"{parameters.prompt}"` in tool parameters
   - Replaces them with corresponding markdown section content
   - Validates that all required sections exist

4. **Document Object Creation**:
   - Creates `SOPDocument` dataclass with all parsed information
   - Validates required fields (`tool.tool_id`, `description`)
   - Stores both original and processed versions

5. **Execution Context**:
   - `DocExecuteEngine` loads documents on-demand
   - Resolves input data using JSON path expressions
   - Renders templates with runtime variables using `{variable}` syntax
   - Executes the specified tool with processed parameters

### Document Selection Process

When executing natural language commands, the system:

1. **Candidate Matching**: Finds potential documents by matching:
   - Full document path in description
   - Filename in description
   - Alias matches

2. **LLM Validation**: Uses LLM to select best match from candidates based on:
   - Task description alignment
   - Tool capabilities
   - Input/output compatibility

3. **Context Resolution**: Extracts input data from current execution context using JSON paths

## Tool Choices

There are several built-in tools, each suited for different workflow node types:

### LLM Tool
- **Use Case**: Text generation, analysis, dynamic planning
- **Dify Equivalent**: LLM nodes, text processing
- **Parameters**: `prompt` (template with variables)
- **Example**: Content generation, task planning, text analysis

### PYTHON_EXECUTOR Tool  
- **Use Case**: Deterministic logic, data processing, calculations, structured transformations, lightweight integration calls
- **Dify Equivalent**: Code execution, data transformation
- **Primary Parameters**:
  - `task_description`: Natural language description of the desired transformation or computation
  - `related_context_content` (optional): Structured/context data passed to the code generator for awareness
  - (Optional direct mode) `python_code`: If supplied, skips generation and executes directly
- **Entry Point Contract**: The executed code MUST define a function `def process_step(context: dict):`
  1. Receives a dictionary `context` (merged runtime context + any `related_context_content`)
  2. Returns a JSON-serializable value (primitive, list, or dict)
  3. Should avoid unintended side effects (no random external writes unless required)
- **Runtime Behavior**:
  - If `python_code` absent, an LLM prompt (see `sop_docs/tools/python.md`) generates the complete function
  - Code is executed in a subprocess; output includes: `python_code`, `return_value`, `stdout`, `stderr`, `exception`
- **Examples**: Data merging, complex calculations, result aggregation, formatting structured output
- **Good Pattern**:
```
def process_step(context: dict):
    items = context.get("items", [])
    total = sum(i.get("value", 0) for i in items)
    return {"count": len(items), "total": total}
```
- **Common Pitfall**: Forgetting a return statement (implicitly returning `None`). Always return structured data.

### TEMPLATE Tool
- **Use Case**: Deterministic text / plan rendering (no logic branching)
- **Dify Equivalent**: Template nodes, variable substitution
- **Source of Truth**: The markdown body itself is the template; YAML usually keeps `parameters: {}` for this tool
- **Variable Resolution**: Placeholders like `{recipient_name}` come from values mapped via `input_json_path`
- **Examples**: Generating structured output, formatting data, stable process task planning (see `sop_docs/examples/generate_personalized_email.md`)
- **Failure Mode**: Missing variable raises error—document all placeholders in `input_description`.

### CLI Tool
- **Use Case**: System commands, external tool integration, quick inspection
- **Logic App Equivalent**: PowerShell/Bash script actions
- **Parameters**:
  - Direct: `command`
  - Or generative: `task_description` (tool will LLM-generate a command if `command` absent)
- **Output**: `stdout`, `stderr`, `returncode`, `executed_command`, `success`
- **Examples**: File operations, system administration, listing artifacts, grepping logs (see `sop_docs/tools/bash.md`)
- **Tip**: Prefer idempotent, read-only commands in automated chains.

### USER Tool
- **Use Case**: Human interaction, input collection, approvals
- **Dify Equivalent**: User input nodes, approval steps
- **Parameters**: `message` (prompt for user, often referencing a section like `{parameters.message}`)
- **Examples**: Collecting requirements, confirmation steps, selecting among alternatives (see `sop_docs/tools/web_user_communicate.md`)
- **Design Tip**: Only insert when genuine human judgment or missing data is required—avoid unnecessary interruptions.

## Examples from xiaohongshu Workflow

### Planning Node Example
**File**: `generate_post_task_list.md`
```yaml
tool:
  tool_id: LLM  # Uses LLM for intelligent task generation
  parameters:
    prompt: "{parameters.prompt}"
```
Generates `<new task to execute>` tags for each subtask to be processed.

### Execution Node Example  
**File**: `write_xiaohongshu_single_post.md`
```yaml
tool:
  tool_id: LLM  # Focused execution of single post generation
  parameters:
    prompt: "{parameters.prompt}"
```
Takes specific inputs (topic, audience) and produces a single deliverable.

### Merge Node Example
**File**: `merge_xiaohongshu_result.md`
```yaml
tool:
  tool_id: PYTHON_EXECUTOR  # Uses Python for data aggregation
  parameters:
    task_description: "Format and merge multiple posts into readable markdown"
```
Combines outputs from multiple execution nodes into final result.

## Converting Existing Workflows

### From Dify/Coze Workflows:
1. **Identify Node Types**: Map each node to planning/execution/merge pattern
2. **Extract Prompts**: Convert node prompts to `## parameters.prompt` sections
3. **Map Variables**: Replace node variables with `{variable}` syntax
4. **Define I/O**: Document input_description and output_description
5. **Chain Tasks**: Use `<new task to execute>` for multi-step workflows

### From Python Scripts:
1. **Break into Functions**: Each significant function becomes a document
2. **Identify Dependencies**: Map function parameters to input_description
3. **Choose Tool**: Use PYTHON_EXECUTOR for complex logic, LLM for AI tasks
4. **Template Variables**: Replace hardcoded values with {variable} placeholders

### From Logic Apps:
1. **Map Triggers/Actions**: Convert each action to a tool invocation
2. **Preserve Conditions**: Use LLM tool for decision logic
3. **Handle Loops**: Break into individual task documents with planning nodes
4. **External Calls**: Use CLI tool or PYTHON_EXECUTOR for API calls

This approach transforms rigid, tool-specific workflows into flexible, reusable, and chainable SOP documents that can be executed programmatically while maintaining human readability.

## Triggering Document Execution

Users can trigger specific SOP documents in several ways:

### Direct Document Reference
Users can explicitly reference a document by name:
```
"Follow write_xiaohongshu_single_post.md to create a post about travel tips"
"Execute generate_topic_idea.md for my blog"
"Use merge_xiaohongshu_result.md to combine the posts"
```

### Chaining Documents
Documents can trigger other documents using the `<new task to execute>` pattern:

**In Planning Documents:**
```markdown
<new task to execute>[Task 1] Follow write_xiaohongshu_single_post.md to write about {topic1}</new task to execute>
<new task to execute>[Task 2] Follow write_xiaohongshu_single_post.md to write about {topic2}</new task to execute>
<new task to execute>[Final] Use merge_xiaohongshu_result.md to combine all posts</new task to execute>
```

This creates a workflow where:
1. Planning document generates subtasks
2. Each subtask references a specific execution document
3. Final merge document combines results

### Best Practices for Document References

**For Document Authors:**
- Use descriptive filenames that reflect the document's purpose
- Add meaningful aliases for common alternative names
- Write clear descriptions that help with automatic selection

**For Users:**
- Use specific document names when you know exactly what you want
- Include the `.md` extension for clarity
- Provide context about your specific requirements

This direct referencing approach gives users precise control over workflow execution while maintaining the flexibility of natural language interaction.

