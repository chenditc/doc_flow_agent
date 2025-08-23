# Doc Flow Visualization System

A comprehensive web-based visualization system for monitoring and analyzing doc flow execution traces in real-time.

## Architecture

- **Backend**: FastAPI server with REST API endpoints (`visualization/server/`)
- **Frontend**: React + TypeScript + Vite application (`visualization/frontend-react/`)
- **Data Source**: JSON trace files in `traces/` directory
- **Testing**: Backend and frontend test suites
- **Real-time Updates**: Server-sent events (SSE) for live trace monitoring

## Core Features

- **Real-time Trace Selection**: Auto-loads latest trace on page load with manual override
- **Interactive Timeline**: Linear timeline view of task executions with status indicators
- **Detailed Phase Analysis**: Click any task to see phase-by-phase execution breakdown
- **Live Monitoring**: Real-time updates with auto-scroll and visual indicators
- **Comprehensive Error Handling**: Graceful handling of missing data and edge cases

## Component Architecture

The React frontend is organized into these main components:

- **App.tsx**: Main application with state management
- **Timeline/**: Task execution timeline with visual status indicators
- **TaskDetails/**: Modal for detailed task information
- **TraceSelector/**: Trace selection dropdown with real-time toggle
- **SOPResolution/**: SOP document resolution visualization
- **LLMCall/**: LLM interaction details display

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

