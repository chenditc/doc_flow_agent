import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from utils.sop_vector_search import vector_search_with_optional_rewrite


@dataclass
class FakeResult:
    doc_id: str
    description: str
    score: float
    metadata: dict


@pytest.mark.asyncio
async def test_vector_search_auto_triggers_rewrite_when_score_low(monkeypatch):
    monkeypatch.setenv("SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE", "auto")
    monkeypatch.setenv("SOP_VECTOR_SEARCH_QUERY_REWRITE_THRESHOLD", "0.5")

    query = "Open https://example.com/user/123 and click the blue button"
    rewritten_query = "browser click button"

    first = [FakeResult(doc_id="raw/doc", description="raw/doc: Raw", score=0.2, metadata={})]
    second = [FakeResult(doc_id="rewritten/doc", description="rewritten/doc: Rewritten", score=0.9, metadata={})]

    store = MagicMock()

    async def search_side_effect(q: str, k: int = 5):
        if q == query:
            return first
        if q == rewritten_query:
            return second
        return []

    store.similarity_search = AsyncMock(side_effect=search_side_effect)

    llm_tool = AsyncMock()

    async def rewrite_side_effect(description: str, tool):
        assert description == query
        assert tool is llm_tool
        return rewritten_query

    monkeypatch.setattr("utils.sop_vector_search.rewrite_for_sop_vector_search", rewrite_side_effect)

    results, used_query_by_doc_id = await vector_search_with_optional_rewrite(
        store=store,
        query=query,
        k=5,
        llm_tool=llm_tool,
    )

    assert store.similarity_search.await_count == 2
    assert store.similarity_search.await_args_list[0].args[0] == query
    assert store.similarity_search.await_args_list[1].args[0] == rewritten_query
    # Merge contains both doc_ids and is score-sorted.
    assert [r.doc_id for r in results] == ["rewritten/doc", "raw/doc"]
    assert used_query_by_doc_id["raw/doc"] == query
    assert used_query_by_doc_id["rewritten/doc"] == rewritten_query


@pytest.mark.asyncio
async def test_vector_search_auto_skips_rewrite_when_score_high(monkeypatch):
    monkeypatch.setenv("SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE", "auto")
    monkeypatch.setenv("SOP_VECTOR_SEARCH_QUERY_REWRITE_THRESHOLD", "0.5")

    query = "List all blog outline SOPs"
    first = [FakeResult(doc_id="raw/doc", description="raw/doc: Raw", score=0.8, metadata={})]

    store = MagicMock()
    store.similarity_search = AsyncMock(return_value=first)

    llm_tool = AsyncMock()

    async def rewrite_side_effect(description: str, tool):
        raise AssertionError("rewrite should not be called when score is high")

    monkeypatch.setattr("utils.sop_vector_search.rewrite_for_sop_vector_search", rewrite_side_effect)

    results, used_query_by_doc_id = await vector_search_with_optional_rewrite(
        store=store,
        query=query,
        k=5,
        llm_tool=llm_tool,
    )

    assert store.similarity_search.await_count == 1
    assert results[0].doc_id == "raw/doc"
    assert used_query_by_doc_id["raw/doc"] == query


@pytest.mark.asyncio
async def test_vector_search_mode_always_forces_rewrite(monkeypatch):
    monkeypatch.setenv("SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE", "always")

    query = "Open https://example.com and login as Alice"
    rewritten_query = "browser login"

    # Even though first score is high, always-mode should attempt rewrite.
    first = [FakeResult(doc_id="raw/doc", description="raw/doc: Raw", score=0.9, metadata={})]
    second = [FakeResult(doc_id="rewritten/doc", description="rewritten/doc: Rewritten", score=0.95, metadata={})]

    store = MagicMock()

    async def search_side_effect(q: str, k: int = 5):
        if q == query:
            return first
        if q == rewritten_query:
            return second
        return []

    store.similarity_search = AsyncMock(side_effect=search_side_effect)

    llm_tool = AsyncMock()

    async def rewrite_side_effect(description: str, tool):
        assert description == query
        assert tool is llm_tool
        return rewritten_query

    monkeypatch.setattr("utils.sop_vector_search.rewrite_for_sop_vector_search", rewrite_side_effect)

    results, used_query_by_doc_id = await vector_search_with_optional_rewrite(
        store=store,
        query=query,
        k=5,
        llm_tool=llm_tool,
    )

    assert store.similarity_search.await_count == 2
    # Both results returned; score-sorted.
    assert [r.doc_id for r in results] == ["rewritten/doc", "raw/doc"]
    assert used_query_by_doc_id["raw/doc"] == query
    assert used_query_by_doc_id["rewritten/doc"] == rewritten_query


@pytest.mark.asyncio
async def test_vector_search_dedupe_picks_best_score_and_tracks_origin_query(monkeypatch):
    monkeypatch.setenv("SOP_VECTOR_SEARCH_QUERY_REWRITE_MODE", "auto")
    monkeypatch.setenv("SOP_VECTOR_SEARCH_QUERY_REWRITE_THRESHOLD", "0.5")

    query = "How do I operate a browser?"
    rewritten_query = "browser operations sop"

    # First search returns doc_ids A + SHARED.
    first = [
        FakeResult(doc_id="shared/doc", description="shared/doc: First", score=0.2, metadata={}),
        FakeResult(doc_id="a/doc", description="a/doc: A", score=0.1, metadata={}),
    ]
    # Second search returns doc_ids SHARED (higher score) + B.
    second = [
        FakeResult(doc_id="shared/doc", description="shared/doc: Second", score=0.9, metadata={}),
        FakeResult(doc_id="b/doc", description="b/doc: B", score=0.5, metadata={}),
    ]

    store = MagicMock()

    async def search_side_effect(q: str, k: int = 5):
        if q == query:
            return first
        if q == rewritten_query:
            return second
        return []

    store.similarity_search = AsyncMock(side_effect=search_side_effect)

    llm_tool = AsyncMock()

    async def rewrite_side_effect(description: str, tool):
        return rewritten_query

    monkeypatch.setattr("utils.sop_vector_search.rewrite_for_sop_vector_search", rewrite_side_effect)

    results, used_query_by_doc_id = await vector_search_with_optional_rewrite(
        store=store,
        query=query,
        k=10,
        llm_tool=llm_tool,
    )

    # Dedup: keep shared/doc from rewritten search (higher score 0.9).
    assert [r.doc_id for r in results] == ["shared/doc", "b/doc", "a/doc"]
    assert used_query_by_doc_id["shared/doc"] == rewritten_query
    assert used_query_by_doc_id["b/doc"] == rewritten_query
    assert used_query_by_doc_id["a/doc"] == query

