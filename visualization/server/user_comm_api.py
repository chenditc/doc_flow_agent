"""
User Communication API module for the visualization server.
Handles web-based user communication functionality.
"""

import json
import os
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

# Get project root for storage
PROJECT_ROOT = Path(__file__).parent.parent.parent
USER_COMM_DIR = PROJECT_ROOT / "user_comm" / "sessions"

# Pydantic models for request/response
class SubmitRequest(BaseModel):
    session_id: str = Field(..., description="Session identifier")
    task_id: str = Field(..., description="Task identifier")
    answer: str = Field(..., description="User's response text")

class SubmitResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    existing: bool = False

# Create router
router = APIRouter(prefix="/api/user-comm", tags=["user-communication"])

def sanitize_path_component(component: str) -> str:
    """Sanitize session_id or task_id to prevent path traversal attacks."""
    # Allow only alphanumeric, underscore, hyphen, and dot
    sanitized = re.sub(r'[^A-Za-z0-9._-]', '_', component)
    # Prevent directory traversal
    if '..' in sanitized or sanitized.startswith('.'):
        sanitized = sanitized.replace('..', '_').lstrip('.')
    return sanitized[:100]  # Limit length

def get_session_task_dir(session_id: str, task_id: str) -> Path:
    """Get the directory path for a session/task combination."""
    clean_session = sanitize_path_component(session_id)
    clean_task = sanitize_path_component(task_id)
    return USER_COMM_DIR / clean_session / clean_task

def atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """Write JSON data atomically using temp file + rename."""
    temp_path = file_path.with_suffix('.tmp')
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    temp_path.replace(file_path)

@router.post("/submit", response_model=SubmitResponse)
async def submit_response(request: SubmitRequest):
    """
    Submit user response for a session/task.
    Creates response.json and updates index.html with confirmation.
    """
    session_dir = get_session_task_dir(request.session_id, request.task_id)
    response_file = session_dir / "response.json"
    index_file = session_dir / "index.html"
    
    # Check if response already exists (idempotent)
    if response_file.exists():
        with open(response_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        logger.info(f"Response already exists for {request.session_id}/{request.task_id}")
        return SubmitResponse(
            success=True,
            message="Response already recorded",
            timestamp=existing_data.get('timestamp', ''),
            existing=True
        )
    
    # Create response data
    timestamp = datetime.now(timezone.utc).isoformat()
    response_data = {
        "session_id": request.session_id,
        "task_id": request.task_id,
        "answer": request.answer,
        "timestamp": timestamp,
        "received_at": timestamp
    }
    
    # Write response file atomically
    atomic_write_json(response_file, response_data)
    
    # Create confirmation HTML to replace index.html
    confirmation_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Response Received</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:300,400,500,700&display=swap">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
    <style>
        body {{
            font-family: 'Roboto', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 24px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .success-icon {{
            color: #4caf50;
            font-size: 48px;
            text-align: center;
            margin-bottom: 16px;
        }}
        .title {{
            font-size: 24px;
            font-weight: 500;
            color: #333;
            text-align: center;
            margin-bottom: 16px;
        }}
        .message {{
            color: #666;
            line-height: 1.5;
            margin-bottom: 24px;
        }}
        .response-box {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 16px;
            margin: 16px 0;
        }}
        .response-label {{
            font-weight: 500;
            color: #333;
            margin-bottom: 8px;
        }}
        .response-text {{
            color: #555;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .timestamp {{
            color: #999;
            font-size: 14px;
            text-align: center;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">
            <i class="material-icons" style="font-size: inherit;">check_circle</i>
        </div>
        <h1 class="title">Response Received</h1>
        <div class="message">
            Thank you! Your response has been successfully recorded and will be processed by the system.
        </div>
        <div class="response-box">
            <div class="response-label">Your Response:</div>
            <div class="response-text">{request.answer.replace('<', '&lt;').replace('>', '&gt;')}</div>
        </div>
        <div class="timestamp">
            Received at: {timestamp}
        </div>
    </div>
</body>
</html>"""
    
    # Write confirmation HTML atomically
    temp_index = index_file.with_suffix('.tmp')
    with open(temp_index, 'w', encoding='utf-8') as f:
        f.write(confirmation_html)
    temp_index.replace(index_file)
    
    logger.info(f"Response submitted for {request.session_id}/{request.task_id}")
    
    return SubmitResponse(
        success=True,
        message="Response recorded successfully",
        timestamp=timestamp,
        existing=False
    )

@router.get("/status/{session_id}/{task_id}")
async def get_status(session_id: str, task_id: str):
    """
    Get response status for a session/task.
    Returns whether a response has been submitted.
    """
    session_dir = get_session_task_dir(session_id, task_id)
    response_file = session_dir / "response.json"
    
    if response_file.exists():
        with open(response_file, 'r', encoding='utf-8') as f:
            response_data = json.load(f)
        return {
            "responded": True,
            "timestamp": response_data.get('timestamp'),
            "answer": response_data.get('answer')
        }
    else:
        return {"responded": False}

# This route is registered in viz_server.py as a catch-all after API routes
# to serve user communication forms
async def serve_user_comm_form(session_id: str, task_id: str) -> HTMLResponse:
    """
    Serve the user communication form or confirmation page.
    This function is called from viz_server.py routing.
    """
    session_dir = get_session_task_dir(session_id, task_id)
    index_file = session_dir / "index.html"
    
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Communication form not found")
    
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return HTMLResponse(content=content)