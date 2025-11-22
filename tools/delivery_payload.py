#!/usr/bin/env python3
"""Unified delivery payload schema and validation helpers.

The DeliveryPayload data structure describes every piece of information that
needs to be rendered or downloaded on the result delivery page. Callers must
construct payload objects that follow this schema before invoking the web
result delivery tool; normalization now only validates and loads that data.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


class DeliveryPayloadError(ValueError):
    """Raised when the payload cannot be normalized or validated."""


@dataclass
class DeliveryMeta:
    title: str
    session_id: str
    task_id: str
    description: Optional[str] = None

    def validate(self) -> None:
        if not self.title:
            raise DeliveryPayloadError("DeliveryMeta.title cannot be empty")
        if not self.session_id:
            raise DeliveryPayloadError("DeliveryMeta.session_id cannot be empty")
        if not self.task_id:
            raise DeliveryPayloadError("DeliveryMeta.task_id cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BaseBlock:
    type: str
    title: Optional[str] = None
    description: Optional[str] = None

    def validate(self) -> None:
        if not self.type:
            raise DeliveryPayloadError("Block type cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TextBlock(BaseBlock):
    type: str = "text"
    content: str = ""
    format: str = "plain"  # plain, markdown, code, json
    asset_id: Optional[str] = None

    def validate(self) -> None:
        super().validate()
        if self.format not in {"plain", "markdown", "code", "json"}:
            raise DeliveryPayloadError(f"Unsupported text format: {self.format}")


@dataclass
class MarkdownAssetReference:
    asset_id: str
    placeholder: str
    original_path: str
    alt_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarkdownBlock(BaseBlock):
    type: str = field(init=False, default="markdown")
    content: str = ""
    asset_id: Optional[str] = None
    embedded_assets: List[MarkdownAssetReference] = field(default_factory=list)

    def validate(self) -> None:
        super().validate()
        if not self.content and not self.asset_id:
            raise DeliveryPayloadError("Markdown content requires either inline content or an asset reference")


@dataclass
class TableBlock(BaseBlock):
    type: str = field(init=False, default="table")
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    csv_asset_id: Optional[str] = None
    preview_rows: int = 0

    def validate(self) -> None:
        super().validate()
        if not self.columns and not self.csv_asset_id:
            raise DeliveryPayloadError("Table block requires columns when no csv_asset_id is provided")


@dataclass
class ImageBlock(BaseBlock):
    type: str = field(init=False, default="image")
    asset_id: str = ""
    alt_text: Optional[str] = None

    def validate(self) -> None:
        super().validate()


@dataclass
class FileBlock(BaseBlock):
    type: str = field(init=False, default="file")
    asset_id: str = ""
    label: Optional[str] = None

    def validate(self) -> None:
        super().validate()


@dataclass
class DeliveryAsset:
    source_path: str
    filename: str
    asset_type: str = "file"  # file, image, csv
    mime_type: Optional[str] = None
    description: Optional[str] = None
    id: Optional[str] = None

    def validate(self) -> None:
        if not self.source_path:
            raise DeliveryPayloadError(f"Asset {self.id} missing source_path")
        if not Path(self.source_path).expanduser().exists():
            raise DeliveryPayloadError(f"Asset source does not exist: {self.source_path}")
        if not self.filename:
            raise DeliveryPayloadError(f"Asset {self.id} missing filename")

    def ensure_id(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeliveryPayload:
    version: str
    meta: DeliveryMeta
    summary: Optional[str] = None
    blocks: List[BaseBlock] = field(default_factory=list)
    assets: List[DeliveryAsset] = field(default_factory=list)

    def validate(self, *, skip_meta_validation: bool = False) -> None:
        if self.version != "1.0":
            raise DeliveryPayloadError(f"Unsupported payload version: {self.version}")
        if not skip_meta_validation:
            self.meta.validate()
        asset_ids = set()
        for asset in self.assets:
            asset.ensure_id()
            if asset.id in asset_ids:
                raise DeliveryPayloadError(f"Duplicate asset id: {asset.id}")
            asset.validate()
            asset_ids.add(asset.id)
        for block in self.blocks:
            block.validate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "meta": self.meta.to_dict(),
            "summary": self.summary,
            "blocks": [block.to_dict() for block in self.blocks],
            "assets": [asset.to_dict() for asset in self.assets],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], *, skip_meta_validation: bool = False) -> "DeliveryPayload":
        meta = DeliveryMeta(**data["meta"])
        blocks = [_deserialize_block(block_data) for block_data in data.get("blocks", [])]
        assets = [DeliveryAsset(**asset_data) for asset_data in data.get("assets", [])]
        payload = cls(
            version=data.get("version", "1.0"),
            meta=meta,
            summary=data.get("summary"),
            blocks=blocks,
            assets=assets,
        )
        payload.validate(skip_meta_validation=skip_meta_validation)
        return payload


def _deserialize_block(block_data: Dict[str, Any]) -> BaseBlock:
    block_type = block_data.get("type")
    if block_type == "markdown":
        assets = [MarkdownAssetReference(**item) for item in block_data.get("embedded_assets", [])]
        return MarkdownBlock(
            title=block_data.get("title"),
            description=block_data.get("description"),
            content=block_data.get("content", ""),
            asset_id=block_data.get("asset_id"),
            embedded_assets=assets,
        )
    if block_type == "table":
        return TableBlock(
            title=block_data.get("title"),
            description=block_data.get("description"),
            columns=block_data.get("columns", []),
            rows=block_data.get("rows", []),
            csv_asset_id=block_data.get("csv_asset_id"),
            preview_rows=block_data.get("preview_rows", 0),
        )
    if block_type == "image":
        return ImageBlock(
            title=block_data.get("title"),
            description=block_data.get("description"),
            asset_id=block_data.get("asset_id", ""),
            alt_text=block_data.get("alt_text"),
        )
    if block_type == "file":
        return FileBlock(
            title=block_data.get("title"),
            description=block_data.get("description"),
            asset_id=block_data.get("asset_id", ""),
            label=block_data.get("label"),
        )
    # default to TextBlock, capturing markdown/text/json formats
    return TextBlock(
        type=block_type or "text",
        title=block_data.get("title"),
        description=block_data.get("description"),
        content=block_data.get("content", ""),
        format=block_data.get("format", "plain"),
        asset_id=block_data.get("asset_id"),
    )


def normalize_result_data(
    result_data: Any,
    *,
    session_id: str,
    task_id: str,
) -> DeliveryPayload:
    """Validate and load a delivery payload provided by the caller."""
    if isinstance(result_data, DeliveryPayload):
        payload = result_data
    elif isinstance(result_data, dict):
        payload_dict = deepcopy(result_data)
        meta_data = payload_dict.get("meta") or {}
        if not isinstance(meta_data, dict):
            raise DeliveryPayloadError("meta must be an object when provided")
        if not meta_data.get("title"):
            meta_data["title"] = meta_data.get("title") or "Task Result"
        meta_data.setdefault("session_id", session_id)
        meta_data.setdefault("task_id", task_id)
        payload_dict["meta"] = meta_data
        payload = DeliveryPayload.from_dict(payload_dict, skip_meta_validation=True)
    else:
        raise DeliveryPayloadError("result_data must be a DeliveryPayload or dict matching its schema")

    payload.validate(skip_meta_validation=True)
    if not payload.meta.session_id:
        payload.meta.session_id = session_id
    if not payload.meta.task_id:
        payload.meta.task_id = task_id
    if not payload.meta.title:
        payload.meta.title = "Task Result"
    if payload.meta.session_id != session_id:
        raise DeliveryPayloadError(
            f"Payload session_id '{payload.meta.session_id}' does not match expected '{session_id}'"
        )
    if payload.meta.task_id != task_id:
        raise DeliveryPayloadError(
            f"Payload task_id '{payload.meta.task_id}' does not match expected '{task_id}'"
        )
    return payload


__all__ = [
    "DeliveryPayload",
    "DeliveryPayloadError",
    "DeliveryMeta",
    "DeliveryAsset",
    "BaseBlock",
    "TextBlock",
    "MarkdownBlock",
    "TableBlock",
    "ImageBlock",
    "FileBlock",
    "MarkdownAssetReference",
    "normalize_result_data",
]
