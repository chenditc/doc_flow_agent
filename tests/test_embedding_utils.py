#!/usr/bin/env python3
import json
import os
import tempfile
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from utils.embedding_utils import get_text_embedding, _cached_client


class TestEmbeddingUtils(IsolatedAsyncioTestCase):
    """Tests for the embedding utility helpers."""

    def tearDown(self) -> None:
        _cached_client.cache_clear()

    async def test_get_text_embedding_without_cache(self):
        """Ensure embeddings are requested from the API when no cache is used."""
        fake_embedding = [0.1, 0.2, 0.3]
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=fake_embedding)]
        )

        with patch("utils.embedding_utils._cached_client", return_value=mock_client):
            result = await get_text_embedding("hello", model="unit-test-model")

        self.assertEqual(result, fake_embedding)
        mock_client.embeddings.create.assert_awaited_once_with(
            model="unit-test-model",
            input="hello",
        )

    async def test_get_text_embedding_with_cache_dir(self):
        """Verify results are read from and written to the cache directory."""
        fake_embedding = [0.5, 0.6]
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=fake_embedding)]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = os.path.join(tmpdir, "unit-test-model.json")
            with patch("utils.embedding_utils._cached_client", return_value=mock_client):
                # First call hits the mocked client and writes cache
                first = await get_text_embedding("cached text", model="unit-test-model", cache_dir=tmpdir)
                # Second call should read from cache without calling API again
                second = await get_text_embedding("cached text", model="unit-test-model", cache_dir=tmpdir)
            file_exists = os.path.exists(cache_file)
            if file_exists:
                with open(cache_file, "r", encoding="utf-8") as handle:
                    cache_data = json.load(handle)
            else:
                cache_data = {}

        self.assertEqual(first, fake_embedding)
        self.assertEqual(second, fake_embedding)
        self.assertTrue(file_exists)
        self.assertEqual(cache_data["cached text"], fake_embedding)
        mock_client.embeddings.create.assert_awaited_once()
