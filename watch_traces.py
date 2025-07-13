#!/usr/bin/env python3
"""
Simple file watcher for trace files
Usage: python watch_traces.py [traces_directory]
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

def watch_traces(traces_dir: str = "traces"):
    """Watch trace files for updates and show progress"""
    traces_path = Path(traces_dir)
    
    if not traces_path.exists():
        print(f"Traces directory '{traces_dir}' does not exist. Creating it...")
        traces_path.mkdir(exist_ok=True)
        return
    
    print(f"Watching trace files in: {traces_path.absolute()}")
    print("Press Ctrl+C to stop monitoring\n")
    
    last_seen_files = set()
    file_mtimes = {}
    
    try:
        while True:
            current_files = set(traces_path.glob("*.json"))
            
            # Check for new files
            new_files = current_files - last_seen_files
            for new_file in new_files:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] 🆕 New session started: {new_file.name}")
                file_mtimes[new_file] = new_file.stat().st_mtime
                show_session_progress(new_file)
            
            # Check for file updates
            for file_path in current_files:
                current_mtime = file_path.stat().st_mtime
                last_mtime = file_mtimes.get(file_path, 0)
                
                if current_mtime > last_mtime:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    if file_path in last_seen_files:  # Only show update if not a new file
                        print(f"[{timestamp}] 🔄 Session updated: {file_path.name}")
                    file_mtimes[file_path] = current_mtime
                    show_session_progress(file_path)
            
            last_seen_files = current_files.copy()
            time.sleep(1)  # Check every second
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped.")

def show_session_progress(file_path: Path):
    """Show progress information from a session file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        session_id = session_data.get("session_id", "unknown")[:8]
        initial_task = session_data.get("initial_task_description", "No initial task")
        final_status = session_data.get("final_status", "running")
        task_executions = session_data.get("task_executions", [])
        
        print(f"    Session: {session_id}")
        print(f"    Initial Task: {initial_task[:60]}{'...' if len(initial_task) > 60 else ''}")
        print(f"    Status: {final_status} | Tasks: {len(task_executions)}")
        
        if task_executions:
            latest_task = task_executions[-1]
            task_status = latest_task.get("status", "running")
            task_desc = latest_task.get("task_description", "Unknown task")
            phases = latest_task.get("phases", {})
            
            print(f"    Latest Task: {task_desc[:50]}{'...' if len(task_desc) > 50 else ''}")
            print(f"    Task Status: {task_status}")
            
            # Show phase progress
            phase_status = []
            for phase_name, phase_data in phases.items():
                phase_stat = phase_data.get("status", "running")
                if phase_stat == "completed":
                    phase_status.append(f"✅ {phase_name}")
                elif phase_stat == "failed":
                    phase_status.append(f"❌ {phase_name}")
                else:
                    phase_status.append(f"🔄 {phase_name}")
            
            if phase_status:
                print(f"    Phases: {' | '.join(phase_status)}")
        
        print()
        
    except (json.JSONDecodeError, KeyError, IOError) as e:
        print(f"    Error reading session file: {e}\n")

if __name__ == "__main__":
    traces_dir = sys.argv[1] if len(sys.argv) > 1 else "traces"
    watch_traces(traces_dir)
