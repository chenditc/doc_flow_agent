#!/usr/bin/env python3
"""Web Result Delivery Tool for Doc Flow Agent
Tool for web-based result delivery to users (text, files, images)

Copyright 2024-2025 Di Chen

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import csv
import json
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.retry_strategies import AppendValidationHintStrategy

from .base_tool import BaseTool
from .llm_tool import LLMTool
from .delivery_payload import (
    DeliveryPayload,
    DeliveryPayloadError,
    DeliveryAsset,
    MarkdownBlock,
    TableBlock,
    TextBlock,
    normalize_result_data,
)


class WebResultDeliveryTool(BaseTool):
    """Web-based result delivery tool for presenting results to users"""
    
    def __init__(self, llm_tool, max_generation_attempts: int = 3):
        super().__init__("WEB_RESULT_DELIVERY")
        if max_generation_attempts < 1:
            raise ValueError("max_generation_attempts must be at least 1")

        self.llm_tool = llm_tool
        self.max_generation_attempts = max_generation_attempts
    
    async def execute(self, parameters: Dict[str, Any], sop_doc_body: Optional[str] = None) -> Dict[str, Any]:
        """Execute web result delivery tool with given parameters
        
        Args:
            parameters: Dictionary containing:
                - result_data (str or dict): The result to display (text, JSON, etc.)
                  Can include file paths and image paths that need to be served
                - session_id (str): Session identifier
                - task_id (str): Task identifier
            
        Returns:
            Dictionary with result URL and status
            
        Raises:
            ValueError: If required parameters are missing
        """
        self.validate_parameters(parameters, ['result_data', 'session_id', 'task_id'])
        
        result_data = parameters.get('result_data', '')
        session_id = parameters.get('session_id', '')
        task_id = parameters.get('task_id', '')
        job_id = parameters.get('job_id') or os.getenv('DOCFLOW_JOB_ID')
        
        visualization_base = self._get_visualization_base_url()
        file_base_url = self._get_file_base_url(visualization_base, session_id, task_id, job_id)
        result_url = self._get_result_url(visualization_base, session_id, task_id, job_id)
        pretty_result_url = self._get_pretty_result_url(result_url)

        # Get base directory and create session/task directory
        # Reuse user_comm directory structure to avoid docker volume changes
        project_root = Path(__file__).parent.parent
        session_dir = project_root / "user_comm" / "sessions" / session_id / task_id
        index_file = session_dir / "index.html"
        files_dir = session_dir / "files"
        pretty_page_name = "pretty.html"
        pretty_file = session_dir / pretty_page_name
        
        # Check if result already exists (idempotent)
        if index_file.exists():
            print(f"[WEB_RESULT_DELIVERY] Found existing result page for {session_id}/{task_id}")
            return {
                "result_url": result_url,
                "pretty_result_url": pretty_result_url,
                "status": "ok",
                "file_included_in_html": self._collect_served_file_paths(files_dir)
            }
        
        # Create directory structure
        session_dir.mkdir(parents=True, exist_ok=True)
        files_dir.mkdir(exist_ok=True)
        data_file_name = "result_data.json"
        payload_file_name = "delivery_payload.json"
        data_file_path = files_dir / data_file_name
        payload_file_path = files_dir / payload_file_name
        self._write_result_data_file(result_data, data_file_path)
        delivery_payload = self._build_delivery_payload(result_data, session_id, task_id)
        generated_assets_dir = session_dir / "generated_assets"
        self._ensure_downloadable_blocks(delivery_payload, generated_assets_dir)
        self._write_delivery_payload_file(delivery_payload, payload_file_path)

        payload_file_url = f"{file_base_url}{payload_file_name}"

        included_files: List[str] = [str(data_file_path), str(payload_file_path)]

        asset_paths = self._copy_payload_assets(delivery_payload, files_dir)
        included_files.extend(str(path) for path in asset_paths)

        fallback_html = self._render_fallback_page(payload_file_name, pretty_page_name)
        self._write_html_file(index_file, fallback_html)

        for i in range(3):
            # Generate HTML page using LLM and get file mappings
            html_content, file_mappings = await self._generate_result_html_with_llm(
                delivery_payload,
                result_data,
                session_id,
                task_id,
                payload_file_name,
                payload_file_url,
                file_base_url,
            )
            
            # Copy files based on LLM-identified mappings
            try:
                copied_paths = self._copy_files_from_mappings(file_mappings, files_dir)
                included_files.extend(str(path) for path in copied_paths)
                break  # Success
            except ValueError as e:
                print(f"[WEB_RESULT_DELIVERY] Error copying files: {e}")
                if i == 2:
                    raise  # Reraise after final attempt
                # Retry generation to get correct file paths
                continue
        
        # Write pretty page atomically
        self._write_html_file(pretty_file, html_content)
        
        # Get result URL and notify user
        self._notify_user(result_url, session_id, task_id)
        
        print(f"[WEB_RESULT_DELIVERY] Result delivered for {session_id}/{task_id}")
        return {
            "result_url": result_url,
            "pretty_result_url": pretty_result_url,
            "status": "ok",
            "file_included_in_html": sorted(set(included_files))
        }
    
    def _copy_files_from_mappings(self, file_mappings: List[Dict[str, str]], dest_dir: Path) -> List[Path]:
        """Copy files based on source-target mappings from LLM
        
        Args:
            file_mappings: List of dicts with 'source' and 'target' keys
            dest_dir: Destination directory for files
        """
        copied: List[Path] = []
        for mapping in file_mappings:
            source_path = mapping.get('source', '')
            target_filename = mapping.get('target', '')
            
            if not source_path or not target_filename:
                raise ValueError(f"[WEB_RESULT_DELIVERY] Warning: Invalid mapping: {mapping}")

            source = Path(source_path)
            if not source.exists():
                raise ValueError(f"[WEB_RESULT_DELIVERY] Warning: File not found: {source_path}")

            if not source.is_file():
                raise ValueError(f"[WEB_RESULT_DELIVERY] Warning: Not a file: {source_path}")

            # Copy file to destination with target filename
            dest_file = dest_dir / target_filename
            try:
                shutil.copy2(source, dest_file)
                print(f"[WEB_RESULT_DELIVERY] Copied file: {source_path} -> {target_filename}")
                copied.append(dest_file)
            except Exception as e:
                raise ValueError(f"[WEB_RESULT_DELIVERY] Error copying {source_path}: {e}")
        return copied

    def _collect_served_file_paths(self, files_dir: Path) -> List[str]:
        if not files_dir.exists():
            return []
        files = [str(path) for path in files_dir.glob('*') if path.is_file()]
        return sorted(files)

    def _get_visualization_base_url(self) -> str:
        base_url = os.getenv('VISUALIZATION_SERVER_URL', 'http://localhost:8000')
        if not base_url.startswith(('http://', 'https://')):
            print(f"[WEB_RESULT_DELIVERY] Warning: VISUALIZATION_SERVER_URL should include protocol, got: {base_url}")
            base_url = f"http://{base_url}"
        return base_url.rstrip('/')

    def _get_file_base_url(self, base_url: str, session_id: str, task_id: str, job_id: Optional[str]) -> str:
        if job_id:
            return f"{base_url}/sandbox/{job_id}/app/user_comm/sessions/{session_id}/{task_id}/files/"
        return f"{base_url}/result-delivery/{session_id}/{task_id}/files/"

    def _get_result_url(self, base_url: str, session_id: str, task_id: str, job_id: Optional[str]) -> str:
        if job_id:
            return f"{base_url}/sandbox/{job_id}/app/user_comm/sessions/{session_id}/{task_id}/index.html"
        return f"{base_url}/result-delivery/{session_id}/{task_id}/"

    def _get_pretty_result_url(self, result_url: str) -> str:
        if result_url.endswith("index.html"):
            return result_url[:-len("index.html")] + "pretty.html"
        if result_url.endswith("/"):
            return f"{result_url}pretty.html"
        return f"{result_url}/pretty.html"
    
    def _notify_user(self, result_url: str, session_id: str, task_id: str) -> None:
        """Notify user about the result using the notification system."""
        import sys
        from pathlib import Path
        # Add project root to path
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from utils.user_notify import notify_user
        
        message = f"Task result available:\nSession: {session_id}\nTask: {task_id}\nView at: {result_url}"
        notify_user(message)

    def _write_result_data_file(self, result_data: Any, file_path: Path) -> None:
        """Persist result data so the HTML page can load it dynamically."""
        if isinstance(result_data, (dict, list)):
            payload = result_data
        else:
            payload = {
                "type": "text",
                "content": str(result_data)
            }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"[WEB_RESULT_DELIVERY] Saved result data to {file_path}")

    def _build_delivery_payload(
        self,
        result_data: Any,
        session_id: str,
        task_id: str,
    ) -> DeliveryPayload:
        try:
            payload = normalize_result_data(
                result_data,
                session_id=session_id,
                task_id=task_id,
            )
        except DeliveryPayloadError as exc:
            raise ValueError(f"Failed to normalize result data: {exc}") from exc

        payload._provided_meta_keys = self._extract_meta_field_keys(result_data)
        return payload

    def _write_delivery_payload_file(self, payload: DeliveryPayload, file_path: Path) -> None:
        payload_dict = payload.to_dict()
        provided_meta_keys = getattr(payload, "_provided_meta_keys", None)
        if provided_meta_keys is not None:
            meta_dict = payload_dict.get("meta", {})
            pruned_meta = {k: v for k, v in meta_dict.items() if k in provided_meta_keys}
            payload_dict["meta"] = pruned_meta
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(payload_dict, f, ensure_ascii=False, indent=2)
        print(f"[WEB_RESULT_DELIVERY] Saved delivery payload to {file_path}")

    def _ensure_downloadable_blocks(self, payload: DeliveryPayload, generated_dir: Path) -> None:
        for block in payload.blocks:
            if isinstance(block, TableBlock):
                if block.csv_asset_id:
                    continue
                has_data = bool(block.columns) or bool(block.rows)
                if not has_data:
                    continue
                asset = self._create_csv_asset(payload, block, generated_dir)
                block.csv_asset_id = asset.id
            elif isinstance(block, MarkdownBlock):
                if block.asset_id or not block.content:
                    continue
                asset = self._create_text_asset(
                    payload=payload,
                    block=block,
                    generated_dir=generated_dir,
                    extension=".md",
                    content=block.content,
                    mime_type="text/markdown",
                )
                block.asset_id = asset.id
            elif isinstance(block, TextBlock):
                if block.asset_id or not block.content:
                    continue
                extension, mime_type = self._pick_text_block_extension(block)
                asset = self._create_text_asset(
                    payload=payload,
                    block=block,
                    generated_dir=generated_dir,
                    extension=extension,
                    content=block.content,
                    mime_type=mime_type,
                )
                block.asset_id = asset.id

    def _create_text_asset(
        self,
        *,
        payload: DeliveryPayload,
        block: TextBlock | MarkdownBlock,
        generated_dir: Path,
        extension: str,
        content: str,
        mime_type: Optional[str] = None,
    ) -> DeliveryAsset:
        generated_dir.mkdir(parents=True, exist_ok=True)
        filename = self._build_asset_filename(block, "content", extension)
        file_path = generated_dir / filename
        with open(file_path, 'w', encoding='utf-8') as handle:
            handle.write(content or '')
        asset = DeliveryAsset(
            source_path=str(file_path),
            filename=filename,
            asset_type="file",
            mime_type=mime_type,
            description=block.description or block.title or f"{block.type} content",
            id=uuid.uuid4().hex,
        )
        payload.assets.append(asset)
        return asset

    def _create_csv_asset(
        self,
        payload: DeliveryPayload,
        block: TableBlock,
        generated_dir: Path,
    ) -> DeliveryAsset:
        generated_dir.mkdir(parents=True, exist_ok=True)
        filename = self._build_asset_filename(block, "table", ".csv")
        file_path = generated_dir / filename
        with open(file_path, 'w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            if block.columns:
                writer.writerow(block.columns)
            for row in block.rows or []:
                writer.writerow([self._stringify_csv_cell(value) for value in row])
        asset = DeliveryAsset(
            source_path=str(file_path),
            filename=filename,
            asset_type="csv",
            mime_type="text/csv",
            description=block.description or block.title or "Table data",
            id=uuid.uuid4().hex,
        )
        payload.assets.append(asset)
        return asset

    def _build_asset_filename(self, block: Any, fallback: str, extension: str) -> str:
        slug = self._slugify(block.title or block.type, fallback)
        unique = uuid.uuid4().hex[:8]
        if not extension.startswith('.'):
            extension = f".{extension}"
        return f"{slug}-{unique}{extension}"

    def _slugify(self, value: Optional[str], fallback: str) -> str:
        base = (value or fallback or "block").lower()
        slug = re.sub(r'[^a-z0-9]+', '-', base).strip('-')
        return slug or fallback or "block"

    def _stringify_csv_cell(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _pick_text_block_extension(self, block: TextBlock) -> tuple[str, Optional[str]]:
        fmt = (block.format or '').lower()
        block_type = (block.type or '').lower()
        if fmt == "json" or block_type == "json":
            return ".json", "application/json"
        if fmt == "markdown" or block_type == "markdown":
            return ".md", "text/markdown"
        if fmt == "code":
            return ".txt", "text/plain"
        return ".txt", "text/plain"

    def _copy_payload_assets(self, payload: DeliveryPayload, dest_dir: Path) -> List[Path]:
        copied: List[Path] = []
        for asset in payload.assets:
            source = Path(asset.source_path)
            if not source.exists():
                raise ValueError(f"[WEB_RESULT_DELIVERY] Asset not found: {asset.source_path}")
            dest_path = dest_dir / asset.filename
            shutil.copy2(source, dest_path)
            copied.append(dest_path)
            print(f"[WEB_RESULT_DELIVERY] Copied asset {asset.source_path} -> {dest_path}")
        return copied

    def _render_fallback_page(self, payload_file_name: str, pretty_page_name: str) -> str:
        payload_relative_path = f"files/{payload_file_name}"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Task Result</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
  <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/json-formatter-js@2.3.4/dist/json-formatter.min.css">
  <style>
    :root {{
      font-family: 'Roboto', sans-serif;
      background-color: #f5f7fb;
      color: #1f2933;
      --card-bg: #ffffff;
      --border: #e0e6ed;
    }}
    body {{
      margin: 0;
    }}
    .app-header {{
      background: #0f62fe;
      color: #fff;
      padding: 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
    }}
    .title-group {{
      display: flex;
      gap: 1rem;
      align-items: center;
    }}
    .material-icons {{
      font-size: 2.5rem;
    }}
    main {{
      padding: 1.5rem;
      max-width: 1200px;
      margin: 0 auto;
    }}
    .card {{
      background: var(--card-bg);
      border-radius: 12px;
      padding: 1.25rem;
      box-shadow: 0 4px 10px rgba(15, 98, 254, 0.08);
      margin-bottom: 1.5rem;
      border: 1px solid var(--border);
    }}
    .hidden {{ display: none; }}
    .button {{
      text-decoration: none;
      border-radius: 100px;
      padding: 0.55rem 1.2rem;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }}
    .button.secondary {{
      background: rgba(255,255,255,0.2);
      color: #fff;
      border: 1px solid rgba(255,255,255,0.4);
    }}
    .ghost-button {{
      border-radius: 999px;
      border: 1px solid #d0d7e3;
      background: transparent;
      padding: 0.35rem 0.9rem;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      cursor: pointer;
      color: #13294b;
    }}
    .ghost-button:hover {{
      background: #eef4ff;
    }}
    .ghost-button .material-icons,
    .button .material-icons {{
      font-size: 1.1rem;
    }}
    .action-row {{
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-top: 0.5rem;
    }}
    pre {{
      background: #0b1526;
      color: #e8edf4;
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      table-layout: fixed;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 0.4rem 0.6rem;
      text-align: left;
      word-break: break-word;
      white-space: normal;
    }}
    th {{
      background: #eef4ff;
      font-weight: 600;
    }}
    img.responsive {{
      max-width: 100%;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    .status-success {{
      color: #0f9d58;
      font-weight: 600;
    }}
    .status-error {{
      color: #d93025;
      font-weight: 600;
    }}
    .block-meta {{
      color: #5f6c80;
      margin-top: -0.25rem;
      margin-bottom: 0.75rem;
      font-size: 0.95rem;
    }}
    .block-content {{
      margin-top: 0.75rem;
    }}
    .block-content.placeholder {{
      color: #5f6c80;
      font-style: italic;
    }}
    .json-viewer {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 0.75rem;
      background: #0b1526;
      color: #e8edf4;
      overflow-x: auto;
    }}
    .table-widget-note {{
      font-size: 0.85rem;
      color: #5f6c80;
      margin-top: -0.35rem;
    }}
    .table-csv-preview {{
      margin-bottom: 0.75rem;
    }}
    @media (max-width: 600px) {{
      .app-header {{
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
      }}
    }}
  </style>
</head>
<body>
  <header class="app-header">
    <div class="title-group">
      <span class="material-icons">task_alt</span>
      <div>
        <h1 id="page-title">Task Result</h1>
        <p id="meta-line">Loading task metadata…</p>
      </div>
    </div>
    <a class="button secondary" href="{pretty_page_name}" target="_blank" rel="noopener">
      <span class="material-icons" aria-hidden="true">auto_awesome</span>
      Pretty format
    </a>
  </header>
  <main>
    <section id="status-card" class="card" aria-live="polite">Preparing result…</section>
    <section id="summary-card" class="card hidden">
      <h2>Summary</h2>
      <p id="summary-text"></p>
    </section>
    <section id="blocks"></section>
    <section id="attachments-card" class="card hidden">
      <h2>Attachments</h2>
      <div id="attachment-list"></div>
    </section>
  </main>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.3/dist/purify.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/json-formatter-js@2.3.4/dist/json-formatter.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"></script>
  <script>
    const PAYLOAD_URL = '{payload_relative_path}';
    const FILE_BASE_PATH = 'files/';
    const FILE_BASE_URL = new URL(FILE_BASE_PATH, window.location.href).href;
    const assetContentCache = new Map();

    document.addEventListener('DOMContentLoaded', () => {{
      fetchPayload();
    }});

    function createActionButton(label, iconName = 'task_alt') {{
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'ghost-button';
      if (iconName) {{
        const icon = document.createElement('span');
        icon.className = 'material-icons';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = iconName;
        button.appendChild(icon);
      }}
      const textNode = document.createElement('span');
      textNode.textContent = label;
      button.appendChild(textNode);
      button._labelNode = textNode;
      return button;
    }}

    function setButtonLabel(button, label) {{
      const target = button._labelNode || button;
      target.textContent = label;
    }}

    function fileUrl(filename) {{
      if (!filename) {{
        return '';
      }}
      try {{
        return new URL(filename, FILE_BASE_URL).href;
      }} catch (error) {{
        console.error('Unable to build file URL', error);
        return '';
      }}
    }}

    function copyToClipboard(text, button) {{
      if (!navigator.clipboard) {{
        return;
      }}
      navigator.clipboard.writeText(text || '').then(() => {{
        if (button) {{
          const labelNode = button.querySelector('span:nth-child(2)');
          const original = labelNode ? labelNode.textContent : '';
          if (labelNode) {{
            labelNode.textContent = 'Copied';
          }}
          button.disabled = true;
          setTimeout(() => {{
            if (labelNode) {{
              labelNode.textContent = original;
            }}
            button.disabled = false;
          }}, 1500);
        }}
      }}).catch(() => {{}});
    }}

    function downloadTextFile(filename, content, mimeType = 'text/plain') {{
      const blob = new Blob([content || ''], {{ type: mimeType }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 0);
    }}

    function suggestFilename(block, extension) {{
      const base = (block.title || block.type || 'content')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '') || 'content';
      return `${{base}}.${{extension}}`;
    }}

    async function fetchPayload() {{
      const statusCard = document.getElementById('status-card');
      statusCard.textContent = 'Loading result data…';
      try {{
        const response = await fetch(PAYLOAD_URL, {{ cache: 'no-store' }});
        if (!response.ok) {{
          throw new Error(`Failed to load payload: ${{response.status}}`);
        }}
        const payload = await response.json();
        await renderPayload(payload);
        statusCard.textContent = 'Result loaded successfully.';
        statusCard.classList.add('status-success');
      }} catch (error) {{
        console.error(error);
        statusCard.textContent = 'Unable to load result data. Please download the payload JSON directly.';
        statusCard.classList.add('status-error');
        addDownloadButton(document.getElementById('status-card'), 'Download payload', PAYLOAD_URL);
      }}
    }}

    async function renderPayload(payload) {{
      const meta = payload.meta || {{}};
      document.getElementById('page-title').textContent = meta.title || 'Task Result';
      document.getElementById('meta-line').textContent = `Session: ${{meta.session_id || 'n/a'}} · Task: ${{meta.task_id || 'n/a'}}`;

      if (payload.summary) {{
        const summaryCard = document.getElementById('summary-card');
        summaryCard.classList.remove('hidden');
        document.getElementById('summary-text').textContent = payload.summary;
      }}

      const assetMap = Object.fromEntries((payload.assets || []).map(asset => [asset.id, asset]));
      renderBlocks(payload.blocks || [], assetMap);
      renderAttachments(payload.assets || []);
    }}

    function renderBlocks(blocks, assetMap) {{
      const container = document.getElementById('blocks');
      container.innerHTML = '';
      if (!blocks.length) {{
        container.innerHTML = '<div class="card">No content available.</div>';
        return;
      }}
      blocks.forEach((block, index) => {{
        const card = document.createElement('article');
        card.className = 'card';
        const titleEl = document.createElement('h2');
        titleEl.textContent = block.title || `Block ${{index + 1}}`;
        card.appendChild(titleEl);

        const metaEl = document.createElement('p');
        metaEl.className = 'block-meta';
        metaEl.textContent = describeBlockMeta(block, assetMap);
        card.appendChild(metaEl);

        const contentEl = document.createElement('div');
        contentEl.className = 'block-content';
        card.appendChild(contentEl);

        if (block.type === 'file') {{
          contentEl.dataset.renderState = 'done';
          renderFile(block, contentEl, assetMap);
        }} else {{
          const actionRow = document.createElement('div');
          actionRow.className = 'action-row';
          const renderButton = createActionButton('Render block', 'play_arrow');
          actionRow.appendChild(renderButton);
          card.appendChild(actionRow);

          contentEl.classList.add('placeholder');
          contentEl.dataset.renderState = 'idle';
          contentEl.textContent = 'Content not rendered yet.';

          renderButton.addEventListener('click', () => {{
            handleBlockRender(block, contentEl, renderButton, assetMap);
          }});
        }}

        container.appendChild(card);
      }});
    }}

    async function handleBlockRender(block, container, button, assetMap) {{
      const state = container.dataset.renderState || 'idle';
      if (state === 'loading' || state === 'done') {{
        return;
      }}
      container.dataset.renderState = 'loading';
      container.classList.remove('placeholder');
      container.textContent = 'Rendering content…';
      setButtonLabel(button, 'Rendering…');
      button.disabled = true;
      try {{
        container.innerHTML = '';
        await renderBlockContent(block, container, assetMap);
        container.dataset.renderState = 'done';
        setButtonLabel(button, 'Rendered');
      }} catch (error) {{
        console.error(error);
        container.dataset.renderState = 'error';
        container.textContent = 'Unable to render block content.';
        setButtonLabel(button, 'Retry render');
        button.disabled = false;
      }}
    }}

    function describeBlockMeta(block, assetMap) {{
      const pieces = [];
      const blockType = block.type || 'text';
      pieces.push(`Type: ${{blockType}}`);
      if (block.format && blockType === 'text' && block.format !== 'plain') {{
        pieces.push(`Format: ${{block.format}}`);
      }}
      if (block.asset_id) {{
        pieces.push(`File: ${{formatAssetLabel(block.asset_id, assetMap)}}`);
      }}
      if (blockType === 'table') {{
        const rowCount = Array.isArray(block.rows) ? block.rows.length : 0;
        if (rowCount) {{
          pieces.push(`${{rowCount}} preview row${{rowCount === 1 ? '' : 's'}}`);
        }}
        if (block.csv_asset_id) {{
          pieces.push(`CSV: ${{formatAssetLabel(block.csv_asset_id, assetMap)}}`);
        }}
      }}
      if (blockType === 'markdown' && Array.isArray(block.embedded_assets) && block.embedded_assets.length) {{
        pieces.push(`${{block.embedded_assets.length}} embedded asset${{block.embedded_assets.length === 1 ? '' : 's'}}`);
      }}
      return pieces.join(' · ') || 'Block details unavailable';
    }}

    function formatAssetLabel(assetId, assetMap) {{
      if (!assetId) {{
        return 'n/a';
      }}
      const asset = assetMap[assetId];
      if (asset && asset.filename) {{
        return asset.filename;
      }}
      return assetId;
    }}

    async function renderBlockContent(block, container, assetMap) {{
      switch (block.type) {{
        case 'markdown':
          await renderMarkdown(block, container, assetMap);
          break;
        case 'table':
          await renderTable(block, container, assetMap);
          break;
        case 'image':
          renderImage(block, container, assetMap);
          break;
        case 'file':
          renderFile(block, container, assetMap);
          break;
        case 'json':
          await renderJson(block, container, assetMap);
          break;
        default:
          if ((block.format || '').toLowerCase() === 'json') {{
            await renderJson(block, container, assetMap);
          }} else {{
            await renderText(block, container, assetMap);
          }}
      }}
    }}

    async function fetchAssetText(assetId, assetMap) {{
      if (!assetId) {{
        return '';
      }}
      if (assetContentCache.has(assetId)) {{
        return assetContentCache.get(assetId);
      }}
      const asset = assetMap[assetId];
      if (!asset) {{
        throw new Error(`Asset not found for id ${{assetId}}`);
      }}
      const response = await fetch(fileUrl(asset.filename), {{ cache: 'no-store' }});
      if (!response.ok) {{
        throw new Error(`Failed to load asset ${{asset.filename}}: ${{response.status}}`);
      }}
      const text = await response.text();
      assetContentCache.set(assetId, text);
      return text;
    }}

    async function renderMarkdown(block, container, assetMap) {{
      let raw = block.content || '';
      if (block.asset_id) {{
        try {{
          raw = await fetchAssetText(block.asset_id, assetMap);
        }} catch (error) {{
          console.error(error);
          container.textContent = 'Markdown content unavailable.';
          return;
        }}
      }}
      const resolved = resolveAssetPlaceholders(raw, assetMap);
      const html = DOMPurify.sanitize(marked.parse(resolved));
      container.innerHTML = html;
      const actions = document.createElement('div');
      actions.className = 'action-row';
      const copyBtn = createActionButton('Copy', 'content_copy');
      copyBtn.addEventListener('click', () => copyToClipboard(raw, copyBtn));
      const downloadBtn = createActionButton('Download', 'download');
      downloadBtn.addEventListener('click', () => downloadTextFile(suggestFilename(block, 'md'), raw, 'text/markdown'));
      actions.append(copyBtn, downloadBtn);
      container.appendChild(actions);
    }}

    async function renderTable(block, container, assetMap) {{
      const hasColumns = Array.isArray(block.columns) && block.columns.length > 0;
      const csvAsset = block.csv_asset_id ? assetMap[block.csv_asset_id] : null;
      if (block.csv_asset_id && !csvAsset) {{
        const warning = document.createElement('p');
        warning.textContent = 'CSV asset not found.';
        warning.style.color = '#d93025';
        container.appendChild(warning);
      }}
      if (csvAsset) {{
        const previewContainer = document.createElement('div');
        previewContainer.className = 'table-csv-preview';
        container.appendChild(previewContainer);
        await renderCsvPreview(previewContainer, csvAsset);
      }}
      if (hasColumns) {{
        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        block.columns.forEach(column => {{
          const th = document.createElement('th');
          th.textContent = column;
          headerRow.appendChild(th);
        }});
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        (block.rows || []).forEach(row => {{
          const tr = document.createElement('tr');
          row.forEach(cell => {{
            const td = document.createElement('td');
            td.textContent = cell ?? '';
            tr.appendChild(td);
          }});
          tbody.appendChild(tr);
        }});
        table.appendChild(tbody);
        container.appendChild(table);
      }}
      if (!csvAsset && !hasColumns) {{
        container.textContent = 'Table data unavailable.';
      }}
      if (csvAsset) {{
        const buttonWrap = document.createElement('div');
        addDownloadButton(buttonWrap, 'Download CSV', fileUrl(csvAsset.filename));
        container.appendChild(buttonWrap);
      }}
    }}

    function renderImage(block, container, assetMap) {{
      const asset = assetMap[block.asset_id];
      if (!asset) {{
        container.textContent = 'Image not available.';
        return;
      }}
      const img = document.createElement('img');
      img.src = fileUrl(asset.filename);
      img.alt = block.alt_text || block.title || 'Image';
      img.className = 'responsive';
      container.appendChild(img);
      const meta = document.createElement('p');
      meta.textContent = asset.filename;
      meta.style.marginTop = '0.5rem';
      meta.style.color = '#5f6c80';
      container.appendChild(meta);
      addDownloadButton(container, 'Download image', fileUrl(asset.filename));
    }}

    function renderFile(block, container, assetMap) {{
      const asset = assetMap[block.asset_id];
      if (!asset) {{
        container.textContent = 'File not available.';
        return;
      }}
      const name = document.createElement('p');
      name.textContent = asset.filename;
      name.style.marginBottom = '0.35rem';
      container.appendChild(name);
      addDownloadButton(container, block.label || 'Download file', fileUrl(asset.filename));
    }}

    async function renderJson(block, container, assetMap) {{
      let textContent = block.content || '';
      if (block.asset_id) {{
        try {{
          textContent = await fetchAssetText(block.asset_id, assetMap);
        }} catch (error) {{
          console.error(error);
          container.textContent = 'JSON content unavailable.';
          return;
        }}
      }}
      let parsed;
      try {{
        parsed = textContent ? JSON.parse(textContent) : null;
      }} catch (error) {{
        console.error(error);
        container.textContent = 'Invalid JSON data.';
        return;
      }}
      if (window.JSONFormatter) {{
        try {{
          const formatter = new window.JSONFormatter(parsed, 1, {{
            theme: 'dark',
            hoverPreviewEnabled: true,
            hoverPreviewArrayCount: 10,
            hoverPreviewFieldCount: 5
          }});
          const element = formatter.render();
          element.classList.add('json-viewer');
          container.appendChild(element);
        }} catch (error) {{
          console.error('JSONFormatter render failed', error);
          const pre = document.createElement('pre');
          pre.textContent = JSON.stringify(parsed, null, 2);
          container.appendChild(pre);
        }}
      }} else {{
        const pre = document.createElement('pre');
        pre.textContent = JSON.stringify(parsed, null, 2);
        container.appendChild(pre);
      }}
      const actions = document.createElement('div');
      actions.className = 'action-row';
      const copyBtn = createActionButton('Copy JSON', 'content_copy');
      copyBtn.addEventListener('click', () => copyToClipboard(JSON.stringify(parsed, null, 2), copyBtn));
      const downloadBtn = createActionButton('Download JSON', 'download');
      downloadBtn.addEventListener('click', () => downloadTextFile(suggestFilename(block, 'json'), JSON.stringify(parsed, null, 2), 'application/json'));
      actions.append(copyBtn, downloadBtn);
      container.appendChild(actions);
    }}

    async function renderText(block, container, assetMap) {{
      let textContent = block.content || '';
      if (block.asset_id) {{
        try {{
          textContent = await fetchAssetText(block.asset_id, assetMap);
        }} catch (error) {{
          console.error(error);
          container.textContent = 'Text content unavailable.';
          return;
        }}
      }}
      const pre = document.createElement('pre');
      pre.textContent = textContent;
      container.appendChild(pre);
      const actions = document.createElement('div');
      actions.className = 'action-row';
      const copyBtn = createActionButton('Copy', 'content_copy');
      copyBtn.addEventListener('click', () => copyToClipboard(textContent, copyBtn));
      const extension = block.format === 'json' || block.type === 'json' ? 'json' : 'txt';
      const mime = extension === 'json' ? 'application/json' : 'text/plain';
      const downloadBtn = createActionButton('Download', 'download');
      downloadBtn.addEventListener('click', () => downloadTextFile(suggestFilename(block, extension), textContent, mime));
      actions.append(copyBtn, downloadBtn);
      container.appendChild(actions);
    }}

    function renderAttachments(assets) {{
      if (!assets.length) {{
        return;
      }}
      const card = document.getElementById('attachments-card');
      const list = document.getElementById('attachment-list');
      list.innerHTML = '';
      assets.forEach(asset => {{
        const link = document.createElement('a');
        link.href = fileUrl(asset.filename);
        link.download = asset.filename;
        link.className = 'button';
        link.textContent = asset.filename;
        list.appendChild(link);
      }});
      card.classList.remove('hidden');
    }}

    function addDownloadButton(container, label, href) {{
      if (!href) return;
      const button = document.createElement('a');
      button.className = 'button';
      button.href = href;
      button.download = '';
      button.textContent = label;
      container.appendChild(button);
    }}

    function resolveAssetPlaceholders(text, assetMap) {{
      return text.replace(/{{{{ASSET_URL:([^}}]+)}}}}/g, (_, id) => {{
        const asset = assetMap[id.trim()];
        return asset ? fileUrl(asset.filename) : '#';
      }});
    }}

    async function renderCsvPreview(target, asset) {{
      const status = document.createElement('p');
      status.className = 'table-widget-note';
      status.textContent = 'Loading CSV preview…';
      target.appendChild(status);
      if (!window.Papa) {{
        status.textContent = 'CSV preview unavailable (missing parser).';
        return;
      }}
      try {{
        const response = await fetch(fileUrl(asset.filename), {{ cache: 'no-store' }});
        if (!response.ok) {{
          throw new Error(`Failed to fetch CSV: ${{response.status}}`);
        }}
        const csvText = await response.text();
        const parsed = window.Papa.parse(csvText, {{ skipEmptyLines: true }});
        const rows = Array.isArray(parsed.data) ? parsed.data.filter(row => row.some(cell => cell !== null && cell !== undefined && String(cell).trim() !== '')) : [];
        if (!rows.length) {{
          status.textContent = 'CSV file is empty.';
          return;
        }}
        const MAX_ROWS = 200;
        const previewRows = rows.slice(0, MAX_ROWS);
        const columnCount = previewRows.reduce((max, row) => Math.max(max, row.length), 0);
        const table = document.createElement('table');
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        const headerValues = previewRows[0] ?? [];
        for (let i = 0; i < columnCount; i++) {{
          const th = document.createElement('th');
          th.textContent = headerValues[i] ?? `Column ${{i + 1}}`;
          headerRow.appendChild(th);
        }}
        thead.appendChild(headerRow);
        table.appendChild(thead);
        const tbody = document.createElement('tbody');
        previewRows.slice(1).forEach(row => {{
          const tr = document.createElement('tr');
          for (let i = 0; i < columnCount; i++) {{
            const td = document.createElement('td');
            const value = row[i];
            td.textContent = value === undefined || value === null ? '' : String(value);
            tr.appendChild(td);
          }}
          tbody.appendChild(tr);
        }});
        table.appendChild(tbody);
        target.innerHTML = '';
        target.appendChild(table);
        const note = document.createElement('p');
        note.className = 'table-widget-note';
        if (rows.length > MAX_ROWS) {{
          note.textContent = `Showing first ${{MAX_ROWS}} rows of ${{rows.length}}. Download for full data.`;
        }} else {{
          note.textContent = `Showing all ${{rows.length}} rows.`;
        }}
        target.appendChild(note);
      }} catch (error) {{
        console.error('CSV preview failed', error);
        status.textContent = 'Unable to render CSV preview.';
      }}
    }}
  </script>
</body>
</html>"""

    def _write_html_file(self, target: Path, content: str) -> None:
        temp_file = target.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        temp_file.replace(target)

    def _extract_meta_field_keys(self, result_data: Any) -> set[str]:
        if isinstance(result_data, dict):
            meta = result_data.get("meta")
            if isinstance(meta, dict):
                return {str(key) for key in meta.keys() if key}
        return set()

    async def _generate_result_html_with_llm(
        self, 
        delivery_payload: DeliveryPayload, 
        raw_result_data: Any,
        session_id: str, 
        task_id: str,
        payload_file_name: str,
        payload_file_url: str,
        file_download_base_url: str,
    ) -> tuple[str, List[Dict[str, str]]]:
        """Generate HTML page using LLM and identify files/images to serve
        
        Returns:
            Tuple of (html_content, file_mappings)
            where file_mappings is a list of {source: local_path, target: filename}
        """
        
        payload_text = json.dumps(delivery_payload.to_dict(), indent=2, ensure_ascii=False)
        if isinstance(raw_result_data, (dict, list)):
            original_result_text = json.dumps(raw_result_data, indent=2, ensure_ascii=False)
        else:
            original_result_text = str(raw_result_data)
        payload_file_relative_path = f"files/{payload_file_name}"
        
        # Prepare prompt for LLM to generate the HTML page and identify files
        llm_prompt = f"""You are a web page generator for a result delivery system. Generate a complete HTML page with Material Design styling that displays task results to the user.

The canonical delivery payload (meta, summary, blocks, assets) is saved as JSON and served to the browser at:
- Local path: {payload_file_relative_path}
- URL: {payload_file_url}

This HTML will be served as pretty.html. The safe fallback index.html already links here with a "Pretty format" button. Include UI that lets users return to the safe view (../index.html) if desired.

Use client-side JavaScript to fetch the delivery payload JSON and render it. Do NOT embed the raw payload directly in the HTML markup. Provide a loading state while the data is being fetched, display the parsed content once loaded, and show a clear error message if loading fails.

Assets listed in the payload are already copied to files/<filename>. Use those filenames for download links or image sources. Only emit file_mappings if you discover additional local paths not already represented by the payload.

Result Payload:
```
{payload_text}
```

Original Result Data:
```
{original_result_text}
```

Your tasks:
1. Generate a complete HTML page that displays the result data after it is fetched from the JSON file
2. Only if necessary, identify missing file assets and add them to file_mappings

Requirements for HTML generation:
1. Create a complete, valid HTML page with proper DOCTYPE, head, and body
2. Use Material Design styling (include Google Fonts Roboto and Material Icons from CDN)
3. Display the result data in a clear, readable format after the fetch completes:
    - Use appropriate formatting for text, markdown (rendered safely), JSON, or structured data
    - Use syntax highlighting for code/JSON if applicable
    - Make long text content scrollable and have a copy button
    - Include a "Download Payload JSON" button that links to the saved file
4. For any assets referenced, create download buttons/links:
   - Use the URL pattern: {file_download_base_url}{{filename}}
   - Style as Material Design buttons with download icons
5. For any local images, display them inline in the page:
   - Use the URL pattern: {file_download_base_url}{{filename}}
   - Make images responsive and have a download button below
6. Use modern CSS with good UX (responsive, accessible, clean layout)
7. Add a header with a success icon and title "Task Result"
8. Include a chip/button or notice that links back to ../index.html
9. Include accessible labels for dynamic content regions (e.g., aria-live for status messages)
10. For non local image or file, use href link with download button.

Return both the HTML content and the file mappings using the provided tool."""

        # Create tool schema for HTML generation
        tool_schema = self._create_html_generation_tool_schema()

        # Use LLM tool to generate the HTML with tool calls
        llm_params = {
            "prompt": llm_prompt,
            "temperature": 0.0,
            "tools": [tool_schema]
        }
        llm_result = await self.llm_tool.execute(llm_params,
                                                    validators=[lambda x: self._extract_html_from_response(x)],
                                                    max_retries=self.max_generation_attempts - 1,
                                                    retry_strategies=[
                                                    AppendValidationHintStrategy(),
                                                ],
                                                retry_llm_tool=self.llm_tool)


        # Extract HTML and file mappings from tool call response
        return self._extract_html_from_response(llm_result)
    
    def _create_html_generation_tool_schema(self) -> Dict[str, Any]:
        """Create tool schema for HTML result page generation with file mapping
        
        Returns:
            Tool schema dictionary for use with LLMTool
        """
        tool_schema = {
            "type": "function",
            "function": {
                "name": "generate_html_result_page",
                "description": "Generate complete HTML result page for task result delivery and identify files to serve",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "html_content": {
                            "type": "string",
                            "description": "Complete HTML page content with proper DOCTYPE, styling and result display"
                        },
                        "file_mappings": {
                            "type": "array",
                            "description": "List of files/images that need to be copied from local paths to the serving directory",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "source": {
                                        "type": "string",
                                        "description": "Local file path as it appears in result_data (absolute or relative path)"
                                    },
                                    "target": {
                                        "type": "string",
                                        "description": "Target filename to use when serving (just filename, not path). This should match the filename used in HTML links/images."
                                    },
                                    "type": {
                                        "type": "string",
                                        "enum": ["file", "image"],
                                        "description": "Type of the file (for reference)"
                                    }
                                },
                                "required": ["source", "target", "type"]
                            }
                        }
                    },
                    "required": ["html_content", "file_mappings"]
                }
            }
        }
        
        return tool_schema

    def _extract_html_from_response(self, response) -> tuple[str, List[Dict[str, str]]]:
        """Extract HTML content and file mappings from LLM response with tool calls
        
        Args:
            response: LLM response containing tool calls
            
        Returns:
            Tuple of (html_content, file_mappings)
        """            
        # Extract tool calls from response
        if not isinstance(response, dict):
            raise ValueError("No tool calls found in LLM response")

        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            raise ValueError("No tool calls found in LLM response")
        
        # Get the first (and should be only) tool call
        tool_call = tool_calls[0]
        if tool_call.get("name") != "generate_html_result_page":
            raise ValueError(f"Unexpected tool call: {tool_call.get('name')}")
        
        # Extract arguments
        arguments = tool_call.get("arguments", {})
        html_content = arguments.get("html_content", "")
        file_mappings = arguments.get("file_mappings", [])
        
        if not html_content:
            raise ValueError("No HTML content generated by LLM")
        
        print(f"[WEB_RESULT_DELIVERY] LLM identified {len(file_mappings)} files to serve")
        for mapping in file_mappings:
            print(f"[WEB_RESULT_DELIVERY]   {mapping.get('type', 'file')}: {mapping.get('source')} -> {mapping.get('target')}")
            
        return html_content, file_mappings

    def get_result_validation_hint(self) -> str:
        return "This step doesn't need validation as it generates a web page for user viewing."
