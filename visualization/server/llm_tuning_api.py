"""
LLM Tuning API module for the visualization server.
Handles LLM tool execution and tuning functionality.
"""

import sys
import os
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

# Load environment variables from the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path)

# Add the parent directory to the path to import tools
sys.path.append(PROJECT_ROOT)

from tools.llm_tool import LLMTool

logger = logging.getLogger(__name__)

# Log environment loading status
if os.path.exists(dotenv_path):
    logger.info(f"Loaded environment variables from {dotenv_path}")
else:
    logger.warning(f"No .env file found at {dotenv_path}")

# Pydantic models for request/response
class LLMExecuteRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to send to the LLM")
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="OpenAI function calling format tools")
    all_parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters for the LLM")

class LLMExecuteResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

# Create router
router = APIRouter(prefix="/api/llm-tuning", tags=["llm-tuning"])

@router.post("/execute", response_model=LLMExecuteResponse)
async def execute_llm_tool(request: LLMExecuteRequest):
    """
    Execute the LLM tool with the provided prompt and OpenAI function calling format tools.
    """
    try:
        import time
        start_time = time.time()
        
        # Create LLMTool instance
        llm_tool = LLMTool()
        
        # Prepare parameters for LLMTool.execute()
        # LLMTool.execute() expects a dictionary with prompt and tools
        execute_params = {
            "prompt": request.prompt
        }
        
        # Add tools if provided (OpenAI function calling format)
        if request.tools:
            execute_params["tools"] = request.tools
        
        # Add any additional parameters
        if request.all_parameters:
            execute_params.update(request.all_parameters)
        
        # Execute the LLM tool
        result = await llm_tool.execute(execute_params)
        
        execution_time = time.time() - start_time
        
        logger.info(f"LLM tool executed successfully in {execution_time:.2f}s")
        
        return LLMExecuteResponse(
            success=True,
            result=result,
            execution_time=execution_time
        )
        
    except Exception as e:
        logger.error(f"Error executing LLM tool: {str(e)}")
        return LLMExecuteResponse(
            success=False,
            error=str(e)
        )
