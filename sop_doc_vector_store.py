#!/usr/bin/env python3
"""SOP document vector store powered by LangChain's in-memory implementation."""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

from sop_document import SOPDocumentLoader
from utils.embedding_utils import get_text_embedding_sync


def _dedupe_docs_with_scores_by_doc_id(
    docs_with_scores: Sequence[Tuple[Document, float]],
    *,
    k: int,
) -> List[Tuple[Document, float]]:
    """Keep only the best-scoring entry per doc_id and return up to k results."""
    best_by_doc_id: Dict[str, Tuple[Document, float]] = {}
    for doc, score in docs_with_scores:
        metadata = doc.metadata or {}
        doc_id = metadata.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id.strip():
            preview = (doc.page_content or "").replace("\n", "\\n")
            if len(preview) > 200:
                preview = preview[:200] + "..."
            raise ValueError(
                "Vector store Document missing required metadata['doc_id'] "
                f"(doc.id={getattr(doc, 'id', None)!r}, metadata_keys={sorted(metadata.keys())!r}, "
                f"page_content_preview={preview!r})"
            )

        existing = best_by_doc_id.get(doc_id)
        # InMemoryVectorStore returns cosine similarity (higher is better), so keep max score.
        # If tied, keep the earlier/better-ranked one (stable).
        if existing is None or score > existing[1]:
            best_by_doc_id[doc_id] = (doc, score)

    deduped = sorted(best_by_doc_id.values(), key=lambda pair: pair[1], reverse=True)
    return deduped[:k]


class _SOPDocEmbeddings(Embeddings):
    """LangChain embedding wrapper that delegates to our sync embedding helper."""

    def __init__(self, *, cache_dir: str = "", model: Optional[str] = None):
        self.cache_dir = cache_dir
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        # LangChain's embedding hooks are synchronous and typically invoked inside thread workers.
        return get_text_embedding_sync(text, model=self.model, cache_dir=self.cache_dir)


@dataclass
class SOPVectorStoreResult:
    """Search result returned from the SOP vector store."""

    doc_id: str
    description: str
    directories: List[str]
    tool_id: Optional[str]
    score: float
    metadata: Dict[str, Any]


