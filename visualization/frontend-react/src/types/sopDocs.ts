/**
 * Type definitions for SOP Document Management
 */

export interface SopDocMeta {
  doc_id?: string;
  description: string;
  aliases: string[];
  tool: {
    tool_id: string;
    parameters?: Record<string, any>;
  };
  input_json_path?: Record<string, string>;
  output_json_path?: string;
  input_description?: Record<string, string>;
  output_description?: string;
  result_validation_rule?: string;
}

export interface SopDoc {
  path: string;
  raw_filename: string;
  meta: SopDocMeta;
  sections: Record<string, string>;
  body_markdown: string;
  hash: string;
}

export interface TreeNode {
  name: string;
  path: string;
  type: 'dir' | 'file';
  doc: boolean;
  children?: TreeNode[];
}

export interface SearchMatch {
  line: number;
  preview: string;
  kind: 'yaml' | 'body';
}

export interface SearchResult {
  path: string;
  matches: SearchMatch[];
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface VectorSearchRequest {
  query: string;
  k?: number;
}

export interface VectorSearchResultItem {
  doc_id: string;
  score: number;
  embedded_text: string;
  tool_id?: string | null;
  used_doc_id_fallback: boolean;
  used_query: string;
}

export interface VectorSearchResponse {
  query: string;
  results: VectorSearchResultItem[];
  total: number;
}

export interface ValidationIssue {
  field: string;
  severity: 'error' | 'warning';
  message: string;
}

export interface ValidationResponse {
  valid: boolean;
  issues: ValidationIssue[];
  warnings: ValidationIssue[];
}

export interface SopDocUpdateRequest {
  meta: SopDocMeta;
  body_markdown: string;
}

export interface CopyRequest {
  source_path: string;
  target_path: string;
  override_doc_id: boolean;
}

export interface SopDocMetaSummary {
  path: string; // path without .md extension
  raw_filename: string; // filename with .md extension
  doc_id?: string;
  description?: string;
  aliases: string[];
}

export interface SopDocMetaSummary {
  path: string; // path without .md extension
  raw_filename: string; // filename with extension
  doc_id?: string;
  description?: string;
  aliases: string[];
}
