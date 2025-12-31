#!/usr/bin/env python3
"""Generate / refresh the committed SOP embedding cache.

This script populates `EMBEDDING_CACHE_DIR/<model>.json` by calling the real
embedding endpoint and persisting results on disk. Tests can then run fast and
offline as long as the SOP docs (and the common query strings below) don't
change.

Usage:
  python tools/generate_embedding_cache.py

Environment:
  - EMBEDDING_MODEL (default: text-embedding-ada-002)
  - EMBEDDING_CACHE_DIR (default: <repo>/.cache/embeddings)
  - OPENAI_API_KEY / OPENAI_API_BASE (loaded from .env if present)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sop_document import SOPDocumentLoader  # noqa: E402
from utils.embedding_utils import get_text_embedding  # noqa: E402


def _doc_texts(docs_dir: Path) -> list[str]:
    """Mirror SOPDocVectorStore.build() text formatting."""
    loader = SOPDocumentLoader(str(docs_dir))
    texts: list[str] = []
    for doc_id in loader.list_doc_ids():
        text = doc_id
        try:
            sop_doc = loader.load_sop_document(doc_id)
        except ValueError:
            # Missing YAML front matter -> doc_id-only embedding
            texts.append(text)
            continue
        except FileNotFoundError:
            continue
        description = (getattr(sop_doc, "description", "") or "").strip()
        if description:
            text = f"{doc_id}: {description}"
        texts.append(text)
    return texts


def _common_query_texts() -> list[str]:
    """Queries used by unit/integration tests for vector search."""
    return [
        "Write a simple Python script that prints 'Hello World'",
        "Generate a welcome message: Write a simple greeting message for a new user to school, less than 50 words. This is for a welcome screen.",
        "Generate a simple greeting message: 'Hello, welcome to our platform!' - keep it exactly like this",
        "Run ls command to list home directory contents using: ls -la ~/",
        "List home directory contents using command: ls -la ~/",
        "Need a custom doc",
        "Need python tool",
        "根据tools/bash完成任务",
    ]


async def _populate_cache(*, docs_dir: Path, cache_dir: Path, model: str) -> None:
    texts = _doc_texts(docs_dir) + _common_query_texts()
    # De-dupe but keep stable order
    seen: set[str] = set()
    ordered: list[str] = []
    for t in texts:
        if t and t not in seen:
            seen.add(t)
            ordered.append(t)

    for idx, text in enumerate(ordered, start=1):
        await get_text_embedding(text, model=model, cache_dir=str(cache_dir))
        if idx % 10 == 0:
            print(f"[EMBED CACHE] {idx}/{len(ordered)}")
    print(f"[EMBED CACHE] Done. Total cached texts: {len(ordered)}")


def main() -> None:
    repo_root = REPO_ROOT
    load_dotenv(repo_root / ".env")

    docs_dir = repo_root / "sop_docs"
    cache_dir = Path(os.getenv("EMBEDDING_CACHE_DIR", str(repo_root / ".cache" / "embeddings"))).resolve()
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

    cache_dir.mkdir(parents=True, exist_ok=True)
    asyncio.run(_populate_cache(docs_dir=docs_dir, cache_dir=cache_dir, model=model))


if __name__ == "__main__":
    main()

