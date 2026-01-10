#!/usr/bin/env python3
"""Utilities for querying embedding vectors via the OpenAI-compatible API."""

import json
import logging
import os
from functools import lru_cache
from typing import Dict, List, Optional

from openai import AsyncOpenAI, OpenAI

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1"

logger = logging.getLogger(__name__)

_IN_MEMORY_CACHE: Dict[str, Dict[str, List[float]]] = {}
_IN_MEMORY_CACHE_MTIME: Dict[str, float] = {}


def _build_async_client() -> AsyncOpenAI:
    """Create a new AsyncOpenAI client configured like the LLM tool."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required for embeddings")

    # Default matches README/.env.example. Override with OPENAI_API_BASE for OpenRouter/Azure/etc.
    base_url = os.getenv("OPENAI_API_BASE", DEFAULT_OPENAI_API_BASE)
    timeout_s = float(os.getenv("OPENAI_EMBEDDINGS_TIMEOUT_SECONDS", "15.0"))
    max_retries = int(os.getenv("OPENAI_EMBEDDINGS_MAX_RETRIES", "0"))
    return AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout_s,
        max_retries=max_retries,
    )


@lru_cache(maxsize=1)
def _cached_client() -> AsyncOpenAI:
    """Return a cached AsyncOpenAI client to avoid re-instantiation."""
    return _build_async_client()


def _build_sync_client() -> OpenAI:
    """Create a new synchronous OpenAI client (safe for thread worker use)."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required for embeddings")

    base_url = os.getenv("OPENAI_API_BASE", DEFAULT_OPENAI_API_BASE)
    timeout_s = float(os.getenv("OPENAI_EMBEDDINGS_TIMEOUT_SECONDS", "15.0"))
    max_retries = int(os.getenv("OPENAI_EMBEDDINGS_MAX_RETRIES", "0"))
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout_s,
        max_retries=max_retries,
    )


@lru_cache(maxsize=1)
def _cached_sync_client() -> OpenAI:
    """Return a cached synchronous client for embeddings."""
    return _build_sync_client()


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
    cache_data: Optional[Dict[str, List[float]]] = {}
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        safe_model = embedding_model.replace("/", "_")
        cache_path = os.path.join(cache_dir, f"{safe_model}.json")
        cache_data = _load_cache(cache_path)
        cached = cache_data.get(text)
        if cached is not None:
            return cached

    resolved_client = client or _cached_client()

    response = await resolved_client.embeddings.create(model=embedding_model, input=text)
    if not response.data:
        raise RuntimeError("no embedding data returned from provider")

    embedding = response.data[0].embedding

    if cache_dir:
        cache_data[text] = embedding
        _save_cache(cache_path, cache_data)

    return embedding


def get_text_embedding_sync(
    text: str,
    *,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
    cache_dir: str = "",
) -> List[float]:
    """Fetch the embedding vector synchronously.

    This is the preferred path for LangChain embedding hooks, since those are sync
    and typically invoked inside a thread worker (safe to block).
    """
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
        cached = cache_data.get(text)
        if cached is not None:
            return cached

    resolved_client = client or _cached_sync_client()

    response = resolved_client.embeddings.create(model=embedding_model, input=text)

    if not response.data:
        raise RuntimeError("no embedding data returned from provider")
    embedding = response.data[0].embedding

    if cache_dir:
        cache_data[text] = embedding
        _save_cache(cache_path, cache_data)

    return embedding

def _load_cache(cache_path: str) -> Dict[str, List[float]]:
    """Load an embedding cache file if it exists."""
    try:
        mtime = os.path.getmtime(cache_path)
    except FileNotFoundError:
        return {}

    cached = _IN_MEMORY_CACHE.get(cache_path)
    if cached is not None and _IN_MEMORY_CACHE_MTIME.get(cache_path) == mtime:
        return cached
    try:
        with open(cache_path, "r", encoding="utf-8") as cache_file:
            data = json.load(cache_file)
            loaded = data if isinstance(data, dict) else {}
            _IN_MEMORY_CACHE[cache_path] = loaded
            _IN_MEMORY_CACHE_MTIME[cache_path] = mtime
            return loaded
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save_cache(cache_path: str, cache_data: Dict[str, List[float]]) -> None:
    """Persist the embedding cache to disk."""
    tmp_path = f"{cache_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as cache_file:
        json.dump(cache_data, cache_file)
    os.replace(tmp_path, cache_path)
    _IN_MEMORY_CACHE[cache_path] = cache_data
    _IN_MEMORY_CACHE_MTIME[cache_path] = os.path.getmtime(cache_path)


__all__ = ["get_text_embedding", "get_text_embedding_sync"]
