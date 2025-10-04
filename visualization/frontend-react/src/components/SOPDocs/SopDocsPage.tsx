/**
 * SOP Documents Management Page
 * Provides a UI for viewing, editing, and managing SOP documents
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { sopDocsService } from '../../services';
import type { TreeNode, SopDoc, SearchResponse } from '../../types';
import { SopDocTree } from './SopDocTree';
import { SopDocEditor } from './SopDocEditor';
import { SearchBar } from './SearchBar';
import { LoadingSpinner } from '../common/LoadingSpinner';
import './SopDocsPage.css';

export const SopDocsPage: React.FC = () => {
  const { '*': docPath } = useParams<{ '*': string }>();
  const navigate = useNavigate();

  const [tree, setTree] = useState<TreeNode[]>([]);
  const [currentDoc, setCurrentDoc] = useState<SopDoc | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [treeLoading, setTreeLoading] = useState(false);
  const [docLoading, setDocLoading] = useState(false);

  // Load tree on mount
  useEffect(() => {
    loadTree();
  }, []);

  // Load document when path changes
  useEffect(() => {
    if (docPath) {
      loadDocument(docPath);
    } else {
      setCurrentDoc(null);
    }
  }, [docPath]);

  const loadTree = async (refresh: boolean = false) => {
    try {
      setTreeLoading(true);
      const treeData = await sopDocsService.getTree(refresh);
      setTree(treeData);
      setError(null);
    } catch (err) {
      console.error('Error loading tree:', err);
      setError('Failed to load document tree');
    } finally {
      setTreeLoading(false);
      setLoading(false);
    }
  };

  const loadDocument = async (path: string) => {
    try {
      setDocLoading(true);
      setError(null);
      const doc = await sopDocsService.getDoc(path);
      setCurrentDoc(doc);
    } catch (err: any) {
      console.error('Error loading document:', err);
      if (err?.status === 404) {
        setError(`Document not found: ${path}`);
      } else {
        setError('Failed to load document');
      }
      setCurrentDoc(null);
    } finally {
      setDocLoading(false);
    }
  };

  const handleSelectDoc = (path: string) => {
    navigate(`/sop-docs/${path}`);
  };

  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }

    try {
      const results = await sopDocsService.search(query);
      setSearchResults(results);
    } catch (err) {
      console.error('Error searching:', err);
      setError('Search failed');
    }
  };

  const handleClearSearch = () => {
    setSearchResults(null);
  };

  const handleSave = async (doc: SopDoc) => {
    try {
      setError(null);
      await sopDocsService.update(
        doc.path,
        {
          meta: doc.meta,
          body_markdown: doc.body_markdown,
        },
        doc.hash
      );
      
      // Reload the document to get updated hash
      await loadDocument(doc.path);
      
      // Refresh tree in case doc_id changed
      await loadTree(true);
      
      return true;
    } catch (err: any) {
      console.error('Error saving document:', err);
      if (err?.status === 409) {
        setError('Document was modified by another user. Please refresh and try again.');
      } else {
        setError('Failed to save document');
      }
      return false;
    }
  };

  const handleCreate = async (path: string, meta: any, body: string) => {
    try {
      setError(null);
      await sopDocsService.create(path, {
        meta,
        body_markdown: body,
      });
      
      // Refresh tree and navigate to new doc
      await loadTree(true);
      navigate(`/sop-docs/${path}`);
      
      return true;
    } catch (err: any) {
      console.error('Error creating document:', err);
      if (err?.status === 409) {
        setError('Document already exists at that path');
      } else {
        setError('Failed to create document');
      }
      return false;
    }
  };

  const handleCopy = async (sourcePath: string, targetPath: string, overrideDocId: boolean) => {
    try {
      setError(null);
      await sopDocsService.copy({
        source_path: sourcePath,
        target_path: targetPath,
        override_doc_id: overrideDocId,
      });
      
      // Refresh tree and navigate to copied doc
      await loadTree(true);
      navigate(`/sop-docs/${targetPath}`);
      
      return true;
    } catch (err: any) {
      console.error('Error copying document:', err);
      if (err?.status === 409) {
        setError('Target path already exists');
      } else {
        setError('Failed to copy document');
      }
      return false;
    }
  };

  const handleDelete = async (path: string) => {
    if (!confirm(`Are you sure you want to delete ${path}?`)) {
      return false;
    }

    try {
      setError(null);
      await sopDocsService.delete(path);
      
      // Refresh tree and clear current doc if it was deleted
      await loadTree(true);
      if (currentDoc?.path === path) {
        setCurrentDoc(null);
        navigate('/sop-docs');
      }
      
      return true;
    } catch (err) {
      console.error('Error deleting document:', err);
      setError('Failed to delete document');
      return false;
    }
  };

  if (loading) {
    return (
      <div className="sop-docs-page">
        <LoadingSpinner message="Loading SOP documents..." />
      </div>
    );
  }

  return (
    <div className="sop-docs-page">
      <div className="sop-docs-sidebar">
        <div className="sop-docs-sidebar-header">
          <h2>SOP Documents</h2>
          <button 
            className="btn-refresh" 
            onClick={() => loadTree(true)}
            disabled={treeLoading}
            title="Refresh tree"
          >
            ↻
          </button>
        </div>
        
        <SearchBar
          onSearch={handleSearch}
          onClear={handleClearSearch}
          searchResults={searchResults}
          onSelectResult={handleSelectDoc}
        />

        <SopDocTree
          tree={tree}
          selectedPath={docPath}
          onSelectDoc={handleSelectDoc}
          searchResults={searchResults}
          loading={treeLoading}
        />
      </div>

      <div className="sop-docs-main">
        {error && (
          <div style={{ padding: '16px', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '4px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{error}</span>
              <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '18px' }}>✕</button>
            </div>
          </div>
        )}

        {docLoading ? (
          <LoadingSpinner message="Loading document..." />
        ) : currentDoc ? (
          <SopDocEditor
            doc={currentDoc}
            onSave={handleSave}
            onDelete={handleDelete}
            onCopy={handleCopy}
            onCreate={handleCreate}
          />
        ) : docPath ? (
          <div className="sop-docs-empty">
            <p>Document not found: {docPath}</p>
          </div>
        ) : (
          <div className="sop-docs-welcome">
            <h1>Welcome to SOP Document Management</h1>
            <p>Select a document from the tree to view and edit it.</p>
            <p>Or search for documents using the search bar above.</p>
          </div>
        )}
      </div>
    </div>
  );
};
