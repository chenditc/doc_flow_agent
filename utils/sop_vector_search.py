#!/usr/bin/env python3
"""Shared SOP vector-search helper.

This module centralizes the "query rewrite + re-search" flow so it can be reused by:
- agent-side SOP selection (`SOPDocumentParser._get_vector_search_candidates`)
- visualization server vector search API (`POST /api/sop-docs/vector-search`)

The behavior is intentionally kept identical to the previous inline implementation in
`sop_document.py`:
- First vector search with the original query
- Optional rewrite decision based on env vars
- Optional rewrite via `rewrite_for_sop_vector_search`
- Second vector search with rewritten query
- If second search returns results: merge original + rewritten results
  - Deduplicate by `doc_id` picking the best score across both
  - Sort final results by score (desc)
  - Return per-item `used_query` mapping via `used_query_by_doc_id`
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from utils.sop_query_rewrite import (
    get_rewrite_threshold,
    rewrite_enabled,
    rewrite_for_sop_vector_search,
)


def _best_score(results: List[Any]) -> float:
    if not results:
        return 0.0
    return float(results[0].score or 0.0)


def _used_query_by_doc_id_for_results(results: List[Any], used_query: str) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for result in results or []:
        doc_id = result.doc_id or ""
        if not doc_id:
            continue
        mapping[doc_id] = used_query
    return mapping


def _merge_sort_dedupe_by_doc_id_with_origin(
    *,
    original_results: List[Any],
    rewritten_results: List[Any],
    original_query: str,
    rewritten_query: str,
    k: int,
) -> Tuple[List[Any], Dict[str, str]]:
    """Merge original+rewritten results, then score-sort and dedupe by doc_id.

    - Each candidate carries (doc_id, score, origin_query, first_seen_index) for deterministic ties.
    - Dedupes by doc_id keeping the highest score (tie -> earlier first_seen_index).
    - Sorts final by score desc, then first_seen_index asc.
    """

    candidates: List[Dict[str, Any]] = []
    first_seen_index = 0

    for result in list(original_results or []):
        doc_id = result.doc_id or ""
        if not doc_id:
            continue
        candidates.append(
            {
                "doc_id": doc_id,
                "score": float(result.score or 0.0),
                "origin_query": original_query,
                "first_seen_index": first_seen_index,
                "result": result,
            }
        )
        first_seen_index += 1

    for result in list(rewritten_results or []):
        doc_id = result.doc_id or ""
        if not doc_id:
            continue
        candidates.append(
            {
                "doc_id": doc_id,
                "score": float(result.score or 0.0),
                "origin_query": rewritten_query,
                "first_seen_index": first_seen_index,
                "result": result,
            }
        )
        first_seen_index += 1

    best_by_doc_id: Dict[str, Dict[str, Any]] = {}
    for cand in candidates:
        doc_id = cand["doc_id"]
        prev = best_by_doc_id.get(doc_id)
        if prev is None:
            best_by_doc_id[doc_id] = cand
            continue

        cand_score = float(cand.get("score", 0.0) or 0.0)
        prev_score = float(prev.get("score", 0.0) or 0.0)
        if cand_score > prev_score:
            best_by_doc_id[doc_id] = cand
            continue
        if cand_score == prev_score and int(cand["first_seen_index"]) < int(prev["first_seen_index"]):
            best_by_doc_id[doc_id] = cand

    kept = list(best_by_doc_id.values())
    kept.sort(key=lambda c: (-float(c.get("score", 0.0) or 0.0), int(c.get("first_seen_index", 0))))

    final_results: List[Any] = []
    used_query_by_doc_id: Dict[str, str] = {}
    for cand in kept[: max(0, int(k))]:
        result = cand["result"]
        doc_id = cand["doc_id"]
        final_results.append(result)
        used_query_by_doc_id[doc_id] = str(cand.get("origin_query", "") or original_query)

    return final_results, used_query_by_doc_id


async def vector_search_with_optional_rewrite(
    *,
    store: Any,
    query: str,
    k: int,
    llm_tool: Any | None = None,
) -> Tuple[List[Any], Dict[str, str]]:
    """Run SOP vector search, optionally rewriting the query and re-searching.

    Args:
        store: Any object supporting `await store.similarity_search(query, k=...)`.
        query: Original query string.
        k: Number of results to return.
        llm_tool: Optional injected LLM tool (used only when rewriting is needed).

    Returns:
        (results, used_query_by_doc_id) where:
          - results: list of vector-store result objects (length <= k)
          - used_query_by_doc_id: mapping of each returned result's doc_id -> query string that produced it
    """

    # Preserve raw query semantics for callers (parser previously did not strip).
    original_query = "" if query is None else str(query)
    mode = rewrite_enabled()
    threshold = get_rewrite_threshold()

    try:
        first_results = await store.similarity_search(original_query, k=k)
    except Exception as exc:  # pragma: no cover - defensive log
        print(f"[SOP_VECTOR_SEARCH] Failed to search vector store: {exc}")
        raise

    first_best_score = _best_score(first_results)

    should_rewrite = False
    if mode == "always":
        should_rewrite = True
    elif mode == "auto":
        should_rewrite = first_best_score < threshold

    rewrite_attempted = bool(should_rewrite)
    rewritten_query: Optional[str] = None
    results: List[Any] = list(first_results or [])

    if should_rewrite:
        # Use injected LLM tool if available; otherwise create one lazily.
        if llm_tool is None:
            from tools.llm_tool import LLMTool

            llm_tool = LLMTool()

        rewritten_query = await rewrite_for_sop_vector_search(original_query, llm_tool)

        # If rewrite returns None/empty/identical → do not run second search.
        if rewritten_query:
            try:
                second_results = await store.similarity_search(rewritten_query, k=k)
            except Exception as exc:  # pragma: no cover - defensive log
                print(f"[SOP_VECTOR_SEARCH] Failed to search vector store with rewritten query: {exc}")
                raise

            # If second search returns empty → keep first search results.
            if second_results:
                return _merge_sort_dedupe_by_doc_id_with_origin(
                    original_results=list(first_results or []),
                    rewritten_results=list(second_results or []),
                    original_query=original_query,
                    rewritten_query=rewritten_query,
                    k=k,
                )

    # No rewrite, rewrite not attempted, rewrite produced empty query, or second search returned empty.
    # In all cases, the result list is the original first search results.
    # Mapping for UI/debug: each returned doc_id maps to the original query string.
    used_query_by_doc_id = _used_query_by_doc_id_for_results(results, original_query)
    if rewrite_attempted:  # keep variables "used" for debuggability in local logs if needed
        _ = mode, threshold, first_best_score  # noqa: F841
    return results, used_query_by_doc_id

