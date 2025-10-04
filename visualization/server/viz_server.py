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
active_connections: Dict[str, List[asyncio.Queue]] = {}
file_observer = None
# Capture the main asyncio event loop so watchdog thread can safely schedule work
main_event_loop: Optional[asyncio.AbstractEventLoop] = None
 
# Debounce control to avoid flooding the event loop with too many broadcasts
DEBOUNCE_SECONDS = 0.3
_pending_broadcast_handles: Dict[str, asyncio.TimerHandle] = {}

class TraceFileHandler(FileSystemEventHandler):
    """Handler for file system events on trace files."""
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        if not event.src_path.endswith('.json'):
            return
            
        # Extract trace ID from file path
        trace_id = Path(event.src_path).stem
        logger.info(f"Trace file modified: {trace_id}")

        # Notify connections using a debounced scheduler on the main event loop.
        # IMPORTANT: watchdog invokes this in a thread; only schedule work, do not touch asyncio objects.
        if main_event_loop is not None:
            try:
                main_event_loop.call_soon_threadsafe(_schedule_debounced_broadcast, trace_id)
            except Exception as e:
                logger.error(f"Failed to schedule debounced SSE broadcast on main loop: {e}")
        else:
            logger.warning("Main event loop not set; skipping SSE broadcast from watchdog thread")

def _schedule_debounced_broadcast(trace_id: str):
    """Debounce broadcasts for a trace: collapse rapid file change events.

    Must be called on the asyncio loop thread.
    """
    loop = asyncio.get_running_loop()
    # Cancel any existing pending broadcast
    handle = _pending_broadcast_handles.get(trace_id)
    if handle and not handle.cancelled():
        handle.cancel()
    # Schedule a new broadcast after DEBOUNCE_SECONDS
    new_handle = loop.call_later(DEBOUNCE_SECONDS, _broadcast_sse_message_in_loop, trace_id)
    _pending_broadcast_handles[trace_id] = new_handle

