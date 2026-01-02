/**
 * Vector Search Panel for SOP Docs
 * Allows searching SOP docs via the backend vector store.
 */

import React, { useMemo, useState } from 'react';
import { sopDocsService } from '../../services';
import type { VectorSearchResponse } from '../../types';
import './VectorSearchPanel.css';

interface VectorSearchPanelProps {
  onSelectDoc: (path: string) => void;
}

export const VectorSearchPanel: React.FC<VectorSearchPanelProps> = ({ onSelectDoc }) => {
  const [query, setQuery] = useState('');
  const [k, setK] = useState<number>(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<VectorSearchResponse | null>(null);

  const canSearch = useMemo(() => query.trim().length > 0 && !loading, [query, loading]);

  const handleSearch = async () => {
    const q = query.trim();
    if (!q) {
      setError('Task description cannot be empty.');
      setResponse(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await sopDocsService.vectorSearch(q, k);
      setResponse(res);
    } catch (e: any) {
      setResponse(null);
      setError(e?.message || 'Vector search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="vector-search-panel">
      <div className="vector-search-field">
        <label className="vector-search-label" htmlFor="vectorSearchQuery">
          Task description
        </label>
        <textarea
          id="vectorSearchQuery"
          className="vector-search-textarea"
          placeholder="Paste a long task description to search SOP docs via vector similarity..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={6}
        />
      </div>

      <div className="vector-search-controls">
        <div className="vector-search-k">
          <label className="vector-search-label" htmlFor="vectorSearchK">
            Top K
          </label>
          <input
            id="vectorSearchK"
            type="number"
            min={1}
            max={20}
            value={k}
            onChange={(e) => setK(Number(e.target.value))}
            className="vector-search-k-input"
          />
        </div>

        <button className="vector-search-button" onClick={handleSearch} disabled={!canSearch}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {error && <div className="vector-search-error">{error}</div>}

      {response && (
        <div className="vector-search-results">
          <div className="vector-search-results-header">
            {response.total} result{response.total !== 1 ? 's' : ''}
          </div>

          {response.total === 0 ? (
            <div className="vector-search-empty">No matching document</div>
          ) : (
            <div className="vector-search-results-list">
              {response.results.map((r) => (
                <button
                  key={`${r.doc_id}:${r.score}`}
                  className="vector-search-result"
                  onClick={() => onSelectDoc(r.doc_id)}
                  title="Open SOP doc"
                >
                  <div className="vector-search-result-main">
                    <div className="vector-search-result-doc">{r.doc_id}</div>
                    <div className="vector-search-result-score">{Number(r.score).toFixed(4)}</div>
                  </div>
                  <div className="vector-search-result-meta">
                    {r.tool_id ? <span className="vector-search-pill">tool: {r.tool_id}</span> : null}
                    {r.used_doc_id_fallback ? (
                      <span className="vector-search-pill">used doc_id fallback</span>
                    ) : null}
                  </div>
                  {r.embedded_text ? (
                    <div className="vector-search-result-preview">{r.embedded_text}</div>
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

