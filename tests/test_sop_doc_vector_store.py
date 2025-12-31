#!/usr/bin/env python3
import os
from pathlib import Path

import pytest

from sop_doc_vector_store import SOPDocVectorStore


@pytest.mark.asyncio
async def test_vector_store_builds_and_searches():
    """Builds/searches using real embeddings loaded from the committed cache."""
    project_root = Path(__file__).resolve().parents[1]
    docs_dir = project_root / "sop_docs"
    cache_dir = Path(os.getenv("EMBEDDING_CACHE_DIR", str(project_root / ".cache" / "embeddings")))
    store = SOPDocVectorStore(docs_dir=str(docs_dir), embedding_cache_dir=str(cache_dir))
    await store.build()
    results = await store.similarity_search("Write a simple Python script that prints 'Hello World'", k=3)
    assert len(results) == 3
    assert all(r.doc_id for r in results)
    assert all(isinstance(r.directories, list) for r in results)


@pytest.mark.asyncio
async def test_vector_store_fallbacks_for_missing_front_matter():
    """Missing YAML docs should fall back to doc_id-only text, which must be cached."""
    project_root = Path(__file__).resolve().parents[1]
    docs_dir = project_root / "sop_docs"
    cache_dir = Path(os.getenv("EMBEDDING_CACHE_DIR", str(project_root / ".cache" / "embeddings")))
    store = SOPDocVectorStore(docs_dir=str(docs_dir), embedding_cache_dir=str(cache_dir))
    await store.build()

    # For docs missing YAML front matter, the embedded text is the doc_id itself.
    results = await store.similarity_search("examples/user_communicate_example", k=1)
    assert len(results) == 1
    assert results[0].doc_id == "examples/user_communicate_example"
    assert results[0].metadata["used_doc_id_fallback"] is True
