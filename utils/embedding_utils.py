#!/usr/bin/env python3
"""Utilities for querying embedding vectors via the OpenAI-compatible API."""

import json
import os
from functools import lru_cache
from typing import Dict, List, Optional

from openai import AsyncOpenAI

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"


def _build_async_client() -> AsyncOpenAI:
    """Create a new AsyncOpenAI client configured like the LLM tool."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required for embeddings")

    base_url = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


@lru_cache(maxsize=1)
def _cached_client() -> AsyncOpenAI:
    """Return a cached AsyncOpenAI client to avoid re-instantiation."""
    return _build_async_client()


async def get_text_embedding(
    text: str,
    *,
    model: Optional[str] = None,
    client: Optional[AsyncOpenAI] = None,
    cache_dir: str = "",
) -> List[float]:
    """Fetch the embedding vector for a given text string."""
    if not text or not text.strip():
        raise ValueError("text must be a non-empty string")

    embedding_model = model or os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

    cache_path = ""
    cache_data: Optional[Dict[str, List[float]]] = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        safe_model = embedding_model.replace("/", "_")
        cache_path = os.path.join(cache_dir, f"{safe_model}.json")
        cache_data = _load_cache(cache_path)
        cached = cache_data.get(text) if cache_data else None
        if cached is not None:
            return cached

    resolved_client = client or _cached_client()

    response = await resolved_client.embeddings.create(model=embedding_model, input=text)
    if not response.data:
        raise RuntimeError("no embedding data returned from provider")

    embedding = response.data[0].embedding

    if cache_dir:
        cache_data = cache_data or {}
        cache_data[text] = embedding
        _save_cache(cache_path, cache_data)

    return embedding


def _load_cache(cache_path: str) -> Dict[str, List[float]]:
    """Load an embedding cache file if it exists."""
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache_path: str, cache_data: Dict[str, List[float]]) -> None:
    """Persist the embedding cache to disk."""
    tmp_path = f"{cache_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as cache_file:
        json.dump(cache_data, cache_file)
    os.replace(tmp_path, cache_path)


__all__ = ["get_text_embedding"]
