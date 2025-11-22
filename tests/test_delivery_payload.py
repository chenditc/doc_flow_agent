#!/usr/bin/env python3
"""Unit tests for strict delivery payload validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.delivery_payload import (
    DeliveryPayload,
    DeliveryPayloadError,
    normalize_result_data,
)


def _base_payload_dict(tmp_path: Path, *, session_id: str, task_id: str) -> dict:
    asset_path = tmp_path / "report.txt"
    asset_path.write_text("report body")
    return {
        "version": "1.0",
        "meta": {
            "title": "Task Result",
            "session_id": session_id,
            "task_id": task_id,
        },
        "summary": "All done.",
        "blocks": [
            {
                "type": "text",
                "title": "Summary",
                "content": "Report text",
                "format": "plain",
            },
            {
                "type": "file",
                "title": "Attachment",
                "asset_id": "file_1",
            },
        ],
        "assets": [
            {
                "id": "file_1",
                "source_path": str(asset_path),
                "filename": "report.txt",
                "asset_type": "file",
            }
        ],
    }


def test_normalize_valid_payload(tmp_path: Path):
    data = _base_payload_dict(tmp_path, session_id="s1", task_id="t1")
    payload = normalize_result_data(data, session_id="s1", task_id="t1")
    assert payload.meta.title == "Task Result"
    assert len(payload.blocks) == 2
    assert payload.assets[0].filename == "report.txt"


def test_normalize_accepts_delivery_payload_instance(tmp_path: Path):
    data = _base_payload_dict(tmp_path, session_id="sA", task_id="tA")
    payload_obj = DeliveryPayload.from_dict(data)
    normalized = normalize_result_data(payload_obj, session_id="sA", task_id="tA")
    assert normalized is payload_obj  # Should not re-create


def test_normalize_session_mismatch_raises(tmp_path: Path):
    data = _base_payload_dict(tmp_path, session_id="expected", task_id="t9")
    with pytest.raises(DeliveryPayloadError, match="session_id"):
        normalize_result_data(data, session_id="WRONG", task_id="t9")


def test_normalize_task_mismatch_raises(tmp_path: Path):
    data = _base_payload_dict(tmp_path, session_id="sX", task_id="correct")
    with pytest.raises(DeliveryPayloadError, match="task_id"):
        normalize_result_data(data, session_id="sX", task_id="other")


def test_normalize_invalid_type_raises():
    with pytest.raises(DeliveryPayloadError, match="DeliveryPayload"):
        normalize_result_data("not-a-dict", session_id="s", task_id="t")
