"""
FastAPI server for the visualization module.
Provides REST API endpoints for trace data and serves static frontend files.
"""

import json
import logging
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for real-time monitoring
active_connections: Dict[str, List[asyncio.Queue]] = {}
file_observer = None

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
        logger.info(f"Active connections: {list(active_connections.keys())}")
        logger.info(f"Number of connections for {trace_id}: {len(active_connections.get(trace_id, []))}")
        
        # Notify all active connections for this trace
        if trace_id in active_connections:
            import time
            message = {
                "event": "file_updated",
                "trace_id": trace_id,
                "timestamp": time.time()
            }
            logger.info(f"Sending SSE message to {len(active_connections[trace_id])} connections: {message}")
            
            # Add message to all queues for this trace
            for queue in active_connections[trace_id]:
                try:
                    # Use put_nowait which doesn't require an event loop
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for trace {trace_id}, dropping message")
                except Exception as e:
                    logger.error(f"Error adding message to queue: {e}")

# Create FastAPI app
app = FastAPI(
    title="Doc Flow Trace Viewer API",
    description="API for viewing and analyzing doc flow execution traces",
    version="1.0.0"
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

@app.get("/health")
async def health_check():
    """Health check endpoint to verify server is running."""
    return {"status": "ok", "message": "Doc Flow Trace Viewer API is running"}

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
    
    logger.info(f"Starting SSE stream for trace: {trace_id}")
    
    # Create a queue for this connection
    message_queue = asyncio.Queue(maxsize=100)
    
    # Add to active connections
    if trace_id not in active_connections:
        active_connections[trace_id] = []
    active_connections[trace_id].append(message_queue)
    logger.info(f"Added SSE connection for trace {trace_id}. Total connections: {len(active_connections[trace_id])}")
    logger.info(f"All active trace connections: {list(active_connections.keys())}")
    
    async def event_stream():
        """Generate SSE events for the client."""
        try:
            # Send initial connection confirmation
            yield f"data: {json.dumps({'event': 'connected', 'trace_id': trace_id})}\n\n"
            
            while True:
                try:
                    # Wait for message with timeout for heartbeat
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat message
                    import time
                    yield f"data: {json.dumps({'event': 'heartbeat', 'timestamp': time.time()})}\n\n"
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
            logger.info(f"SSE stream closed for trace: {trace_id}")
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

# Startup and shutdown events for file watcher
@app.on_event("startup")
async def startup_event():
    """Initialize file watcher on startup."""
    global file_observer
    
    # Check if we're in testing mode (don't start file watcher during tests)
    import os
    if os.getenv('TESTING') == 'true':
        logger.info("Testing mode detected, file watcher disabled")
        return
    
    if TRACES_DIR.exists():
        event_handler = TraceFileHandler()
        file_observer = Observer()
        file_observer.schedule(event_handler, str(TRACES_DIR), recursive=False)
        file_observer.start()
        logger.info(f"File watcher started for directory: {TRACES_DIR}")
    else:
        logger.warning(f"Traces directory {TRACES_DIR} does not exist, file watcher not started")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop file watcher on shutdown."""
    global file_observer
    
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
    
    # Clear all active connections
    active_connections.clear()
    logger.info("All SSE connections cleared")

# Add logging middleware for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# Serve static files (React frontend) - this should be last
if REACT_BUILD_DIR.exists() and (REACT_BUILD_DIR / "index.html").exists():
    # Mount static assets (CSS, JS, etc.)
    app.mount("/assets", StaticFiles(directory=REACT_BUILD_DIR / "assets"), name="assets")
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "viz_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
