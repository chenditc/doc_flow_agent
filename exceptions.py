#!/usr/bin/env python3
"""
Custom exceptions for Doc Flow Agent
"""

class TaskInputMissingError(Exception):
    """Raised when required input for a task cannot be found in context"""
    
    def __init__(self, field_name: str, description: str):
        self.field_name = field_name
        self.description = description
        
        message = f"Missing input for field '{field_name}': {description}"
        super().__init__(message)


class TaskCreationError(Exception):
    """Raised when a task cannot be created due to various reasons"""
    
    def __init__(self, task_description: str, original_error: Exception, recovery_tasks: list = None):
        self.task_description = task_description
        self.original_error = original_error
        self.recovery_tasks = recovery_tasks or []
        
        message = f"Failed to create task '{task_description}': {original_error}"
        if recovery_tasks:
            message += f"\nSuggested recovery tasks: {recovery_tasks}"
            
        super().__init__(message)
