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


@pytest.mark.asyncio
async def test_vector_store_alias_is_searchable():
    """Aliases should be indexed as separate entries and retrievable offline."""
    project_root = Path(__file__).resolve().parents[1]
    docs_dir = project_root / "sop_docs"
    cache_dir = Path(os.getenv("EMBEDDING_CACHE_DIR", str(project_root / ".cache" / "embeddings")))
    store = SOPDocVectorStore(docs_dir=str(docs_dir), embedding_cache_dir=str(cache_dir))
    await store.build()

    results = await store.similarity_search("task planning", k=5)
    assert any(r.doc_id == "general/plan" for r in results)


@pytest.mark.asyncio
async def test_vector_store_dedupes_by_doc_id(monkeypatch, tmp_path):
    """If multiple entries match the same doc_id, only the best one is returned."""
    docs_dir = tmp_path / "sop_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / "a.md").write_text(
        "---\n"
        "description: Primary description\n"
        "aliases:\n"
        "  - alias one\n"
        "tool:\n"
        "  tool_id: LLM\n"
        "---\n"
        "Body\n",
        encoding="utf-8",
    )
    (docs_dir / "b.md").write_text(
        "---\n"
        "description: Other doc\n"
        "tool:\n"
        "  tool_id: LLM\n"
        "---\n"
        "Body\n",
        encoding="utf-8",
    )

    import sop_doc_vector_store as store_module

    def fake_get_text_embedding_sync(text: str, *, model=None, client=None, cache_dir: str = ""):
        # Make alias match strictly better than primary for doc 'a'.
        if text == "alias one":
            return [1.0, 0.0, 0.0]
        if text == "a: Primary description":
            return [0.8, 0.6, 0.0]  # cosine sim with query [1,0,0] is 0.8
        if text == "b: Other doc":
            return [0.1, 0.9, 0.0]  # low similarity
        # Default deterministic fallback
        return [0.0, 0.0, 1.0]

    monkeypatch.setattr(store_module, "get_text_embedding_sync", fake_get_text_embedding_sync)

    store = SOPDocVectorStore(docs_dir=str(docs_dir), embedding_cache_dir=str(tmp_path / "cache"))
    await store.build()

    results = await store.similarity_search("alias one", k=5)
    assert len(results) >= 1
    assert results[0].doc_id == "a"
    # Must not return duplicate doc_ids even though both primary+alias exist.
    assert len({r.doc_id for r in results}) == len(results)
    # Best match should be the alias entry (embedded_text == alias string).
    assert results[0].description == "alias one"
