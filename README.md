# Doc Flow Agent

**Version:** 2.0  
**Last Updated:** December 2024  
**Authors:** Di Chen  
**License:** Apache License 2.0

> A document-driven AI agent framework that externalizes all business logic and domain knowledge into Standard Operating Procedure (SOP) documents.

## Overview

Doc Flow Agent is a production-ready AI agent system designed for complex, multi-step task automation. Unlike traditional hardcoded agent systems, this framework:

- **Externalizes Logic**: All task behavior is defined in markdown SOP documents
- **Provides Isolated Execution**: Jobs run in sandbox containers with full Python/shell access  
- **Offers Real-time Observability**: Comprehensive execution tracing with web-based visualization
- **Enables Human-in-the-Loop**: Built-in web forms for user communication during execution
- **Supports Multiple LLM Backends**: OpenAI, Azure, OpenRouter, local proxies

## Architecture

The system consists of four containerized services orchestrated via Docker Compose:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (nginx:80)                         │
│                   Exposed at localhost:28080                    │
│    Serves React SPA + Proxies /api/* to backend services        │
└─────────────┬───────────────────────────────────┬───────────────┘
              │                                   │
              ▼                                   ▼
┌─────────────────────────┐     ┌─────────────────────────────────┐
│   Orchestrator (:8001)  │     │     Visualization (:8000)       │
│                         │     │                                 │
│ • Job management API    │     │ • Trace viewer API              │
│ • Job submission        │     │ • SSE real-time streaming       │
│ • Status tracking       │     │ • SOP document management       │
│ • Log retrieval         │     │ • User communication forms      │
│ • Sandbox coordination  │     │ • LLM tuning interface          │
└───────────┬─────────────┘     └─────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Sandbox (:8080)                            │
│                                                                 │
│   Isolated execution environment for running agent tasks        │
│   • Full Python runtime with project dependencies               │
│   • Shell command execution                                     │
│   • File system access within /app                              │
│   • Exposed at localhost:8080 for debugging                     │
└─────────────────────────────────────────────────────────────────┘
```

### Service Responsibilities

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | 28080 (external) | nginx serving React SPA, proxies API requests |
| **Orchestrator** | 8001 (internal) | Job lifecycle management, spawns sandbox executions |
| **Visualization** | 8000 (internal) | Trace viewing, real-time updates, SOP docs management |
| **Sandbox** | 8080 (external) | Isolated job execution environment |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose (v2.x+)
- An LLM API key (OpenAI, Azure, or compatible)

### 1. Clone and Configure

```bash
git clone https://github.com/chenditc/doc_flow_agent.git
cd doc_flow_agent

# Create environment configuration
cp .env.example .env
# Edit .env with your API keys
```

### 2. Configure Your LLM Provider

Edit `.env` with one of these configurations:

**OpenAI:**
```bash
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

**Azure AI Foundry:**
```bash
OPENAI_API_BASE=https://<your-service>.cognitiveservices.azure.com/openai/v1/
OPENAI_API_KEY=dummy  # Uses Azure Identity
OPENAI_MODEL=gpt-4
```

**OpenRouter or Local Proxy:**
```bash
OPENAI_API_BASE=http://localhost:4141/v1/
OPENAI_API_KEY=your-key-or-dummy
OPENAI_MODEL=claude-sonnet-4
```

### 3. Start All Services

```bash
# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f
```

### 4. Access the UI

Open http://localhost:28080 in your browser. You'll see:
- **Jobs**: Submit and monitor job executions
- **Traces**: View detailed execution traces with task hierarchy
- **SOP Docs**: Browse and edit SOP documents

### 5. Submit Your First Job

Via the web UI or API:

```bash
curl -X POST http://localhost:28080/api/jobs \
  -H 'Content-Type: application/json' \
  -d '{"task_description": "Check current Beijing time using bash"}'
```

---

## Core Concepts

### Jobs

A **Job** represents a single execution request submitted to the system:

```json
{
  "job_id": "20241211-143025-abc12345",
  "task_description": "Write a blog post about AI",
  "status": "RUNNING",
  "max_tasks": 50,
  "trace_files": ["20241211-143025-abc12345.json"]
}
```

**Job Statuses:**
- `QUEUED` → `STARTING` → `RUNNING` → `COMPLETED` | `FAILED` | `CANCELLED`

### SOP Documents

**Standard Operating Procedure (SOP) documents** define how the agent performs tasks. They are markdown files with YAML frontmatter:

```markdown
---
description: Execute bash commands in sandbox environment
tool:
  tool_id: CLI
input_json_path:
  task_description: $.current_task
output_description: stdout and stderr from execution
skip_new_task_generation: true
---

Optional markdown body with additional instructions...
```

**Key Fields:**
- `description`: What this SOP does (used for matching)
- `tool.tool_id`: Which tool to invoke (LLM, CLI, PYTHON_EXECUTOR, etc.)
- `input_description` / `input_json_path`: How to find input data
- `output_description`: What the output represents

### Tools

Built-in tools available for SOP documents:

| Tool ID | Description |
|---------|-------------|
| `LLM` | Large language model inference for reasoning, writing, analysis |
| `CLI` | Execute bash commands and scripts |
| `PYTHON_EXECUTOR` | Run Python code with full project access |
| `WEB_USER_COMMUNICATE` | Generate web forms to collect user input |
| `WEB_RESULT_DELIVERY` | Deliver results to users via web pages |
| `TEMPLATE` | Simple string template rendering |

### Execution Flow

When a job is submitted:

1. **Job Created**: Orchestrator creates job metadata, assigns ID
2. **Sandbox Spawn**: Orchestrator starts `runner.py` in sandbox container
3. **Engine Execution**: `DocExecuteEngine` processes the task:
   - **SOP Resolution**: Match task description to SOP document
   - **Task Creation**: Generate input/output JSON paths
   - **Tool Execution**: Invoke the specified tool
   - **Context Update**: Store results in execution context
   - **New Task Generation**: Parse output for follow-up tasks
4. **Completion**: Results saved, trace file finalized

---

## API Reference

### Orchestrator API (`/api/*`)

**Job Management:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Submit new job |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/{job_id}` | Get job details |
| `POST` | `/api/jobs/{job_id}/cancel` | Cancel running job |
| `GET` | `/api/jobs/{job_id}/logs?tail=N` | Get job logs |
| `GET` | `/api/jobs/{job_id}/context` | Get execution context |
| `GET` | `/api/health` | Health check |

**Submit Job Request:**
```json
{
  "task_description": "Your task description",
  "max_tasks": 50,
  "env_vars": {"CUSTOM_VAR": "value"}
}
```

### Visualization API (`/api/traces/*`)

**Trace Management:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/traces` | List all trace IDs |
| `GET` | `/api/traces/latest` | Get latest trace ID |
| `GET` | `/api/traces/{trace_id}` | Get full trace JSON |
| `GET` | `/api/traces/{trace_id}/stream` | SSE real-time updates |

### SOP Docs API (`/api/sop-docs/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sop-docs/tree` | Get directory tree |
| `GET` | `/api/sop-docs/doc/{path}` | Get document details |
| `GET` | `/api/sop-docs/raw/{path}` | Get raw document content |
| `PUT` | `/api/sop-docs/doc/{path}` | Update document |
| `POST` | `/api/sop-docs/create?doc_path=...` | Create new document |
| `DELETE` | `/api/sop-docs/doc/{path}` | Delete document |
| `GET` | `/api/sop-docs/search?q=...` | Search documents |
| `POST` | `/api/sop-docs/validate` | Validate document |

---

## Project Structure

```
doc_flow_agent/
├── docker-compose.yml          # Service orchestration
├── Dockerfile.orchestrator     # Orchestrator service image
├── Dockerfile.visualization    # Visualization service image  
├── Dockerfile.frontend         # Frontend (nginx + React) image
├── Dockerfile.sandbox          # Sandbox execution environment
├── nginx.conf                  # Frontend proxy configuration
│
├── orchestrator_service/       # Job management service
│   ├── api.py                  # FastAPI endpoints
│   ├── manager.py              # ExecutionManager (job lifecycle)
│   ├── runner.py               # Job runner (invoked in sandbox)
│   ├── models.py               # Job data model
│   └── settings.py             # Configuration
│
├── visualization/
│   ├── server/
│   │   ├── viz_server.py       # FastAPI server
│   │   ├── trace_stream.py     # SSE streaming
│   │   ├── sop_doc_api.py      # SOP document management
│   │   ├── user_comm_api.py    # User communication
│   │   └── llm_tuning_api.py   # LLM tuning interface
│   └── frontend-react/         # React SPA
│       ├── src/
│       │   ├── components/     # UI components
│       │   ├── services/       # API clients
│       │   └── hooks/          # React hooks
│       └── package.json
│
├── doc_execute_engine.py       # Core execution engine
├── sop_document.py             # SOP document parsing
├── sop_doc_vector_store.py     # Vector search for SOPs
│
├── tools/                      # Built-in tools
│   ├── base_tool.py            # Abstract base class
│   ├── llm_tool.py             # LLM inference
│   ├── cli_tool.py             # Bash execution
│   ├── python_executor_tool.py # Python execution
│   ├── web_user_communicate_tool.py
│   ├── web_result_delivery_tool.py
│   └── json_path_generator.py  # Smart input/output mapping
│
├── sop_docs/                   # SOP document library
│   ├── tools/                  # Tool-specific SOPs
│   ├── general/                # Generic SOPs (fallback, plan)
│   └── examples/               # Example domain SOPs
│
├── tracing.py                  # Execution tracer
├── tracing_wrappers.py         # Tool tracing wrappers
├── utils/                      # Utility functions
└── requirements.txt            # Python dependencies
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | LLM API key | Required |
| `OPENAI_API_BASE` | LLM API endpoint | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Default model | `gpt-4` |
| `DEFAULT_SANDBOX_URL` | Sandbox URL (auto-set in compose) | `http://sandbox:8080` |
| `NOTIFICATION_CHANNEL` | Notification method | `stdout` |
| `WORK_WECHAT_WEBHOOK_URL` | WeChat webhook (if using) | - |

### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `traces` | Execution trace JSON files |
| `jobs` | Job metadata and context |
| `schedules` | Scheduled job specs and status |
| `log` | Application logs |
| `user_comm` | User communication sessions |
| `embedding_cache` | Vector embedding cache |

---

## Development

### Local Development Setup

```bash
# Use development compose override
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Frontend runs at localhost:5173 with hot reload
# Backend services have code mounted for live reload
```

### Running Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start orchestrator
uvicorn orchestrator_service.api:app --host 0.0.0.0 --port 8001

# Start visualization server  
uvicorn visualization.server.viz_server:app --host 0.0.0.0 --port 8000

# Start frontend (development)
cd visualization/frontend-react && npm install && npm run dev
```

### Running Tests

```bash
# Backend tests
pytest orchestrator_service/tests/
pytest visualization/tests/

# Frontend tests
cd visualization/frontend-react && npm test
```

---

## Writing Custom SOP Documents

### Basic Structure

Create a new file in `sop_docs/` with this structure:

```markdown
---
description: One-line description of what this SOP does
aliases:
  - alternative phrase 1
  - alternative phrase 2
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.main_prompt}"
input_description:
  topic: The main topic to work with
output_description: The generated content
---

## parameters.main_prompt

You are a helpful assistant. Please help with: {topic}

Provide a detailed response.
```

### Input Mapping Options

**Static Path:**
```yaml
input_json_path:
  topic: $.user_request
```

**Dynamic Generation (from description):**
```yaml
input_description:
  topic: The topic from user's original request
```

### Tool Configuration Examples

**LLM with custom prompt:**
```yaml
tool:
  tool_id: LLM
  parameters:
    prompt: "{parameters.analysis_prompt}"
    model: gpt-4o
```

**CLI command:**
```yaml
tool:
  tool_id: CLI
input_json_path:
  task_description: $.current_task
```

**Python execution:**
```yaml
tool:
  tool_id: PYTHON_EXECUTOR
input_description:
  task_description: The Python coding task to complete
```

---

## Troubleshooting

### Common Issues

**Job stuck in STARTING:**
- Check sandbox logs: `docker compose logs sandbox`
- Verify API credentials in `.env`

**No trace data:**
- Ensure trace volume is mounted
- Check visualization service logs

**LLM errors:**
- Verify `OPENAI_API_BASE` and `OPENAI_API_KEY`
- Check rate limits on your API account

### Debugging

```bash
# View all service logs
docker compose logs -f

# Check specific service
docker compose logs orchestrator -f

# Access sandbox shell
docker compose exec sandbox bash

# Check health endpoints
curl http://localhost:28080/health
curl http://localhost:8080/v1/sandbox
```

---

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) file.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