class SOPDocVectorStore:
    """Vector store for SOP document descriptions."""

    def __init__(
        self,
        *,
        docs_dir: str = "sop_docs",
        embedding_cache_dir: str = "",
        embedding_model: Optional[str] = None,
    ) -> None:
        self.loader = SOPDocumentLoader(docs_dir)
        # Always use remote embeddings; persist them locally so subsequent runs are fast.
        # Cache directory is intentionally under `.cache/` (may be committed for test stability).
        self.embedding_cache_dir = embedding_cache_dir or str(
            (Path(__file__).resolve().parent / ".cache" / "embeddings").resolve()
        )
        # Default to the committed model so vector-search works out of the box
        # without requiring EMBEDDING_MODEL to be set in the runtime environment.
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL") or "text-embedding-ada-002"
        self._embedding = _SOPDocEmbeddings(
            cache_dir=self.embedding_cache_dir,
            model=self.embedding_model,
        )
        self._vector_store: Optional[InMemoryVectorStore] = None

    async def build(self) -> None:
        """Scan SOP docs and build an in-memory vector store."""
        debug = os.getenv("SOP_VECTOR_STORE_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
        t0 = time.perf_counter()
        doc_ids = self.loader.list_doc_ids()
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        def _append(text: str, metadata: Dict[str, Any]) -> None:
            texts.append(text)
            metadatas.append(metadata)

        skipped_docs_due_to_missing_file = 0
        invalid_docs = 0
        alias_entries_added = 0
        primary_entries_added = 0

        for doc_id in doc_ids:
            directories = doc_id.split("/")[:-1]
            base_metadata: Dict[str, Any] = {
                "doc_id": doc_id,
                "directories": directories,
                "tool_id": None,
                "used_doc_id_fallback": False,
            }
            description = ""
            primary_text = doc_id
            aliases_to_index: List[str] = []
            try:
                sop_doc = self.loader.load_sop_document(doc_id)
            except FileNotFoundError as exc:  # pragma: no cover - defensive log
                print(f"[SOP_VECTOR_STORE] Missing file for {doc_id}: {exc}")
                skipped_docs_due_to_missing_file += 1
                continue
            except ValueError as exc:  # e.g., missing YAML front matter
                print(f"[SOP_VECTOR_STORE] Invalid document {doc_id}: {exc}")
                base_metadata["used_doc_id_fallback"] = True
                invalid_docs += 1
            else:
                base_metadata["tool_id"] = (
                    sop_doc.tool.get("tool_id") if isinstance(sop_doc.tool, dict) else None
                )
                description = (sop_doc.description or "").strip()
                if description:
                    primary_text = f"{doc_id}: {description}"
                else:
                    base_metadata["used_doc_id_fallback"] = True

                raw_aliases = sop_doc.aliases or []
                seen_aliases: set[str] = set()
                for alias in raw_aliases:
                    if not isinstance(alias, str):
                        continue
                    cleaned = alias.strip()
                    if not cleaned:
                        continue
                    if cleaned in seen_aliases:
                        continue
                    # Reduce redundant entries.
                    if cleaned == doc_id or cleaned == primary_text:
                        continue
                    seen_aliases.add(cleaned)
                    aliases_to_index.append(cleaned)

            primary_metadata = dict(base_metadata)
            primary_metadata["entry_type"] = "primary"
            if description:
                primary_metadata["sop_description"] = description
            _append(primary_text, primary_metadata)
            primary_entries_added += 1

            for alias in aliases_to_index:
                alias_metadata = dict(base_metadata)
                alias_metadata["entry_type"] = "alias"
                alias_metadata["alias"] = alias
                if description:
                    alias_metadata["sop_description"] = description
                _append(alias, alias_metadata)
                alias_entries_added += 1

        self._vector_store = InMemoryVectorStore(embedding=self._embedding)
        if texts:
            if debug:
                print(
                    "[SOP_VECTOR_STORE] Building in-memory store. "
                    f"doc_ids={len(doc_ids)} primary_entries={primary_entries_added} "
                    f"alias_entries={alias_entries_added} texts_to_embed={len(texts)} "
                    f"invalid_docs={invalid_docs} missing_files={skipped_docs_due_to_missing_file}"
                )
            await asyncio.to_thread(
                self._vector_store.add_texts,
                texts,
                metadatas,
            )
        if debug:
            dt = time.perf_counter() - t0
            print(f"[SOP_VECTOR_STORE] build() complete in {dt:.3f}s")

    async def similarity_search(self, query: str, k: int = 4) -> List[SOPVectorStoreResult]:
        """Return the top-K SOP documents that best match the query."""
        if not self._vector_store:
            raise RuntimeError("Vector store has not been built. Call build() first.")

        raw_k = min(50, max(k, k * 5))
        docs_with_scores = await asyncio.to_thread(
            self._vector_store.similarity_search_with_score,
            query,
            raw_k,
        )
        docs_with_scores = _dedupe_docs_with_scores_by_doc_id(docs_with_scores, k=k)

        results: List[SOPVectorStoreResult] = []
        for doc, score in docs_with_scores:
            metadata = doc.metadata or {}
            results.append(
                SOPVectorStoreResult(
                    doc_id=metadata.get("doc_id", ""),
                    description=doc.page_content,
                    directories=metadata.get("directories", []),
                    tool_id=metadata.get("tool_id"),
                    score=score,
                    metadata=metadata,
                )
            )
        return results

    async def similarity_search_by_vector(
        self,
        embedding: Sequence[float],
        k: int = 4,
    ) -> List[SOPVectorStoreResult]:
        """Search using a pre-computed embedding vector."""
        if not self._vector_store:
            raise RuntimeError("Vector store has not been built. Call build() first.")

        raw_k = min(50, max(k, k * 5))
        docs_with_scores = await asyncio.to_thread(
            self._vector_store.similarity_search_with_score_by_vector,
            list(embedding),
            raw_k,
        )
        docs_with_scores = _dedupe_docs_with_scores_by_doc_id(docs_with_scores, k=k)
        results: List[SOPVectorStoreResult] = []
        for doc, score in docs_with_scores:
            metadata = doc.metadata or {}
            results.append(
                SOPVectorStoreResult(
                    doc_id=metadata.get("doc_id", ""),
                    description=doc.page_content,
                    directories=metadata.get("directories", []),
                    tool_id=metadata.get("tool_id"),
                    score=score,
                    metadata=metadata,
                )
            )
        return results
