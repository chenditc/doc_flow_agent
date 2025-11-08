"""
FastAPI server for the visualization module.
Provides REST API endpoints for trace data and serves static frontend files.
"""

import json
import logging
import os
import asyncio
from contextlib import asynccontextmanager
import threading
import time
import signal
import traceback
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from visualization.server.trace_stream import TraceStreamManager

# Add path to import tools
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the LLM tuning API router
from visualization.server.llm_tuning_api import router as llm_tuning_router
# Import the user communication API router
from visualization.server.user_comm_api import (
    router as user_comm_router, 
    serve_user_comm_form,
    serve_result_delivery_page,
    serve_result_delivery_file
)
# Import the SOP docs API router
from visualization.server.sop_doc_api import router as sop_docs_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable faulthandler to dump stack traces on SIGUSR1
try:
    import faulthandler  # type: ignore
    try:
        faulthandler.register(signal.SIGUSR1)
        logger.info("Faulthandler registered on SIGUSR1 for thread dumps")
    except Exception:
        # Some platforms may not support SIGUSR1
        logger.warning("Faulthandler could not register SIGUSR1; thread dumps via endpoint only")
except Exception:
    logger.warning("Faulthandler not available; install or rely on /debug/threads endpoint")

# Global variables for real-time monitoring
file_observer = None

# Debounce control to avoid flooding the event loop with too many broadcasts
DEBOUNCE_SECONDS = 0.3

