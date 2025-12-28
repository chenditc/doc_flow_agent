#!/usr/bin/env python3
"""SOP document vector store powered by LangChain's in-memory implementation."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.embeddings import Embeddings

from sop_document import SOPDocumentLoader
from utils.embedding_utils import get_text_embedding


class _SOPDocEmbeddings(Embeddings):
    """LangChain embedding wrapper that delegates to our custom async helper."""

    def __init__(self, *, cache_dir: str = "", model: Optional[str] = None):
        self.cache_dir = cache_dir
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        return asyncio.run(get_text_embedding(text, model=self.model, cache_dir=self.cache_dir))


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
        self.embedding_cache_dir = embedding_cache_dir
        self.embedding_model = embedding_model
        self._embedding = _SOPDocEmbeddings(
            cache_dir=self.embedding_cache_dir,
            model=self.embedding_model,
        )
        self._vector_store: Optional[InMemoryVectorStore] = None

    async def build(self) -> None:
        """Scan SOP docs and build an in-memory vector store."""
        doc_ids = self.loader.list_doc_ids()
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for doc_id in doc_ids:
            directories = doc_id.split("/")[:-1]
            text = doc_id
            metadata = {
                "doc_id": doc_id,
                "directories": directories,
                "tool_id": None,
                "used_doc_id_fallback": False,
            }
            try:
                sop_doc = self.loader.load_sop_document(doc_id)
            except FileNotFoundError as exc:  # pragma: no cover - defensive log
                print(f"[SOP_VECTOR_STORE] Missing file for {doc_id}: {exc}")
                continue
            except ValueError as exc:  # e.g., missing YAML front matter
                print(f"[SOP_VECTOR_STORE] Invalid document {doc_id}: {exc}")
                metadata["used_doc_id_fallback"] = True
            else:
                metadata["tool_id"] = (
                    sop_doc.tool.get("tool_id") if isinstance(sop_doc.tool, dict) else None
                )
                description = (sop_doc.description or "").strip()
                if description:
                    text = f"{doc_id}: {description}"
                else:
                    metadata["used_doc_id_fallback"] = True

            texts.append(text)
            metadatas.append(metadata)

        self._vector_store = InMemoryVectorStore(embedding=self._embedding)
        if texts:
            await asyncio.to_thread(
                self._vector_store.add_texts,
                texts,
                metadatas,
            )

    async def similarity_search(self, query: str, k: int = 4) -> List[SOPVectorStoreResult]:
        """Return the top-K SOP documents that best match the query."""
        if not self._vector_store:
            raise RuntimeError("Vector store has not been built. Call build() first.")

        docs_with_scores = await asyncio.to_thread(
            self._vector_store.similarity_search_with_score,
            query,
            k,
        )

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

        docs_with_scores = await asyncio.to_thread(
            self._vector_store.similarity_search_with_score_by_vector,
            list(embedding),
            k,
        )
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
