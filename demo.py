#!/usr/bin/env python3
"""
Simple demo script for Doc Flow Agent
Shows basic usage patterns
"""

import asyncio
import os
from dotenv import load_dotenv
from doc_execute_engine import DocExecuteEngine

# Load environment variables from .env file
load_dotenv()

async def demo_time_check():
    """Demo: Check current time using bash"""
    print("=== Demo: Check Current Time ===")
    engine = DocExecuteEngine()
    await engine.start("Check current time using bash")
    print("Context after execution:", engine.context)
    print()

async def demo_llm_task():
    """Demo: Simple LLM task"""
    print("=== Demo: Generate a joke ===")
    engine = DocExecuteEngine()
    await engine.start("Generate a programming joke using LLM")
    print("Context after execution:", engine.context)
    print()

async def main():
    """Run all demos"""
    print("Doc Flow Agent - Demo Script")
    print("============================")
    
    # Check if API key is configured
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not found in environment variables")
        print("Please set your API key in .env file or environment")
        print()
    
    try:
        await demo_time_check()
        await demo_llm_task()
        print("Demos completed successfully!")
    except Exception as e:
        print(f"Demo failed: {e}")
        print("Make sure your API key is configured and you have internet access")

if __name__ == "__main__":
    asyncio.run(main())
