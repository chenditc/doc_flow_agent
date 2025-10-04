/**
 * Search Bar Component for SOP Documents
 */

import React, { useState, useEffect, useRef } from 'react';
import type { SearchResponse } from '../../types';
import './SearchBar.css';

interface SearchBarProps {
  onSearch: (query: string) => void;
  onClear: () => void;
  searchResults?: SearchResponse | null;
  onSelectResult?: (path: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  onClear,
  searchResults,
  onSelectResult,
}) => {
  const [query, setQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);

  // Debounce search
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    if (query.trim()) {
      debounceTimer.current = setTimeout(() => {
        onSearch(query);
      }, 300);
    } else {
      onClear();
    }

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [query, onSearch, onClear]);

  const handleClear = () => {
    setQuery('');
    setShowResults(false);
    onClear();
  };

  const handleSelectResult = (path: string) => {
    setShowResults(false);
    onSelectResult?.(path);
  };

  return (
    <div className="search-bar-container">
      <div className="search-bar">
        <input
          type="text"
          className="search-input"
          placeholder="Search documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setShowResults(true)}
        />
        {query && (
          <button className="search-clear" onClick={handleClear}>
            ✕
          </button>
        )}
      </div>

      {showResults && searchResults && searchResults.results.length > 0 && (
        <div className="search-results-dropdown">
          <div className="search-results-header">
            {searchResults.total} result{searchResults.total !== 1 ? 's' : ''}
          </div>
          <div className="search-results-list">
            {searchResults.results.map((result) => (
              <div
                key={result.path}
                className="search-result-item"
                onClick={() => handleSelectResult(result.path)}
              >
                <div className="search-result-path">{result.path}</div>
                <div className="search-result-matches">
                  {result.matches.slice(0, 5).map((match, idx) => (
                    <div key={idx} className="search-result-match">
                      {match.line > 0 ? (
                        <span className="match-line">Line {match.line}:</span>
                      ) : (
                        <span className="match-line match-path-indicator">📁</span>
                      )}
                      <span className="match-preview">{match.preview}</span>
                    </div>
                  ))}
                  {result.matches.length > 5 && (
                    <div className="search-result-more">
                      +{result.matches.length - 5} more match{result.matches.length - 5 !== 1 ? 'es' : ''}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
