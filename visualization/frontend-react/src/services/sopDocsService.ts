/**
 * SOP Documents API Service
 */

import { apiClient } from './api';
import type {
  TreeNode,
  SopDoc,
  SearchResponse,
  ValidationResponse,
  SopDocUpdateRequest,
  CopyRequest,
} from '../types/sopDocs';

export class SopDocsService {
  /**
   * Get directory tree of SOP documents
   */
  async getTree(refresh: boolean = false): Promise<TreeNode[]> {
    const url = `/api/sop-docs/tree${refresh ? '?refresh=true' : ''}`;
    return apiClient.get<TreeNode[]>(url);
  }

  /**
   * Get a specific SOP document
   */
  async getDoc(docPath: string): Promise<SopDoc> {
    // Ensure no leading slash
    const cleanPath = docPath.startsWith('/') ? docPath.slice(1) : docPath;
    return apiClient.get<SopDoc>(`/api/sop-docs/doc/${cleanPath}`);
  }

  /**
   * Search SOP documents
   */
  async search(query: string): Promise<SearchResponse> {
    return apiClient.get<SearchResponse>(`/api/sop-docs/search?q=${encodeURIComponent(query)}`);
  }

  /**
   * Get metadata summaries for all SOP docs (doc_id, aliases, description, path, filename)
   * Used for client-side reference highlighting.
   */
  async getAllMetadata(): Promise<import('../types').SopDocMetaSummary[]> {
    return apiClient.get<import('../types').SopDocMetaSummary[]>(`/api/sop-docs/meta/all`);
  }

  /**
   * Validate a SOP document without saving
   */
  async validate(request: SopDocUpdateRequest): Promise<ValidationResponse> {
    return apiClient.post<ValidationResponse>('/api/sop-docs/validate', request);
  }

  /**
   * Create a new SOP document
   */
  async create(docPath: string, request: SopDocUpdateRequest): Promise<SopDoc> {
    const cleanPath = docPath.startsWith('/') ? docPath.slice(1) : docPath;
    return apiClient.post<SopDoc>(`/api/sop-docs/create?doc_path=${encodeURIComponent(cleanPath)}`, request);
  }

  /**
   * Update an existing SOP document
   */
  async update(docPath: string, request: SopDocUpdateRequest, hash?: string): Promise<SopDoc> {
    const cleanPath = docPath.startsWith('/') ? docPath.slice(1) : docPath;
    const headers: Record<string, string> = {};
    if (hash) {
      headers['If-Match'] = hash;
    }
    
    return apiClient.put<SopDoc>(
      `/api/sop-docs/doc/${cleanPath}`,
      request
    );
  }

  /**
   * Copy a SOP document
   */
  async copy(request: CopyRequest): Promise<SopDoc> {
    return apiClient.post<SopDoc>('/api/sop-docs/copy', request);
  }

  /**
   * Get full raw content (YAML + body) of a document
   */
  async getRaw(docPath: string): Promise<{ path: string; raw_filename: string; content: string }> {
    const cleanPath = docPath.startsWith('/') ? docPath.slice(1) : docPath;
    return apiClient.get<{ path: string; raw_filename: string; content: string }>(`/api/sop-docs/raw/${cleanPath}`);
  }

  /**
   * Delete a SOP document
   */
  async delete(docPath: string): Promise<{ success: boolean; message: string }> {
    const cleanPath = docPath.startsWith('/') ? docPath.slice(1) : docPath;
    return apiClient.delete<{ success: boolean; message: string }>(`/api/sop-docs/doc/${cleanPath}`);
  }
}

// Export singleton instance
export const sopDocsService = new SopDocsService();
