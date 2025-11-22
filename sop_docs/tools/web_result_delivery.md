---
description: Use to deliver task results to users through dynamically generated web pages. The LLM will create an appropriate result page based on the content type (text, JSON, files, images). If some file needs to be delivered, needs to provide the file path on local disk and the delivery tool create a download link on the webpage. If some content needs to be previewed, the tool will create proper rendering blocks.
tool:
  tool_id: WEB_RESULT_DELIVERY
input_description:
  result_data: >
    Delivery payload dict describing exactly what should be rendered. Based on the file extension to determine how to render the content. Supported content types include text, markdown, table (CSV), image (PNG, JPG), JSON, and generic files. See output description for schema details.
    The object must follow this schema:
      {
        "version": "1.0",
        "summary": "optional summary text",
        "blocks": [
          {
            "type": "text" | "markdown" | "table" | "image" | "file" | "json",
            "...": "block-specific fields"
          }
        ],
        "assets": [
          {
            "id": "asset identifier referenced by blocks",
            "source_path": "/abs/path/to/local/file",
            "filename": "file name exposed to the browser",
            "asset_type": "file|image|csv",
            "mime_type": "optional mime type",
            "description": "optional description"
          }
        ]
      }
    All file/image/table assets must be declared under `assets` with valid source paths so the delivery tool can copy them before rendering.  Any payload that does not match this schema will cause the tool to fail.
    Block-specific expectations:
      - `text` / `json` / `code` blocks (set `format` to control rendering):
        * Required: either `content` (string) or `asset_id` (string). When `asset_id` is provided, point at a text file asset (`asset_type: "file"`) that the frontend can download and render.
        * Optional: `format` (`plain`|`markdown`|`code`|`json`) and `description`.
      - `markdown` blocks:
        * Required: either inline `content` or an `asset_id` referencing a markdown file asset. The asset contents will be fetched at runtime, so no need to inline long markdown.
        * Optional: `embedded_assets` array for placeholder substitutions, plus `description`.
      - `table` blocks:
        * Required: either (a) `columns` (list of header strings) plus representative `rows`, or (b) a `csv_asset_id` referencing an uploaded CSV asset.
        * Optional: `csv_asset_id` when inline data is present to offer a download, and `preview_rows` describing how many inline rows to render. When only `csv_asset_id` is provided the UI streams the CSV into a hosted Grist table widget for full exploration, so inline rows are not necessary.
      - `image` blocks:
        * Required: `asset_id` referencing an image asset (`asset_type: "image"`).
        * Optional: `alt_text`, `title`, and `description`.
      - `file` blocks:
        * Required: `asset_id` referencing a downloadable asset.
        * Optional: `label` to customize the download button text plus `title`/`description`.
        * These blocks render immediately (no "Render block" button) because the UI only needs to show download links.
      - Any `asset_id` you reference must exist in the `assets` array with a unique `id`, the correct `asset_type`, the file already present at `source_path`, and a user-facing `filename`.
      - Blocks render lazily in the UI: users initially see the title, type, and referenced filenames plus a **Render block** button. Provide meaningful titles/descriptions so users can decide which blocks to expand, and ensure referenced assets remain available when the button is pressed.
output_description: JSON object containing the result URL where user can view the results, status ("ok"), and `file_included_in_html` (list of file paths on disk that were included in the generated page, including the JSON payload and any attachments).
skip_new_task_generation: true
---
