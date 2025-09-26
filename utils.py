#!/usr/bin/env python3
"""Utility functions for doc_flow_agent

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

import re
from typing import Dict, Any, List, Union
from jsonpath_ng.ext import parse
from jsonpath_ng import jsonpath


def set_json_path_value(data: Dict[str, Any], json_path: str, value: Any) -> None:
    """
    Set a value in a dictionary using JSON path notation.
    
    This function can handle both simple paths ($.key) and nested paths ($.parent.child).
    If parent paths don't exist, they will be created as empty dictionaries.
    
    Args:
        data: The target dictionary to modify
        json_path: JSON path string (e.g., "$.key", "$.parent.child", "$.parent[0].child")
        value: The value to set at the specified path
        
    Examples:
        >>> data = {}
        >>> set_json_path_value(data, "$.title", "My Title")
        >>> print(data)  # {"title": "My Title"}
        
        >>> set_json_path_value(data, "$.blog.outline", ["point1", "point2"])
        >>> print(data)  # {"title": "My Title", "blog": {"outline": ["point1", "point2"]}}
    """
    
    # Handle simple case: $.key
    if json_path.startswith('$.') and '.' not in json_path[2:] and '[' not in json_path:
        key = json_path[2:]
        data[key] = value
        return
    
    # Parse the JSON path
    try:
        jsonpath_expr = parse(json_path)
    except Exception as e:
        raise ValueError(f"Invalid JSON path '{json_path}': {e}")
    
    # For more complex paths, we need to ensure parent paths exist
    _ensure_path_exists(data, json_path)
    
    # Now set the value using jsonpath
    # We'll use a more direct approach for setting values
    _set_value_by_path(data, json_path, value)


def _ensure_path_exists(data: Dict[str, Any], json_path: str) -> None:
    """
    Ensure all parent paths exist in the data dictionary.
    Creates empty dictionaries for missing parent paths.
    """
    # Parse path components - handle $.parent.child.key format
    if not json_path.startswith('$.'):
        raise ValueError(f"JSON path must start with '$.' but got: {json_path}")
    
    # Remove the initial '$.' and split by '.'
    path_without_root = json_path[2:]
    
    # Handle array indices and complex paths
    # For now, focus on simple dot notation paths
    if '[' in path_without_root:
        # Complex path with array indices - handle separately
        path_without_root = re.match(r"\[\'(.*)\'\]", path_without_root).groups()[0]
    
    # Simple dot notation path
    path_parts = path_without_root.split('.')
    
    # Navigate/create the path up to the parent
    current = data
    for part in path_parts[:-1]:  # All parts except the last one
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            # If the intermediate path exists but is not a dict, we can't continue
            raise ValueError(f"Cannot set nested path: intermediate key '{part}' is not a dictionary")
        current = current[part]


def _set_value_by_path(data: Dict[str, Any], json_path: str, value: Any) -> None:
    """
    Set the value at the specified JSON path.
    Assumes the path already exists (created by _ensure_path_exists).
    """
    # For simple paths, use direct dictionary access
    if not json_path.startswith('$.'):
        raise ValueError(f"JSON path must start with '$.' but got: {json_path}")
    
    path_without_root = json_path[2:]

    if path_without_root.startswith('['):
        path_without_root = re.match(r"\[\'(.*)\'\]", path_without_root).groups()[0]
    
    # Handle simple dot notation
    path_parts = path_without_root.split('.')
    current = data
    
    # Navigate to the parent
    for part in path_parts[:-1]:
        current = current[part]
    
    # Set the final value
    final_key = path_parts[-1]
    current[final_key] = value

def get_json_path_value(data: Dict[str, Any], json_path: str) -> Any:
    """
    Get a value from a dictionary using JSON path notation.
    
    Args:
        data: The source dictionary
        json_path: JSON path string (e.g., "$.key", "$.parent.child")
        
    Returns:
        The value at the specified path, or None if not found
        
    Examples:
        >>> data = {"title": "My Title", "blog": {"outline": ["point1", "point2"]}}
        >>> get_json_path_value(data, "$.title")
        "My Title"
        >>> get_json_path_value(data, "$.blog.outline")
        ["point1", "point2"]
    """
    # Handle simple case: $.key
    if json_path.startswith('$.') and '.' not in json_path[2:] and '[' not in json_path:
        key = json_path[2:]
        return data.get(key)
    
    # Use jsonpath for complex cases
    try:
        jsonpath_expr = parse(json_path)
        matches = jsonpath_expr.find(data)
        if matches:
            return matches[0].value
        return None
    except Exception:
        return None


def extract_key_from_json_path(json_path: str) -> str:
    """
    Extract the top-level key from a JSON path.
    
    Args:
        json_path: JSON path string (e.g., "$.key", "$.parent.child", "$.['key']")
        
    Returns:
        The top-level key extracted from the JSON path
        
    Examples:
        >>> extract_key_from_json_path("$.title")
        "title"
        >>> extract_key_from_json_path("$.blog.outline")  
        "blog"
        >>> extract_key_from_json_path("$.['complex_key']")
        "complex_key"
        >>> extract_key_from_json_path("$.key[0].subkey")
        "key"
    """
    if not json_path or not json_path.startswith('$.'):
        return json_path
    
    # Remove the '$.' prefix
    path_part = json_path[2:]
    
    # Handle bracket notation: $.['key'] or $."key"
    if path_part.startswith('['):
        # Match patterns like ['key'] or ["key"]
        bracket_match = re.match(r'\[[\'"](.*?)[\'"]\]', path_part)
        if bracket_match:
            return bracket_match.group(1)
    
    # Handle dot notation and array indices: $.key, $.key[0], $.key.subkey
    # Split on '.' and '[' to get the first component
    first_component = re.split(r'[.\[]', path_part)[0]
    return first_component


# Test function to verify the implementation
def test_set_json_path_value():
    """Test the set_json_path_value function"""
    print("Testing set_json_path_value function...")
    
    # Test 1: Simple path
    data1 = {}
    set_json_path_value(data1, "$.title", "My Blog Title")
    assert data1 == {"title": "My Blog Title"}, f"Test 1 failed: {data1}"
    print("✓ Test 1 passed: Simple path")
    
    # Test 2: Nested path (parent doesn't exist)
    data2 = {}
    set_json_path_value(data2, "$.blog.title", "Nested Title")
    expected2 = {"blog": {"title": "Nested Title"}}
    assert data2 == expected2, f"Test 2 failed: {data2}"
    print("✓ Test 2 passed: Nested path creation")
    
    # Test 3: Nested path (parent exists)
    data3 = {"blog": {"author": "John"}}
    set_json_path_value(data3, "$.blog.title", "Another Title")
    expected3 = {"blog": {"author": "John", "title": "Another Title"}}
    assert data3 == expected3, f"Test 3 failed: {data3}"
    print("✓ Test 3 passed: Nested path with existing parent")
    
    # Test 4: Deep nested path
    data4 = {}
    set_json_path_value(data4, "$.blog.meta.tags", ["python", "json"])
    expected4 = {"blog": {"meta": {"tags": ["python", "json"]}}}
    assert data4 == expected4, f"Test 4 failed: {data4}"
    print("✓ Test 4 passed: Deep nested path")
    
    # Test 5: Overwriting existing value
    data5 = {"title": "Old Title"}
    set_json_path_value(data5, "$.title", "New Title")
    expected5 = {"title": "New Title"}
    assert data5 == expected5, f"Test 5 failed: {data5}"
    print("✓ Test 5 passed: Overwriting existing value")
    
    print("All set_json_path_value tests passed! ✓")


def test_extract_key_from_json_path():
    """Test the extract_key_from_json_path function"""
    print("Testing extract_key_from_json_path function...")
    
    # Test 1: Simple path
    assert extract_key_from_json_path("$.title") == "title"
    print("✓ Test 1 passed: Simple path")
    
    # Test 2: Nested path
    assert extract_key_from_json_path("$.blog.outline") == "blog"
    print("✓ Test 2 passed: Nested path")
    
    # Test 3: Bracket notation with single quotes
    assert extract_key_from_json_path("$.['complex_key']") == "complex_key"
    print("✓ Test 3 passed: Bracket notation with single quotes")
    
    # Test 4: Bracket notation with double quotes
    assert extract_key_from_json_path('$.["another_key"]') == "another_key"
    print("✓ Test 4 passed: Bracket notation with double quotes")
    
    # Test 5: Array index
    assert extract_key_from_json_path("$.items[0]") == "items"
    print("✓ Test 5 passed: Array index")
    
    # Test 6: Complex nested with array
    assert extract_key_from_json_path("$.data[0].nested.field") == "data"
    print("✓ Test 6 passed: Complex nested with array")
    
    # Test 7: Edge case - empty or invalid paths
    assert extract_key_from_json_path("") == ""
    assert extract_key_from_json_path("invalid") == "invalid"
    print("✓ Test 7 passed: Edge cases")
    
    print("All extract_key_from_json_path tests passed! ✓")


if __name__ == "__main__":
    test_set_json_path_value()
    test_extract_key_from_json_path()