def _broadcast_sse_message_in_loop(trace_id: str):
    """Broadcast an SSE message to all connections for a trace within the asyncio loop thread."""
    # Clear pending handle if this is the scheduled run
    handle = _pending_broadcast_handles.pop(trace_id, None)
    if handle and not handle.cancelled():
        # nothing else needed; just ensure it's removed
        pass

    queues = active_connections.get(trace_id, [])
    if not queues:
        return
    import time
    message: Dict[str, Any] = {
        "event": "file_updated",
        "trace_id": trace_id,
        "timestamp": time.time(),
    }
    logger.info(f"Sending SSE message to {len(queues)} connections: {message}")
    for queue in list(queues):
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning(f"Queue full for trace {trace_id}, dropping message")
        except Exception as e:
            logger.error(f"Error adding message to queue in loop: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle events (startup and shutdown)."""
    global file_observer, main_event_loop
    
    # Startup
    # Check if we're in testing mode (don't start file watcher during tests)
    import os
    if os.getenv('TESTING') == 'true':
        logger.info("Testing mode detected, file watcher disabled")
    else:
        # Capture the running loop for cross-thread scheduling
        try:
            main_event_loop = asyncio.get_running_loop()
        except RuntimeError:
            main_event_loop = None
            logger.warning("Could not capture main event loop during startup")
        
        if TRACES_DIR.exists():
            event_handler = TraceFileHandler()
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
    
    # Cancel any pending debounced broadcasts
    for trace_id, handle in list(_pending_broadcast_handles.items()):
        try:
            if handle and not handle.cancelled():
                handle.cancel()
        except Exception:
            pass
    _pending_broadcast_handles.clear()

    # Clear all active connections
    active_connections.clear()
    logger.info("All SSE connections cleared")
    main_event_loop = None

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
        conn_summary: Dict[str, Any] = {}
        for tid, queues in active_connections.items():
            try:
                q_sizes = [q.qsize() for q in queues]
            except Exception:
                q_sizes = [None for _ in queues]
            conn_summary[tid] = {
                "connections": len(queues),
                "queue_sizes": q_sizes,
            }
        # Pending debounced broadcasts
        pending = list(_pending_broadcast_handles.keys())
        # File observer status
        observer_alive = bool(file_observer and file_observer.is_alive())
        # Loop info
        tasks = list(asyncio.all_tasks(loop))
        return {
            "active_traces": list(active_connections.keys()),
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

@app.get("/traces", response_model=List[str])
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

@app.get("/traces/latest")
async def get_latest_trace():
    """
    Get the latest trace ID based on filename timestamp.
    Returns the trace ID of the most recently created trace.
    """
    try:
        if not TRACES_DIR.exists():
            logger.warning(f"Traces directory {TRACES_DIR} does not exist")
            raise HTTPException(status_code=404, detail="No traces directory found")
        
        trace_files = list(TRACES_DIR.glob("*.json"))
        if not trace_files:
            raise HTTPException(status_code=404, detail="No trace files found")
        
        # Sort files by name (which includes timestamp) in descending order
        # Since files are named session_YYYYMMDD_HHMMSS_<hash>.json, 
        # sorting by name will sort by timestamp
        latest_file = max(trace_files, key=lambda f: f.name)
        latest_trace_id = latest_file.stem
        
        logger.info(f"Latest trace identified: {latest_trace_id}")
        return {"trace_id": latest_trace_id}
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error finding latest trace: {e}")
        raise HTTPException(status_code=500, detail=f"Error finding latest trace: {str(e)}")

@app.get("/traces/{trace_id}")
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

@app.get("/traces/{trace_id}/stream")
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
    
    # Create a queue for this connection
    message_queue = asyncio.Queue(maxsize=100)
    
    # Add to active connections
    if trace_id not in active_connections:
        active_connections[trace_id] = []
    active_connections[trace_id].append(message_queue)
    logger.info(f"[SSE] Added connection for trace {trace_id}. Total for this trace: {len(active_connections[trace_id])}. All traces with connections: {list(active_connections.keys())}")
    
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
            # Clean up connection
            if trace_id in active_connections and message_queue in active_connections[trace_id]:
                active_connections[trace_id].remove(message_queue)
                if not active_connections[trace_id]:
                    del active_connections[trace_id]
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
if REACT_BUILD_DIR.exists() and (REACT_BUILD_DIR / "index.html").exists():
    # Mount static assets (CSS, JS, etc.)
    app.mount("/assets", StaticFiles(directory=REACT_BUILD_DIR / "assets"), name="assets")
    
    # Serve user communication forms
    @app.get("/user-comm/{session_id}/{task_id}/")
    async def serve_user_comm(session_id: str, task_id: str):
        """Serve user communication form or confirmation page."""
        return await serve_user_comm_form(session_id, task_id)
    
    # Serve result delivery pages
    @app.get("/result-delivery/{session_id}/{task_id}/")
    async def serve_result_page(session_id: str, task_id: str):
        """Serve result delivery page."""
        return await serve_result_delivery_page(session_id, task_id)
    
    # Serve result delivery files
    @app.get("/result-delivery/{session_id}/{task_id}/files/{filename}")
    async def serve_result_file(session_id: str, task_id: str, filename: str):
        """Serve files from result delivery directory."""
        return await serve_result_delivery_file(session_id, task_id, filename)
    
    # Serve the LLM tuning HTML page
    @app.get("/llm-tuning")
    async def serve_llm_tuning():
        """Serve the LLM tool tuning page."""
        llm_tuning_path = PROJECT_ROOT / "visualization" / "llm_tuning.html"
        if llm_tuning_path.exists():
            return FileResponse(llm_tuning_path)
        else:
            raise HTTPException(status_code=404, detail="LLM tuning page not found")
    
    # Serve index.html at root and handle SPA routing
    @app.get("/")
    @app.get("/{path:path}")
    async def serve_react_app(path: str = None):
        """Serve the React SPA. All paths serve index.html for client-side routing."""
        # Serve API endpoints first (they won't reach here due to route precedence)
        # For all other paths, serve the React app
        index_path = REACT_BUILD_DIR / "index.html"
        return FileResponse(index_path)
    
    logger.info(f"React build directory found at {REACT_BUILD_DIR}")
else:
    logger.warning(f"No React build found at {REACT_BUILD_DIR}. Please run 'npm run build' in frontend-react/ to build the frontend.")
    
    # If no React build, serve a basic index page
    @app.get("/")
    async def serve_basic_index():
        """Serve basic index page when no React build is available."""
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
