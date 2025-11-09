#!/usr/bin/env python3
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest

from sop_doc_vector_store import SOPDocVectorStore


def create_sop_doc(base_dir: Path, relative_path: str, front_matter: Dict[str, str]) -> None:
    """Utility to create a SOP markdown file under a temporary directory."""
    target = base_dir / f"{relative_path}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    fm_lines = ["---"]
    for key, value in front_matter.items():
        if isinstance(value, dict):
            fm_lines.append(f"{key}:")
            for nested_key, nested_value in value.items():
                fm_lines.append(f"  {nested_key}: {nested_value}")
        else:
            fm_lines.append(f"{key}: {value}")
    fm_lines.append("---\n")
    target.write_text("\n".join(fm_lines), encoding="utf-8")


@pytest.mark.asyncio
async def test_vector_store_builds_and_searches(tmp_path):
    docs_dir = tmp_path / "sop_docs"
    create_sop_doc(
        docs_dir,
        "tools/python",
        {
            "doc_id": "tools/python",
            "description": "Run Python code for automation tasks.",
            "tool": {"tool_id": "PYTHON_EXECUTOR"},
        },
    )
    create_sop_doc(
        docs_dir,
        "tools/web",
        {
            "doc_id": "tools/web",
            "description": "Visit websites via browser automation.",
            "tool": {"tool_id": "WEB_VISITOR"},
        },
    )

    embeddings: Dict[str, List[float]] = {
        "tools/python: Run Python code for automation tasks.": [0.9, 0.1],
        "tools/web: Visit websites via browser automation.": [0.1, 0.9],
        "Query xxx website": [0.2, 0.8],
    }

    async def fake_get_text_embedding(text: str, **_: str) -> List[float]:
        return embeddings[text]

    with patch("sop_doc_vector_store.get_text_embedding", side_effect=fake_get_text_embedding):
        store = SOPDocVectorStore(docs_dir=str(docs_dir))
        await store.build()
        results = await store.similarity_search("Query xxx website", k=1)

    assert len(results) == 1
    match = results[0]
    assert match.doc_id == "tools/web"
    assert match.directories == ["tools"]
    assert match.tool_id == "WEB_VISITOR"
    assert match.description == "tools/web: Visit websites via browser automation."
    assert match.metadata["doc_id"] == "tools/web"
    assert match.score >= 0


@pytest.mark.asyncio
async def test_vector_store_uses_doc_id_when_description_missing(tmp_path):
    docs_dir = tmp_path / "sop_docs"
    create_sop_doc(
        docs_dir,
        "general/plan",
        {
            "doc_id": "general/plan",
            "description": "",
            "tool": {"tool_id": "PLANNER"},
        },
    )
    create_sop_doc(
        docs_dir,
        "tools/search",
        {
            "doc_id": "tools/search",
            "description": "Search across indexed content.",
            "tool": {"tool_id": "SEARCH_TOOL"},
        },
    )

    embeddings = {
        "tools/search: Search across indexed content.": [0.7, 0.3],
        "general/plan": [0.2, 0.8],
        "search query": [0.6, 0.4],
    }

    async def fake_get_text_embedding(text: str, **_: str) -> List[float]:
        return embeddings[text]

    with patch("sop_doc_vector_store.get_text_embedding", side_effect=fake_get_text_embedding) as mock_embed:
        store = SOPDocVectorStore(docs_dir=str(docs_dir))
        await store.build()
        calls = [call.args[0] for call in mock_embed.call_args_list]
        assert "tools/search: Search across indexed content." in calls
        assert "general/plan" in calls
        results = await store.similarity_search("search query", k=1)

    assert len(results) == 1
    assert results[0].doc_id == "tools/search"
    assert results[0].metadata["used_doc_id_fallback"] is False


@pytest.mark.asyncio
async def test_vector_store_fallbacks_for_missing_front_matter(tmp_path):
    docs_dir = tmp_path / "sop_docs"
    invalid_doc = docs_dir / "examples" / "user_communicate_example.md"
    invalid_doc.parent.mkdir(parents=True, exist_ok=True)
    invalid_doc.write_text("## Example without YAML front matter", encoding="utf-8")

    embeddings = {
        "examples/user_communicate_example": [0.3, 0.3],
        "find communicate example": [0.3, 0.3],
    }

    async def fake_get_text_embedding(text: str, **_: str) -> List[float]:
        return embeddings[text]

    with patch("sop_doc_vector_store.get_text_embedding", side_effect=fake_get_text_embedding):
        store = SOPDocVectorStore(docs_dir=str(docs_dir))
        await store.build()
        results = await store.similarity_search("find communicate example", k=1)

    assert len(results) == 1
    match = results[0]
    assert match.doc_id == "examples/user_communicate_example"
    assert match.metadata["used_doc_id_fallback"] is True
