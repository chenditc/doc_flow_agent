import json
import os

from orchestrator_service.env_file import load_env_file


def test_load_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / "env.json"
    payload = {"DOCFLOW_TEST_ENV": "applied", "INT_VALUE": 42}
    env_file.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.delenv("DOCFLOW_TEST_ENV", raising=False)
    monkeypatch.delenv("INT_VALUE", raising=False)

    load_env_file(str(env_file))
    assert os.environ["DOCFLOW_TEST_ENV"] == "applied"
    assert os.environ["INT_VALUE"] == "42"
