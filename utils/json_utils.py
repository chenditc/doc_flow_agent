#!/usr/bin/env python3
"""JSON path utility functions (moved from top-level utils.py)

Provides:
    set_json_path_value
    get_json_path_value
    extract_key_from_json_path
"""

import re
from typing import Dict, Any
from jsonpath_ng.ext import parse


def set_json_path_value(data: Dict[str, Any], json_path: str, value: Any) -> None:
    if json_path.startswith('$.') and '.' not in json_path[2:] and '[' not in json_path:
        key = json_path[2:]
        data[key] = value
        return
    try:
        parse(json_path)  # validate
    except Exception as e:
        raise ValueError(f"Invalid JSON path '{json_path}': {e}")
    _ensure_path_exists(data, json_path)
    _set_value_by_path(data, json_path, value)


def _ensure_path_exists(data: Dict[str, Any], json_path: str) -> None:
    if not json_path.startswith('$.'):
        raise ValueError(f"JSON path must start with '$.' but got: {json_path}")
    path_without_root = json_path[2:]
    if '[' in path_without_root:
        path_without_root = re.match(r"\[\'(.*)\'\]", path_without_root).groups()[0]
    path_parts = path_without_root.split('.')
    current = data
    for part in path_parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            raise ValueError(f"Cannot set nested path: intermediate key '{part}' is not a dictionary")
        current = current[part]


def _set_value_by_path(data: Dict[str, Any], json_path: str, value: Any) -> None:
    if not json_path.startswith('$.'):
        raise ValueError(f"JSON path must start with '$.' but got: {json_path}")
    path_without_root = json_path[2:]
    if path_without_root.startswith('['):
        path_without_root = re.match(r"\[\'(.*)\'\]", path_without_root).groups()[0]
    path_parts = path_without_root.split('.')
    current = data
    for part in path_parts[:-1]:
        current = current[part]
    current[path_parts[-1]] = value


def get_json_path_value(data: Dict[str, Any], json_path: str) -> Any:
    if json_path.startswith('$.') and '.' not in json_path[2:] and '[' not in json_path:
        return data.get(json_path[2:])
    try:
        expr = parse(json_path)
        matches = expr.find(data)
        return matches[0].value if matches else None
    except Exception:
        return None


def extract_key_from_json_path(json_path: str) -> str:
    if not json_path or not json_path.startswith('$.'):
        return json_path
    path_part = json_path[2:]
    if path_part.startswith('['):
        bracket_match = re.match(r'\[[\'\"](.*?)[\'\"]\]', path_part)
        if bracket_match:
            return bracket_match.group(1)
    return re.split(r'[.\[]', path_part)[0]


__all__ = [
    'set_json_path_value',
    'get_json_path_value',
    'extract_key_from_json_path'
]
