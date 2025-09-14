#!/usr/bin/env python3
"""Custom exceptions for Doc Flow Agent

Copyright 2024-2025 Di Chen

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
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