class TraceFileHandler(FileSystemEventHandler):
    """Handler for file system events on trace files."""

    def __init__(self, stream_manager: TraceStreamManager):
        super().__init__()
        self.stream_manager = stream_manager

    def on_modified(self, event):
        self._maybe_notify(event.src_path, event.is_directory)

    def on_created(self, event):
        self._maybe_notify(event.src_path, event.is_directory)

    def on_moved(self, event):
        if event.is_directory:
            return
        self._maybe_notify(event.dest_path, False)

    def _maybe_notify(self, path: str, is_dir: bool):
        if is_dir:
            return
        if not path.endswith('.json'):
            return
        trace_id = Path(path).stem
        logger.info(f"Trace file updated: {trace_id}")
        self.stream_manager.notify_file_modified(trace_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle events (startup and shutdown)."""
    global file_observer

    # Capture the running loop for cross-thread scheduling
    try:
        loop = asyncio.get_running_loop()
        trace_stream_manager.attach_loop(loop)
    except RuntimeError:
        trace_stream_manager.detach_loop()
        logger.warning("Could not capture main event loop during startup")
    
    # Startup
    if os.getenv('TESTING') == 'true':
        logger.info("Testing mode detected, file watcher disabled")
    else:
        if TRACES_DIR.exists():
            event_handler = TraceFileHandler(trace_stream_manager)
            file_observer = Observer()
            file_observer.schedule(event_handler, str(TRACES_DIR), recursive=False)
            file_observer.start()
            logger.info(f"File watcher started for directory: {TRACES_DIR}")
        else:
            logger.warning(f"Traces directory {TRACES_DIR} does not exist, file watcher not started")
    
    yield  # App runs here
    
    # Shutdown
    if file_observer:
        try:
            file_observer.stop()
            # Use a timeout to avoid hanging indefinitely
            file_observer.join(timeout=2.0)
            if file_observer.is_alive():
                logger.warning("File watcher did not stop within timeout")
            else:
                logger.info("File watcher stopped")
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")
        finally:
            file_observer = None
    
    await trace_stream_manager.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Doc Flow Trace Viewer API",
    description="API for viewing and analyzing doc flow execution traces",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        # Added 28080 mappings after external port change
        "http://localhost:28080",
        "http://127.0.0.1:28080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get paths relative to the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
TRACES_DIR = PROJECT_ROOT / "traces"
REACT_BUILD_DIR = PROJECT_ROOT / "visualization" / "frontend-react" / "dist"
_orch_base = os.getenv("ORCHESTRATOR_BASE_URL", "").strip()
ORCHESTRATOR_BASE_URL = _orch_base.rstrip("/") if _orch_base else ""
ORCHESTRATOR_SYNC_TIMEOUT = float(os.getenv("ORCHESTRATOR_SYNC_TIMEOUT", "10.0"))
TRACE_SYNC_POLL_INTERVAL = float(os.getenv("TRACE_SYNC_POLL_INTERVAL", "2.0"))

trace_stream_manager = TraceStreamManager(
    orchestrator_base_url=ORCHESTRATOR_BASE_URL,
    sync_timeout=ORCHESTRATOR_SYNC_TIMEOUT,
    poll_interval=TRACE_SYNC_POLL_INTERVAL,
    debounce_seconds=DEBOUNCE_SECONDS,
)

# Include the LLM tuning router
app.include_router(llm_tuning_router)
# Include the user communication router
app.include_router(user_comm_router)
# Include the SOP docs router
app.include_router(sop_docs_router)

@app.get("/health")
async def health_check():
    """Health check endpoint to verify server is running."""
    return {"status": "ok", "message": "Doc Flow Trace Viewer API is running"}

@app.get("/debug/state")
async def debug_state():
    """Return internal server state for debugging hangs/flows."""
    try:
        loop = asyncio.get_running_loop()
        # Summarize active connections and queue sizes
        conn_summary = trace_stream_manager.connection_debug_snapshot()
        pending = trace_stream_manager.pending_broadcast_traces()
        # File observer status
        observer_alive = bool(file_observer and file_observer.is_alive())
        # Loop info
        tasks = list(asyncio.all_tasks(loop))
        return {
            "active_traces": trace_stream_manager.active_trace_ids(),
            "connections": conn_summary,
            "pending_broadcasts": pending,
            "file_observer_alive": observer_alive,
            "loop_debug": getattr(loop, "get_debug", lambda: False)(),
            "tasks_count": len(tasks),
        }
    except Exception as e:
        logger.error(f"/debug/state error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/threads")
async def debug_threads():
    """Dump stacks of all threads to help inspect hangs."""
    frames = sys._current_frames()
    parts = []
    for thread_id, frame in frames.items():
        thread_name = None
        for t in threading.enumerate():
            if t.ident == thread_id:
                thread_name = t.name
                break
        header = f"\n--- Thread {thread_name or thread_id} ({thread_id}) ---\n"
        stack = ''.join(traceback.format_stack(frame))
        parts.append(header + stack)
    content = ''.join(parts)
    return FileResponse(path=None) if False else StreamingResponse(iter([content]), media_type="text/plain")

@app.get("/api/traces", response_model=List[str])
async def list_traces():
    """
    List all available trace files.
    Returns a list of trace IDs (filenames without .json extension).
    """
    try:
        if not TRACES_DIR.exists():
            logger.warning(f"Traces directory {TRACES_DIR} does not exist")
            return []
        
        trace_files = []
        for file_path in TRACES_DIR.glob("*.json"):
            # Return filename without .json extension as trace ID
            trace_id = file_path.stem
            trace_files.append(trace_id)
        
        logger.info(f"Found {len(trace_files)} trace files")
        return sorted(trace_files)
    
    except Exception as e:
        logger.error(f"Error listing traces: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing traces: {str(e)}")

@app.get("/api/traces/latest")
async def get_latest_trace():
    """
    Get the latest trace ID based on file modification time.
    Returns the trace ID of the most recently updated trace.
    """
    try:
        if not TRACES_DIR.exists():
            logger.warning(f"Traces directory {TRACES_DIR} does not exist")
            raise HTTPException(status_code=404, detail="No traces directory found")
        
        trace_files = list(TRACES_DIR.glob("*.json"))
        if not trace_files:
            raise HTTPException(status_code=404, detail="No trace files found")
        
        # Use modification time to identify the freshest trace. This works even when filenames
        # are not timestamped (e.g., when traces share the job_id as their name).
        latest_file = max(trace_files, key=lambda f: f.stat().st_mtime)
        latest_trace_id = latest_file.stem
        
        logger.info(f"Latest trace identified: {latest_trace_id}")
        return {"trace_id": latest_trace_id}
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error finding latest trace: {e}")
        raise HTTPException(status_code=500, detail=f"Error finding latest trace: {str(e)}")

@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str) -> Dict[str, Any]:
    """
    Get a specific trace by ID.
    Returns the parsed JSON content of the trace file.
    """
    # Validate trace_id to prevent path traversal attacks
    if ".." in trace_id or "/" in trace_id or "\\" in trace_id:
        raise HTTPException(status_code=400, detail="Invalid trace ID format")
    
    # Remove .json extension if present to avoid double extension
    if trace_id.endswith('.json'):
        trace_id = trace_id[:-5]
    
    await trace_stream_manager.request_sync_once(trace_id, force=True)

    # Construct file path
    trace_file = TRACES_DIR / f"{trace_id}.json"
    
    # Check if file exists
    if not trace_file.exists():
        logger.warning(f"Trace file not found: {trace_file}")
        raise HTTPException(status_code=404, detail=f"Trace '{trace_id}' not found")
    
    try:
        # Read and parse the JSON file
        with open(trace_file, 'r', encoding='utf-8') as f:
            trace_data = json.load(f)
        
        logger.info(f"Successfully loaded trace: {trace_id}")
        return trace_data
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in trace file {trace_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid JSON in trace file: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error reading trace file {trace_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading trace file: {str(e)}")

@app.get("/api/traces/{trace_id}/stream")
async def stream_trace_updates(trace_id: str):
    """
    Stream real-time updates for a specific trace using Server-Sent Events (SSE).
    """
    # Validate trace_id to prevent path traversal attacks
    if ".." in trace_id or "/" in trace_id or "\\" in trace_id:
        raise HTTPException(status_code=400, detail="Invalid trace ID format")
    
    # Remove .json extension if present
    if trace_id.endswith('.json'):
        trace_id = trace_id[:-5]
    
    logger.info(f"[SSE] Starting SSE stream handler for trace: {trace_id}")

    await trace_stream_manager.request_sync_once(trace_id, force=True)
    
    # Create a queue for this connection
    message_queue = trace_stream_manager.register_connection(trace_id)
    trace_stream_manager.ensure_sync_polling(trace_id)
    logger.info(
        "[SSE] Added connection for trace %s. Total for this trace: %d. Active traces: %s",
        trace_id,
        trace_stream_manager.connection_count(trace_id),
        trace_stream_manager.active_trace_ids(),
    )
    
    async def event_stream():
        """Generate SSE events for the client."""
        try:
            # Send initial connection confirmation
            init_msg = {'event': 'connected', 'trace_id': trace_id}
            logger.info(f"[SSE] Sending initial message: {init_msg}")
            yield f"data: {json.dumps(init_msg)}\n\n"
            
            while True:
                try:
                    # Wait for message with timeout for heartbeat
                    qsize_before = message_queue.qsize()
                    logger.debug(f"[SSE] Waiting for message (qsize={qsize_before}) for trace {trace_id}")
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                    logger.info(f"[SSE] Emitting message: {message}")
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat message
                    import time
                    hb = {'event': 'heartbeat', 'timestamp': time.time()}
                    logger.debug(f"[SSE] Heartbeat: {hb}")
                    yield f"data: {json.dumps(hb)}\n\n"
                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"SSE stream error for trace {trace_id}: {e}")
        finally:
            trace_stream_manager.unregister_connection(trace_id, message_queue)
            logger.info(f"[SSE] Stream closed for trace: {trace_id}")
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
            # Some environments need explicit no-transform and X-Accel-Buffering to keep the stream live
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
        }
    )

# ---------------- Legacy shim endpoints for backward compatibility (deprecated) ----------------
@app.get("/traces", include_in_schema=False)
async def legacy_list_traces():
    return await list_traces()

@app.get("/traces/latest", include_in_schema=False)
async def legacy_latest_trace():
    return await get_latest_trace()

@app.get("/traces/{trace_id}", include_in_schema=False)
async def legacy_get_trace(trace_id: str):
    return await get_trace(trace_id)

@app.get("/traces/{trace_id}/stream", include_in_schema=False)
async def legacy_stream_trace(trace_id: str):
    return await stream_trace_updates(trace_id)

# Add logging middleware for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    start = time.time()
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    dur_ms = int((time.time() - start) * 1000)
    logger.info(f"Response status: {response.status_code} ({dur_ms} ms)")
    return response

# Serve static files (React frontend) - this should be last
def _register_core_pages():
    """Register user communication and result delivery routes (always available for tests)."""
    # Serve user communication forms
    @app.get("/user-comm/{session_id}/{task_id}/")
    async def serve_user_comm(session_id: str, task_id: str):  # type: ignore
        return await serve_user_comm_form(session_id, task_id)

    # Serve result delivery pages
    @app.get("/result-delivery/{session_id}/{task_id}/")
    async def serve_result_page(session_id: str, task_id: str):  # type: ignore
        return await serve_result_delivery_page(session_id, task_id)

    # Serve result delivery files
    @app.get("/result-delivery/{session_id}/{task_id}/files/{filename}")
    async def serve_result_file(session_id: str, task_id: str, filename: str):  # type: ignore
        return await serve_result_delivery_file(session_id, task_id, filename)

_register_core_pages()

if REACT_BUILD_DIR.exists() and (REACT_BUILD_DIR / "index.html").exists():
    # Mount static assets (CSS, JS, etc.)
    app.mount("/assets", StaticFiles(directory=REACT_BUILD_DIR / "assets"), name="assets")

    # Serve the LLM tuning HTML page (only if build exists to avoid 404 noise)
    @app.get("/llm-tuning")
    async def serve_llm_tuning():  # type: ignore
        llm_tuning_path = PROJECT_ROOT / "visualization" / "llm_tuning.html"
        if llm_tuning_path.exists():
            return FileResponse(llm_tuning_path)
        raise HTTPException(status_code=404, detail="LLM tuning page not found")

    # Serve index.html at root and handle SPA routing
    @app.get("/")
    @app.get("/{path:path}")
    async def serve_react_app(path: str = None):  # type: ignore
        index_path = REACT_BUILD_DIR / "index.html"
        return FileResponse(index_path)

    logger.info(f"React build directory found at {REACT_BUILD_DIR}")
else:
    logger.warning(
        f"No React build found at {REACT_BUILD_DIR}. Frontend assets disabled; core API & HTML endpoints still available."  # noqa: E501
    )

    # Basic index when no React build present
    @app.get("/")
    async def serve_basic_index():  # type: ignore
        return {"message": "Doc Flow Visualization API", "llm_tuning": "/llm-tuning"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "viz_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
