# Doc Flow Agent: Technical Design Specification

**Version:** 1.0  
**Last Updated:** August 19, 2025  
**Authors:** Di Chen
**Document Status:** In Progress

## Executive Summary

The Doc Flow Agent is a document-driven task execution framework that implements a novel approach to AI agent architecture. Unlike traditional hardcoded agent systems, this framework externalizes all business logic and domain knowledge into Standard Operating Procedure (SOP) documents, creating a highly flexible and maintainable agent system.

### Key Innovations
- **Document-Driven Architecture**: All task logic resides in markdown SOP documents
- **Intelligent Path Generation**: Biomimetic approach to context data management
- **Comprehensive Observability**: Multi-phase execution tracing with complete LLM call logging
- **Auto-Recovery Mechanisms**: Intelligent error handling with automatic task generation
- **Execution Isolation**: Prefixed output paths prevent data conflicts

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/chenditc/doc_flow_agent.git
cd doc_flow_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys (the file will be automatically loaded)
```

4. Run a simple example:
```python
import asyncio
from doc_execute_engine import DocExecuteEngine

async def main():
    engine = DocExecuteEngine()
    await engine.start("Check current time using bash")

if __name__ == "__main__":
    asyncio.run(main())
```

### Requirements
- Python 3.8+
- OpenAI API key or compatible LLM API
- Unix-like environment (Linux/macOS recommended)

### Visualization

The project includes a web-based visualization system for monitoring and analyzing execution traces in real-time:

```bash
# Start the visualization server
cd visualization/frontend-react && npm install && npm run build && cd .. && source ../.venv/bin/activate && uvicorn server.viz_server:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000 to view execution traces, task timelines, and debug information. See [`visualization/README.md`](visualization/README.md) for detailed setup and development instructions.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Core Concepts](#2-core-concepts)  
3. [SOP Document Specification](#3-sop-document-specification)
4. [Task Management System](#4-task-management-system)
5. [Context Data Architecture](#5-context-data-architecture)
6. [Document Storage & Indexing](#6-document-storage--indexing)
7. [Execution Engine Design](#7-execution-engine-design)
8. [Tool Integration Framework](#8-tool-integration-framework)
9. [Observability & Tracing](#9-observability--tracing)
10. [Implementation Examples](#10-implementation-examples)
11. [API Reference](#11-api-reference)

---

## 1. Architecture Overview

### 1.1 System Architecture

The Doc Flow Agent implements a five-phase execution pipeline with comprehensive tracing capabilities:

```
┌─────────────────────────────┐
│        User Input           │
│    "Check Beijing time"     │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│     DocExecuteEngine        │
│  • LIFO Task Stack          │
│  • Main Execution Loop      │
│  • Error Handling & Retry   │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│   Phase 1: SOP Resolution   │
│  • SOPDocumentParser        │
│  • Semantic Matching        │
│  • LLM Validation           │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│   Phase 2: Task Creation    │
│  • JsonPathGenerator        │
│  • Smart Input Path Gen     │
│  • Missing Input Detection  │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│   Phase 3: Task Execution   │
│  • Tool Invocation          │
│  • Dynamic Output Path Gen  │
│  • Execution Counter Mgmt   │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  Phase 4: Context Update    │
│  • JSON Path Writing        │
│  • Temporary Data Cleanup   │
│  • State Persistence        │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Phase 5: New Task Generation│
│  • LLM Output Parsing       │
│  • Task Description Extract │
│  • Task Stack Management    │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│      ExecutionTracer        │
│  • Phase-Level Tracking     │
│  • LLM Call Logging         │
│  • JSON Persistence         │
└─────────────────────────────┘
```

### 1.2 Design Principles

- **Document-First**: All business logic externalized to SOP documents
- **Minimal Core**: Simple, maintainable engine with complex behavior in documents
- **Composable Architecture**: Documents can reference and chain together
- **Agent as Interpreter**: Core engine interprets and executes document instructions
- **Zero-Code Domain Logic**: Domain expertise injected via documents, not code changes

### 1.3 Key Components

| Component | Responsibility |
|-----------|----------------|
| `DocExecuteEngine` | Main execution loop, task stack management |
| `SOPDocumentLoader` | Document parsing and loading |
| `JsonPathGenerator` | Intelligent input/output path generation |
| `ExecutionTracer` | Comprehensive observability and logging |
| `BaseTool` | Abstract tool interface |
| `Task` | Execution unit data structure |

---

## 2. Core Concepts

### 2.1 Task

A **Task** represents the atomic unit of execution in the system. Each task encapsulates:

- **What to do**: Human-readable description
- **How to do it**: Reference to SOP document
- **Input/Output mapping**: JSON paths for context data
- **Tool configuration**: Specific tool and parameters

```python
@dataclass
class Task:
    task_id: str                    # UUID identifier
    description: str                # Human-readable description
    sop_doc_id: str                # SOP document reference
    tool: Dict[str, Any]           # Tool configuration
    input_json_path: Dict[str, str] # Input field mappings
    output_json_path: str          # Output JSON path
    output_description: str        # Output semantic description
```

### 2.2 Standard Operating Procedure (SOP)

SOPs are **human-readable task guides** that define how to transform natural language task descriptions into executable tasks. They specify:

- Tool invocation patterns
- Input/output requirements  
- Parameter templates
- Error handling strategies

### 2.3 Context

The **Context** is a global JSON object serving as a shared "blackboard" for all tasks:

- Stores all task inputs and outputs
- Supports JsonPath syntax for data access
- Implements execution-scoped namespacing
- Provides persistence and state recovery

---

## 3. SOP Document Specification

### 3.1 Document Structure

SOP documents use Markdown format with YAML front matter:

```markdown
---
doc_id: tools/bash
description: Execute bash commands in sandbox environment
aliases:
  - shell command
  - terminal
tool:
  tool_id: CLI
  parameters:
    command: "{parameters.bash_command}"
input_description:
  command: "The bash command or script to execute"
output_description: "Command execution results with stdout/stderr"
---

## parameters.bash_command

Execute the following command: {command}

Additional context: {context}
```

### 3.2 Field Specifications

| Field | Type | Description | Priority |
|-------|------|-------------|----------|
| `doc_id` | String | Unique document identifier | Required |
| `description` | String | Document summary | Required |
| `aliases` | Array | Alternative task phrases for matching | Optional |
| `tool` | Object | Tool configuration (ID + parameters) | Required |
| `input_description` | Object | Semantic input requirements | Optional |
| `input_json_path` | Object | Direct JSON path mappings | Optional |
| `output_description` | String | Semantic output description | Optional |
| `output_json_path` | String | Direct output JSON path | Optional |
| `parameters` | Object | Markdown section templates | Optional |

### 3.3 Intelligent Path Generation

#### Biomimetic Design Philosophy

The system emulates human workflow patterns when working with "scratch paper":

- **Tagged Storage**: Each information piece has semantic labels for quick location
  - *Human behavior*: Writing "Phone numbers", "Meeting notes", "TODO items" as headers
  - *System mapping*: Context keys like `$.current_task`, `$.user_request` serve as semantic labels
  - *Implementation*: JsonPath expressions act as hierarchical tags for data organization

- **Similarity Search**: Find similar candidates first, then confirm the best match
  - *Human behavior*: Scanning scratch paper for "something about time" or "that command I wrote earlier"
  - *System mapping*: Context candidate analysis scans all existing keys for semantic relevance
  - *Implementation*: LLM analyzes context schema and identifies fields like `$.previous_command` for reuse

- **Progressive Confirmation**: Step-by-step filtering rather than exact matching
  - *Human behavior*: "This looks relevant... let me check if it's actually what I need"
  - *System mapping*: Four-step process from broad candidate search to specific extraction
  - *Implementation*: Candidate analysis → Code generation → Content extraction → Path mapping

- **Write-and-Tag**: Immediately label and store generated information
  - *Human behavior*: Writing down results with clear labels like "Beijing time: 3:42 PM"
  - *System mapping*: Generated content stored with descriptive prefixed keys
  - *Implementation*: `msg1_beijing_time_result` instead of generic `output` or `result`

- **Selective Retention**: Keep only useful information; discard metadata like "where input came from"
  - *Human behavior*: Keeping the phone number but throwing away the sticky note about "got this from John"
  - *System mapping*: Temporary `_temp_input_*` keys are cleaned up after successful extraction
  - *Implementation*: Task execution metadata is traced but not persisted in working context

- **Format Adaptation**: Each step can reformat inputs to match tool requirements
  - *Human behavior*: Rewriting "call mom tomorrow" as "Call: Mom, Time: Tomorrow 2PM" for calendar entry
  - *System mapping*: Extraction code can transform context data to match tool parameter expectations
  - *Implementation*: Generated Python functions convert raw task descriptions into specific command formats

#### Four-Step Input Processing

**Step 1: Context Candidate Analysis**
- Scan all context key-value pairs for semantically relevant fields
- Use LLM to analyze which existing data might relate to required input
- Generate candidate field list with current values:

```json
{
  "$.current_task": "Check Beijing time with bash",
  "$.user_original_request": "...",
  "$.previous_command": "..."
}
```

**Step 2: Extraction Code Generation**
- Generate Python extraction functions based on candidates and input descriptions
- Support multiple strategies: direct extraction, format conversion, content synthesis
- Code example:

```python
def extract_func(context):
    # Extract command keywords from task description
    task = context.get('current_task', '')
    if 'bash' in task and 'time' in task:
        return 'TZ=Asia/Shanghai date'
    return context.get('fallback_command', '')
```

**Step 3: Content Extraction**
- Safely execute generated extraction code to obtain actual input values
- If extraction fails or returns special markers, throw `TaskInputMissingError`
- Trigger automatic recovery mechanism to generate tasks for missing information

**Step 4: Path Mapping**
- Store extracted content in temporary keys: `_temp_input_{uuid}`
- Generate JSON paths pointing to temporary keys: `$['_temp_input_abc123']`
- Ensure task execution can correctly find required input values

---

## 4. Task Management System

### 4.1 Task Data Structure

The Task object encapsulates all information needed for execution:

```python
@dataclass
class Task:
    task_id: str                    # UUID task identifier
    description: str                # Human-readable task intent
    sop_doc_id: str                # Pointer to SOP document ID
    tool: Dict[str, Any]           # Tool invocation configuration
    input_json_path: Dict[str, str] # Input field to JSON path mapping
    output_json_path: str          # Output JSON path (dynamic generation supported)
    output_description: str        # Output description (for dynamic path generation)
```

### 4.2 Task Creation Pipeline

**Natural Language to Task Object Flow**:

1. **SOP Resolution**: Parse task description → Match SOP document ID
2. **Document Loading**: Load corresponding SOP document  
3. **Path Generation**:
   - If `input_json_path` exists: Use directly
   - If only `input_description`: Generate paths intelligently
4. **Task Construction**: Create complete Task object

### 4.3 Execution-Time Path Processing

**Input Path Resolution**:
- Extract values from context using `input_json_path`
- Throw `TaskInputMissingError` for missing required inputs
- Auto-generate recovery tasks to obtain missing information

**Output Path Processing**:
- Support static predefined paths (`output_json_path`)
- Support dynamic path generation (based on `output_description`)
- Auto-add execution counter prefix: `msg{counter}_{original_key}`

### 4.4 Task Stack Management

**LIFO Stack Design**:
- New tasks added to stack top for priority execution
- Support task decomposition and sub-task management
- Recovery tasks automatically inserted before failed tasks

**Task Retry Mechanism**:
- Maximum retry attempts: 3 times
- Retry counter tracks attempt count per task
- Clear retry count on successful recovery task execution

---

## 5. Context Data Architecture

### 5.1 Core Design

- **Global JSON Object**: Single mutable state store
- **JsonPath Access**: Uses jsonpath_ng library for path resolution  
- **Persistent Storage**: Auto-save to context.json file
- **Namespace Management**: Execution counter prefixes prevent conflicts

### 5.2 Path Prefix System

**Execution Counter Prefixes**:
- Format: `msg{execution_count}_{original_key}`
- Examples: `msg1_outline`, `msg2_user_input`  
- Purpose: Prevent output overwrites during multiple executions

**Path Transformation Examples**:
```
Original: $.outline
Transformed: $.msg1_outline

Original: $.blog.title  
Transformed: $.msg1_blog.title

Original: $.items[0]
Transformed: $.msg1_items[0]
```

### 5.3 Temporary Data Management

**Temporary Input Keys**:
- Prefix: `_temp_input_` + UUID
- Usage: Store JsonPathGenerator intermediate results
- Cleanup: Auto-delete after each task execution completion

**Context Cleanup Flow**:
1. Execute task and generate output
2. Store output to prefixed path
3. Clean all `_temp_input_*` keys
4. Save updated context

### 5.4 Data Structure Examples

```json
{
  "current_task": "Write a blog about environmental protection",
  "user_original_input": "Write a blog about environmental protection",
  
  "_temp_input_abc123": "Environmental Protection",
  
  "msg1_title": "Environmental Protection",
  "msg1_outline": [
     "Current Environmental Issues",
     "Environmental Protection Measures", 
     "Future Outlook"
  ],
  "msg2_paragraphs": [
     {"title": "...", "text": "..."}
  ],
  "msg3_final_article": "Complete blog content..."
}
```

### 5.5 Context Access Patterns

**Read Operations**:
- `resolve_json_path(path, context)`: Parse JSON path to get values
- Support complex paths: `$.blog.sections[0].title`
- Error handling: Return None when path doesn't exist

**Write Operations**:
- `set_json_path_value(context, path, value)`: Set JSON path values
- Auto-create intermediate paths: Create parent objects when they don't exist
- Type safety: Ensure path structure consistency

**Utility Functions**:
```python
# Import from utils.py
from utils import set_json_path_value, get_json_path_value

# Read value
title = get_json_path_value(context, "$.msg1_title")

# Set value  
set_json_path_value(context, "$.msg2_outline", ["intro", "body", "conclusion"])
```

---

## 6. Document Storage & Indexing

### 6.1 Storage Architecture

**File System Layout**:
```
sop_docs/
├── tools/                    # Tool-related SOPs
│   ├── llm.md               # LLM tool documentation
│   ├── bash.md              # CLI tool documentation  
│   └── user_communicate.md  # User interaction tool docs
├── general/                 # Generic SOPs
│   └── fallback.md          # Default fallback document
├── blog/                    # Domain-specific SOPs
│   ├── generate_outline.md  # Blog outline generation
│   └── write_paragraph.md   # Paragraph writing
└── examples/                # Templates and examples
```

**Document Naming Conventions**:
- Use doc_id as file path: `{doc_id}.md`
- Support multi-level directory structure: `blog/generate_outline.md`
- Use lowercase letters and underscores

### 6.2 SOP Document Parsing

**SOPDocumentLoader Class**:
```python
class SOPDocumentLoader:
    def __init__(self, docs_dir: str = "sop_docs")
    def load_sop_document(self, doc_id: str) -> SOPDocument
```

**Parsing Pipeline**:
1. Locate file path based on doc_id
2. Separate YAML front matter from markdown body
3. Parse YAML metadata
4. Extract markdown sections as parameters
5. Replace tool parameter section references

### 6.3 Intelligent SOP Matching

**SOPDocumentParser Class**:
- Parse appropriate SOP document ID from natural language task descriptions
- Combine semantic search with LLM validation
- Support alias matching and fuzzy matching

**Matching Strategy**:
1. **Filename Matching**: Direct matching based on doc_id paths
2. **Alias Matching**: Use aliases field defined in SOP documents
3. **Semantic Matching**: Use LLM to judge task description relevance to documents
4. **Fallback Strategy**: Use `general/fallback` when no match found

**Matching Pipeline**:
```python
async def parse_sop_doc_id_from_description(description: str) -> str:
    # 1. Find candidate documents (based on filenames and aliases)
    # 2. LLM validation and selection of best match
    # 3. Return selected doc_id or None
```

### 6.4 Semantic Search Integration

**Search Strategy**:
- Text matching based on document descriptions and aliases
- Consider keywords and tool references in task descriptions
- Support mixed Chinese-English matching

**LLM Validation Mechanism**:
- Use LLM for final candidate document selection
- Provide document descriptions and alias information for LLM reference
- Return XML format selection results: `<doc_id>selected_id</doc_id>`

**Performance Optimizations**:
- Document loading cache mechanism
- Avoid re-parsing already loaded documents
- Error handling and fault tolerance

---

## 7. Execution Engine Design

### 7.1 Core Execution Engine (DocExecuteEngine)

**Main Loop Design**:
1. Pop task description from task stack (LIFO)
2. **SOP Resolution Phase (create_task_from_description)**:
   - Parse natural language task description → SOP document ID
   - Load corresponding SOP document
   - Create complete Task object

3. **Task Execution Phase (execute_task)**:
   - Input parsing: Extract input values from context
   - Tool invocation: Execute specified tool and get output
   - Output path generation: Dynamically generate JSON paths with execution counter prefix
   - Context update: Store output in context

4. **New Task Generation Phase**:
   - Use LLM to parse tool output, extract new task descriptions
   - Add new tasks to task stack

### 7.2 Intelligent Input Path Generation (JsonPathGenerator)

**Biomimetic Four-Step Processing**:

**Step 1: Candidate Analysis**
- Intelligently scan context for semantically relevant fields
- Similar to humans searching for related tags on scratch paper
- Generate candidate field mapping with current values

**Step 2: Code Generation**
- LLM generates Python extraction functions based on candidate fields
- Support direct extraction, format conversion, content synthesis strategies
- Each step provides opportunity for input reformatting

**Step 3: Content Extraction**
- Execute generated code and obtain actual input values
- Trigger TaskInputMissingError and auto-recovery on failure
- Write results back to "scratch paper" awaiting use

**Step 4: Path Mapping**
- Generate temporary keys to store extracted content
- Create JSON paths pointing to temporary keys
- Don't persist metadata (like "where input came from")

**Output Path Generation**:
- Based on output descriptions and tool output content
- Dynamically generate semantic JSON paths
- Add execution counter prefixes to avoid conflicts

### 7.3 Execution State Tracking (Tracing System)

**Phase-Level Tracking**:
- **SOP Resolution Phase**: Document matching, LLM validation
- **Task Creation Phase**: Input path generation, task construction
- **Task Execution Phase**: Tool invocation, output generation
- **Context Update Phase**: State changes, cleanup operations
- **New Task Generation Phase**: Task discovery, stack management

**Observability Features**:
- Complete LLM call records (prompts, responses, step identifiers)
- Engine state snapshots (task stack, context, execution count)
- Error handling and retry tracking
- JSON file persistent storage

### 7.4 Intelligent Error Handling & Recovery

**Missing Input Handling (TaskInputMissingError)**:
- Auto-detect missing required inputs
- Generate recovery tasks to obtain missing information
- Support retry mechanism (maximum 3 attempts)
- Graceful fallback to fallback SOP

**Recovery Strategies**:
- User interaction: Use user_communicate tool for inquiries
- LLM generation: Use llm tool to generate missing content
- CLI execution: Use bash tool to get system information

### 7.5 Tool System Architecture

**Base Tool Class (BaseTool)**:
- Unified asynchronous execution interface
- Parameter validation mechanisms
- Error handling specifications

**Built-in Tools**:
- **LLM Tool**: Support template rendering, step identification
- **CLI Tool**: Execute bash commands, return stdout/stderr
- **User Interaction Tool**: Bidirectional communication, confirmation mechanisms

**Tool Wrappers (TracingToolWrapper)**:
- Transparent tracing integration
- Tool invocation monitoring
- Performance data collection

### 7.6 Context Management Strategy

**JSON Path Prefix System**:
- Add `msg{counter}_` prefix for each execution
- Prevent output conflicts and data overwrites
- Support complex nested paths

**Temporary Data Management**:
- Use `_temp_input_` prefix to store intermediate results
- Auto-cleanup temporary data after execution
- Reduce context pollution

**Persistence Mechanism**:
- Auto-save to context.json file
- Support checkpoint resume and state recovery
- JSON format convenient for debugging and inspection

---

## 8. Tool Integration Framework

### 8.1 Tool Architecture

**Base Tool Class Design**:
```python
class BaseTool(abc.ABC):
    def __init__(self, tool_id: str)
    async def execute(self, parameters: Dict[str, Any]) -> str
    def validate_parameters(self, parameters: Dict[str, Any], required_params: list)
```

**Tool Registration & Management**:
- Dynamic registration via `DocExecuteEngine.register_tool()`
- Support tool wrapper patterns (like TracingToolWrapper)
- Automatic parameter validation and error handling

### 8.2 Built-in Tool Specifications

**LLM Tool**:
```python
tool_id: "LLM"
Parameters:
  - prompt: str           # Prompt text with variable substitution
  - step: str (optional)  # Step identifier for tracing
  - model: str (optional) # Specify model
Output: Text response
```

**CLI Tool**:
```python
tool_id: "CLI"  
Parameters:
  - command: str          # bash command or script
Output: JSON format {"stdout": "...", "stderr": "..."}
```

**User Communication Tool**:
```python
tool_id: "USER_COMMUNICATE"
Parameters:
  - message: str          # Message to send to user
Output: User response content
```

### 8.3 Tool Parameter Processing

**Variable Substitution Mechanism**:
- Use `{variable}` syntax for template substitution
- Support values parsed from input_json_path
- Support templates defined in SOP document parameters sections

**Parameter Template Example**:
```yaml
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.system_prompt}"
```

Corresponding markdown parameter section:
```markdown
## parameters.system_prompt
Please complete the following task: {current_task}

Based on the following background information: {context}
```

### 8.4 Tracing Integration

**Tool Wrapper Pattern**:
- TracingToolWrapper: Generic tool tracing wrapper
- TracingLLMTool: Specialized LLM tool tracing

**Trace Information Collection**:
- Tool invocation time and duration
- Input parameters and output results
- Error messages and stack traces
- LLM-specific information (model, token usage, etc.)

**Observability Features**:
- Real-time tool execution status monitoring
- Performance analysis and bottleneck identification
- Error pattern analysis and diagnosis

---

## 9. Observability & Tracing

### 9.1 Execution Tracing Architecture

**Design Goals**:
- Complete recording of all key events in task execution process
- Support debugging, performance analysis, and execution replay
- Provide hierarchical data structures for analysis and visualization

**Core Components**:
```python
class ExecutionTracer:
    def start_session(initial_task: str) -> str       # Start session
    def start_task_execution(task_desc: str) -> str   # Start task execution
    def start_phase(phase_name: str)                  # Start execution phase
    def end_phase(data: Dict[str, Any])              # End execution phase
    def end_task_execution(status: ExecutionStatus)   # End task execution
    def end_session(status: ExecutionStatus) -> str   # End session and save
```

### 9.2 Hierarchical Data Structure

**Session Level (ExecutionSession)**:
```python
@dataclass
class ExecutionSession:
    session_id: str                    # Session unique identifier
    start_time: str                   # Session start time
    initial_task_description: str     # Initial task description
    engine_snapshots: Dict            # Engine state snapshots
    task_executions: List             # Task execution records
    final_status: ExecutionStatus     # Final status
```

**Task Execution Level (TaskExecution)**:
- Task description and execution counter
- Before/after engine state comparison
- Detailed execution data by phases
- Execution status and error information

**Phase-Level Tracking**:
- **SOP Resolution Phase**: Document matching, LLM validation calls
- **Task Creation Phase**: Input path generation, task object construction
- **Task Execution Phase**: Tool invocation, output path generation
- **Context Update Phase**: State changes, data cleanup
- **New Task Generation Phase**: Task discovery, stack management

### 9.3 LLM Call Specialized Tracking

**LLM Call Records (LLMCall)**:
```python
@dataclass
class LLMCall:
    tool_call_id: str           # Call unique identifier
    step: str                   # Step identifier (e.g., "sop_document_validation")
    prompt: str                 # Complete prompt text
    response: str               # LLM response content
    start_time: str            # Call start time
    end_time: str              # Call end time
    model: str                 # Model name used
    token_usage: Dict          # Token usage statistics
```

**Step Identifier Examples**:
- `sop_document_validation`: SOP document validation
- `json_path_analyze_context_candidates`: Context candidate analysis
- `json_path_generate_extraction_code`: Extraction code generation
- `json_path_output_generation`: Output path generation
- `new_task_generation`: New task generation

### 9.4 Tool Invocation Tracking

**TracingToolWrapper**:
- Transparent wrapper for existing tools, no tool implementation changes needed
- Record tool execution input parameters, output results, duration
- Capture and record exceptions during tool execution

**TracingLLMTool**:
- Specialized tracing wrapper for LLM tools
- Support step identifier passing and recording
- Enhanced prompt/response formatting display

### 9.5 State Snapshot System

**Engine State Snapshots**:
```python
def capture_engine_state(event: str, task_stack: List, context: Dict, counter: int):
    # Record complete engine state at key moments
    # Event types: start, end, error, task_boundary
```

**Context Change Tracking**:
- Complete context comparison before/after execution
- Record added, modified, deleted key-value pairs
- Track temporary data creation and cleanup processes

### 9.6 Data Persistence

**JSON File Storage**:
```
traces/
├── session_20250818_194221_a86db40f.json    # Complete session trace
├── session_20250818_194154_5ea09a58.json    # Another session
└── ...
```

**File Format Features**:
- Human-readable JSON format
- Nested structure supports drill-down analysis
- Contains complete timestamp information
- Supports string serialization of status enums

**Data Integrity**:
- Deep copy ensures state consistency
- Exception-safe data saving mechanism
- Support state recovery after interruption

### 9.7 Error Handling & Retry Tracking

**Error Status Records**:
- `ExecutionStatus.FAILED`: Execution failed
- `ExecutionStatus.RETRYING`: Retrying
- `ExecutionStatus.INTERRUPTED`: Interrupted

**Retry Mechanism Tracking**:
- Record retry attempt counts for each attempt
- Track recovery task generation and execution
- Complete preservation of failure causes and recovery processes

**Debug Information**:
- Complete exception stack traces
- Engine state snapshots at failure moments
- Recovery strategy decision process records

---

## 10. Implementation Examples

### 10.1 Real Execution Example: Beijing Time Query

**User Input**:
```
"Check current Beijing time using bash.md"
```

**Execution Flow Trace**:

**Phase 1: SOP Resolution**:
- Candidate documents: `tools/bash`
- LLM validation selection: `tools/bash`
- Load SOP document to get input_description

**Phase 2: Task Creation**:
- Detect missing input: `command` field
- Throw TaskInputMissingError
- Generate recovery task:
```
"Use llm.md, prompt is: 'What is the specific bash command to display Beijing time?'"
```

**Phase 3: Recovery Task Execution**:
- Execute LLM tool to generate bash command
- Output: `TZ=Asia/Shanghai date`
- Store in context temporary key

**Phase 4: Original Task Retry**:
- Extract command parameter from temporary key
- Execute CLI tool: `TZ=Asia/Shanghai date`
- Store output in `msg1_beijing_time_result`

**Final Context State**:
```json
{
  "current_task": "Check current Beijing time using bash.md",
  "msg1_command_for_beijing_time": "TZ=Asia/Shanghai date",
  "msg1_beijing_time_result": {
    "stdout": "Sun Aug 18 19:42:45 CST 2025\n",
    "stderr": ""
  }
}
```

### 10.2 Trace File Structure Example

```json
{
  "session_id": "a86db40f-7c73-493d-9670-a0033d2259e6",
  "start_time": "2025-08-18T11:42:21.740758Z",
  "initial_task_description": "Check current Beijing time using bash.md",
  "task_executions": [
    {
      "task_execution_counter": 0,
      "task_description": "Check current Beijing time using bash.md",
      "status": "retrying",
      "phases": {
        "sop_resolution": {
          "selected_doc_id": "tools/bash",
          "llm_validation_call": {
            "prompt": "Given the user's request...",
            "response": "<doc_id>tools/bash</doc_id>",
            "step": "sop_document_validation"
          }
        },
        "task_creation": {
          "error": "Missing input for field 'command': The bash command..."
        }
      }
    }
  ]
}
```

---

## 11. API Reference

### 11.1 Core Classes

#### DocExecuteEngine

**Constructor**:
```python
def __init__(self, docs_dir: str = "sop_docs", 
             context_file: str = "context.json",
             enable_tracing: bool = True, 
             trace_output_dir: str = "traces")
```

**Key Methods**:
```python
async def start(self, initial_task_description: str = None) -> None
def register_tool(self, tool: BaseTool) -> None
def load_context(self, load_if_exists: bool = True) -> Dict[str, Any]
def save_context() -> None
```

#### Task

**Data Structure**:
```python
@dataclass
class Task:
    task_id: str
    description: str
    sop_doc_id: str
    tool: Dict[str, Any]
    input_json_path: Dict[str, str]
    output_json_path: str
    output_description: str = None
```

#### JsonPathGenerator

**Key Methods**:
```python
async def generate_input_json_paths(
    self, 
    input_descriptions: Dict[str, str], 
    context: Dict[str, Any],
    user_original_ask: str = ""
) -> Dict[str, str]

async def generate_output_json_path(
    self, 
    output_description: str, 
    context: Dict[str, Any],
    user_original_ask: str = "",
    tool_output: Any = ""
) -> str
```

### 11.2 Tool Interface

#### BaseTool

**Abstract Interface**:
```python
class BaseTool(abc.ABC):
    def __init__(self, tool_id: str)
    
    @abc.abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> str
    
    def validate_parameters(self, parameters: Dict[str, Any], required_params: list) -> None
```

### 11.3 Utility Functions

#### Context Manipulation

```python
from utils import set_json_path_value, get_json_path_value

def set_json_path_value(data: Dict[str, Any], json_path: str, value: Any) -> None
def get_json_path_value(data: Dict[str, Any], json_path: str) -> Any
```

### 11.4 Exception Handling

#### Custom Exceptions

```python
class TaskInputMissingError(Exception):
    def __init__(self, field_name: str, description: str)

class TaskCreationError(Exception):
    def __init__(self, task_description: str, original_error: Exception, recovery_tasks: list = None)
```

---

## Appendix A: Performance Considerations

### A.1 Scalability Factors

- **Document Loading**: Cached to avoid repeated parsing
- **Context Size**: JsonPath operations scale with context complexity
- **LLM Calls**: Primary performance bottleneck; minimize unnecessary calls
- **Trace Storage**: JSON files can become large; consider rotation policies

### A.2 Optimization Strategies

- Implement document caching
- Use connection pooling for LLM API calls
- Consider context compression for large datasets
- Implement trace file rotation

---

## Appendix B: Security Considerations

### B.1 Code Execution Security

- JsonPathGenerator executes dynamically generated Python code
- Implement sandboxing for code execution
- Validate generated code before execution
- Consider using AST parsing for safer code generation

### B.2 Data Privacy

- Context may contain sensitive information
- Implement encryption for context files
- Consider data retention policies for trace files
- Sanitize sensitive data in logs

---

## Appendix C: Future Enhancements

### C.1 Planned Features

- **Visual Workflow Designer**: GUI for creating and editing SOP documents
- **Parallel Execution**: Support concurrent task execution
- **Plugin Architecture**: Third-party tool integration framework
- **Performance Dashboard**: Real-time execution monitoring
- **A/B Testing**: Compare different SOP document versions

### C.2 Research Directions

- **Learning from Traces**: Use execution history to improve path generation
- **Dynamic SOP Generation**: Auto-generate SOP documents from successful executions
- **Federated Execution**: Distributed task execution across multiple agents
- **Natural Language Programming**: Direct SOP creation from conversational input

---

**Document Version History**:
- v1.0 (2025-08-19): Initial comprehensive design specification
- Future versions will track implementation updates and feature additions

---

*This document represents the current state of the Doc Flow Agent architecture. For implementation details and code examples, please refer to the source code repository and inline documentation.*
