# Doc Flow Visualization System

A comprehensive web-based visualization system for monitoring and analyzing doc flow execution traces in real-time.

## Architecture

- **Backend**: FastAPI server with REST API endpoints (`visualization/server/`)
- **Frontend**: React + TypeScript + Vite application (`visualization/frontend-react/`)
- **Data Source**: JSON trace files in `traces/` directory
- **Testing**: Backend and frontend test suites
- **Real-time Updates**: Server-sent events (SSE) for live trace monitoring

## Core Features

- **Job Orchestration**: Submit, monitor, cancel, and inspect execution jobs with linked trace files
- **SOP Document Management**: View, edit, search, and manage Standard Operating Procedure documents
- **Trace Visualization**: Real-time trace monitoring with hierarchical task display
- **LLM Tool Tuning**: Interactive LLM testing and debugging interface

## Component Architecture

The React frontend is organized into these main components:

- **App.tsx**: Main application with state management
# Frontend tests (single run, no watch)
cd visualization/frontend-react && npm test

# Frontend watch mode (optional for active development)
cd visualization/frontend-react && npm run test:watch
- **TraceSelector/**: Trace selection dropdown with real-time toggle
# Frontend coverage report
cd visualization/frontend-react && npm run coverage
- **SOPResolution/**: SOP document resolution visualization
- **LLMCall/**: LLM interaction details display

6. **Job Lifecycle**: Submit a job, observe status transitions (QUEUED → STARTING → RUNNING → COMPLETED/FAILED), inspect logs and generated trace links

### Job Orchestration Feature

The visualization site now includes a Jobs section accessible via the top navigation:

**Capabilities**
- Submit a new job with task description and optional `max_tasks`
- View all jobs with status filtering (Queued, Starting, Running, Completed, Failed, Cancelled)
- Auto-refresh active jobs and logs (polling, upgradeable to SSE/WebSocket later)
- Cancel an in-flight job
- Inspect job summary (timing, duration, params)
- Tail logs (select 100/500/1000 lines or full)
- View discovered trace files and jump directly into the Trace Viewer
- Inspect recorded execution context JSON (if produced)

**Routes**
- `/jobs` – Jobs list and submission dialog
- `/jobs/:jobId` – Detailed job view with tabs (Summary, Logs, Traces, Context)

**Frontend Components** (in `src/components/Jobs/`)
- `JobsListPage.tsx`
- `JobDetailPage.tsx`
- `JobSubmitForm.tsx`
- `JobStatusChip.tsx`

**Service Layer**
- `src/services/jobService.ts` wraps orchestrator FastAPI endpoints:
	- `POST /jobs`
	- `GET /jobs`
	- `GET /jobs/{job_id}`
	- `POST /jobs/{job_id}/cancel`
	- `GET /jobs/{job_id}/logs?tail=N`
	- `GET /jobs/{job_id}/context`

### SOP Document Management Feature

A comprehensive web-based UI for managing Standard Operating Procedure (SOP) documents. Access via the **SOP Docs** tab in the navigation.

**Key Features**
- **Directory Tree**: Hierarchical view with collapsible folders and search filtering
- **Document Search**: Fast search using ripgrep with context previews
- **Structured Editor**: Form-based YAML metadata editing with validation
- **Markdown Editor**: Body editing with preview and section management
- **Document Operations**: Create, copy, update, delete documents with atomic writes
- **URL Navigation**: Deep linking to documents (e.g., `/sop-docs/tools/bash`)

**API Endpoints** (`/api/sop-docs`)
- `GET /tree` – Directory structure
- `GET /doc/{path}` – Document details
- `GET /search?q={query}` – Search documents
- `POST /validate` – Validate without saving
- `POST /create` – Create new document
- `PUT /doc/{path}` – Update document
- `POST /copy` – Copy document
- `DELETE /doc/{path}` – Delete document

**Frontend Components** (in `src/components/SOPDocs/`)
- `SopDocsPage.tsx` – Main page layout
- `SopDocTree.tsx` – Directory tree
- `SearchBar.tsx` – Search with results
- `SopDocEditor.tsx` – Document editor
- `MetadataForm.tsx` – YAML metadata form
- `MarkdownEditor.tsx` – Markdown body editor

**Documentation**: See [SOP_DOCS_MANAGEMENT.md](./SOP_DOCS_MANAGEMENT.md) for detailed usage guide

### Testing Notes
- Default `npm test` now performs a one-shot run (`vitest --run`) and exits (CI-friendly)
- Use `npm run test:watch` for interactive watch mode

**Future Enhancements (Suggested)**
- SSE / WebSocket stream for status + incremental log lines
- Pagination / infinite scroll for large job history
- Persisted filters and column preferences
- Side-by-side embedded trace viewer inside Job Detail
## Quick Start

### Start Local Visualization Site

```bash
# From the project root directory
cd visualization/frontend-react && npm install && npm run build && cd .. && source ../.venv/bin/activate && uvicorn server.viz_server:app --reload --host 0.0.0.0 --port 8000
```

The visualization will be available at: http://localhost:8000

### Development Setup (Fresh Clone)

```bash
# 1. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Set up React frontend
cd visualization/frontend-react && npm install && npm run build && cd ..

# 3. Start production server
source ../.venv/bin/activate && uvicorn server.viz_server:app --reload --host 0.0.0.0 --port 8000
```

**For development with hot reload:**
```bash
# Terminal 1 - Backend server
cd visualization && source ../.venv/bin/activate && uvicorn server.viz_server:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend development server (in a new terminal)
cd visualization/frontend-react && npm run dev
```

- Production site: http://localhost:8000 (serves built React app)
- Development site: http://localhost:5173 (with hot reload)

## Testing

### What's Covered by Unit Tests

**Backend Tests** (`visualization/tests/`):
- API endpoints and data validation
- Real-time SSE streaming
- Trace file processing
- Error handling

**Frontend Tests** (`visualization/frontend-react/`):
- Component rendering and interactions
- Data fetching and state management
- User interface behavior

Run tests:
```bash
# Backend tests
cd visualization && source ../.venv/bin/activate && python -m pytest tests/

# Frontend tests  
cd visualization/frontend-react && npm test
```

### Manual Verification Required

1. **Real-time Updates**: Start monitoring, run a doc flow task, verify live updates
2. **Timeline Interactions**: Click tasks, check modal details, verify data display
3. **Trace Selection**: Switch between traces, verify data loads correctly
4. **Error Scenarios**: Test with missing/corrupted trace files
5. **Responsive Design**: Test on different screen sizes

### File Structure
```
visualization/
├── server/           # FastAPI backend
├── frontend-react/   # React frontend (current)
├── tests/            # Backend test suite
└── README.md         # This file
```

## Development Guide

### Project Structure

- **Backend (`server/`)**: FastAPI application serving REST API and static files
- **Frontend (`frontend-react/`)**: Modern React + TypeScript + Vite application
- **Data Flow**: JSON trace files → REST API → React components → Real-time updates via SSE

### Key Technologies

- **Backend**: FastAPI, Server-sent Events (SSE), File watching
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, React Query
- **Build System**: Vite for development/production builds
- **Testing**: pytest (backend), Vitest + React Testing Library (frontend)

### Development Workflow

1. **Backend changes**: Modify `server/viz_server.py`, restart with `uvicorn --reload`
2. **Frontend changes**: Modify React components, use `npm run dev` for hot reload
3. **Production build**: Run `npm run build` to generate optimized static files
4. **Testing**: Run backend/frontend tests separately as documented above

