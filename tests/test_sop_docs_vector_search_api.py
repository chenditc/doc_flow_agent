import os

from fastapi.testclient import TestClient


def _make_client() -> TestClient:
    # Must be set before importing the app to disable file watcher.
    os.environ["TESTING"] = "true"
    from visualization.server.viz_server import app  # noqa: WPS433

    return TestClient(app)


def test_sop_docs_vector_search_happy_path():
    client = _make_client()
    resp = client.post(
        "/api/sop-docs/vector-search",
        json={
            "query": "Write a simple Python script that prints 'Hello World'",
            "k": 3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["results"]) == 3
    for item in data["results"]:
        assert item["doc_id"]
        assert isinstance(item["score"], (int, float))


def test_sop_docs_vector_search_validation_empty_query():
    client = _make_client()
    resp = client.post("/api/sop-docs/vector-search", json={"query": "   ", "k": 3})
    assert resp.status_code == 400


def test_sop_docs_vector_search_empty_corpus(monkeypatch, tmp_path):
    client = _make_client()
    import visualization.server.sop_doc_api as sop_doc_api  # noqa: WPS433

    monkeypatch.setattr(sop_doc_api, "SOP_DOCS_DIR", tmp_path)

    resp = client.post(
        "/api/sop-docs/vector-search",
        json={"query": "anything", "k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["results"] == []

