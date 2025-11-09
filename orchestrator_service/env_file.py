"""Helpers for loading job-scoped environment variable files."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


def load_env_file(path: Optional[str]) -> None:
    """Load environment variables from a JSON file into os.environ."""
    if not path:
        return
    env_path = Path(path)
    try:
        content = env_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - treated as fatal
        raise RuntimeError(f"Environment file not found: {env_path}") from exc
    except OSError as exc:  # pragma: no cover - treated as fatal
        raise RuntimeError(f"Failed to read environment file {env_path}: {exc}") from exc
    if not content:
        data = {}
    else:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:  # pragma: no cover - treated as fatal
            raise RuntimeError(f"Environment file {env_path} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Environment file must contain a JSON object")
    os.environ.update({str(key): str(value) for key, value in data.items()})
