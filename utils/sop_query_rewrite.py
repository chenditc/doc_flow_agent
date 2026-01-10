#!/usr/bin/env python3
"""Query rewrite helper for SOP vector search.

This module rewrites overly-specific user task descriptions into a short, generic
"SOP-like" query (usually 3–12 words) to improve vector-search recall when the
initial similarity score is low.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional


DEFAULT_REWRITE_THRESHOLD = 0.5

_MODE_ENV = "SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE"
_THRESHOLD_ENV = "SOP_VECTOR_SEARCH_QUERY_REWRITE_THRESHOLD"

# Optional in-process cache for deterministic repeated calls within a process.
_rewrite_cache: Dict[str, Optional[str]] = {}
_MAX_CACHE_SIZE = 512


def get_rewrite_threshold() -> float:
    """Return rewrite threshold from env (default 0.5).

    Env: SOP_VECTOR_SEARCH_QUERY_REWRITE_THRESHOLD
    """
    raw = (os.getenv(_THRESHOLD_ENV, "") or "").strip()
    if not raw:
        return DEFAULT_REWRITE_THRESHOLD
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_REWRITE_THRESHOLD
    # Clamp to a sensible range.
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def rewrite_enabled() -> str:
    """Return rewrite mode: 'off' | 'auto' | 'always' (default 'auto')."""
    mode = (os.getenv(_MODE_ENV, "auto") or "auto").strip().lower()
    if mode not in {"off", "auto", "always"}:
        return "auto"
    return mode


def _sanitize_rewritten_query(original: str, rewritten: str, *, max_len: int = 120) -> Optional[str]:
    original_clean = re.sub(r"\s+", " ", (original or "").strip())
    rewritten_clean = re.sub(r"\s+", " ", (rewritten or "").strip())
    if not rewritten_clean:
        return None
    if len(rewritten_clean) > max_len:
        rewritten_clean = rewritten_clean[:max_len].rstrip()
    if not rewritten_clean:
        return None
    if rewritten_clean == original_clean:
        return None
    return rewritten_clean


async def rewrite_for_sop_vector_search(description: str, llm_tool: Any) -> Optional[str]:
    """Rewrite description into a generic SOP vector-search query.

    Uses a structured tool schema to force a single JSON argument:
      rewrite_sop_vector_query(query: string)

    Returns:
      Sanitized rewritten query or None (if rewrite was empty/invalid/identical).
    """
    if description is None:
        return None
    description = str(description)

    cached = _rewrite_cache.get(description)
    if cached is not None:
        return cached

    tool_schema = {
        "type": "function",
        "function": {
            "name": "rewrite_sop_vector_query",
            "description": "Rewrite a task description into a short, generic SOP-style vector search query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A short, generic query (3–12 words if possible) capturing the core action + tool type.",
                    }
                },
                "required": ["query"],
            },
        },
    }

    prompt = f"""Rewrite the following task description into a short, generic SOP-style vector search query.

Rules:
- Output 5–12 words if possible.
- Remove URLs, names, IDs, exact numbers, and other unique entities.
- Keep the core action and (if applicable) the tool type: browser / python / cli / user communication.
- Do NOT include quotes or extra commentary.
- Use the rewrite_sop_vector_query tool to return the rewritten query.

Task description:
{description}
"""

    response = await llm_tool.execute(
        {
            "prompt": prompt,
            "model": llm_tool.small_model,
            "tools": [tool_schema],
        }
    )

    tool_calls = (response or {}).get("tool_calls", []) or []
    rewritten_raw = ""
    if tool_calls:
        first = tool_calls[0] or {}
        args = first.get("arguments") or {}
        if isinstance(args, dict):
            rewritten_raw = args.get("query", "") or ""

    rewritten = _sanitize_rewritten_query(description, rewritten_raw)

    # Simple bounded cache
    if len(_rewrite_cache) >= _MAX_CACHE_SIZE:
        _rewrite_cache.clear()
    _rewrite_cache[description] = rewritten

    return rewritten

