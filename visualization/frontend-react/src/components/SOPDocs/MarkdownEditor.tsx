/**
 * Markdown Editor Component
 * Simple textarea with preview toggle for editing document body
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { sopDocsService } from '../../services';
import type { SopDocMetaSummary } from '../../types';
import './MarkdownEditor.css';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  sections: Record<string, string>;
  allMetaSummaries: SopDocMetaSummary[]; // list of all docs for reference highlighting
}

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
  allMetaSummaries,
}) => {
  const [showPreview, setShowPreview] = useState(false);
  const previewRef = useRef<HTMLDivElement | null>(null);
  const [modal, setModal] = useState<{open: boolean; content: string; docPath?: string; loading: boolean}>({open: false, content: '', loading: false});
  const docCache = useRef<Record<string, string>>({}); // raw body cache

  // Extract section names from current body
  const currentSections = useMemo(() => {
    const pattern = /^## (.+?)$/gm;
    const matches = [...value.matchAll(pattern)];
    return matches.map((m) => m[1]);
  }, [value]);

  const insertSection = () => {
    const sectionName = prompt('Section name (e.g., parameters.prompt):');
    if (sectionName) {
      const newSection = `\n## ${sectionName}\n\nContent goes here...\n`;
      onChange(value + newSection);
    }
  };

  // Simple markdown-to-HTML for preview (basic implementation)
  const highlightContent = (html: string) => {
    if (!allMetaSummaries || allMetaSummaries.length === 0) return html;

    const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    // Collect tokens
    const tokenInfos: { token: string; path: string }[] = [];
    for (const meta of allMetaSummaries) {
      const basePath = meta.path;
      if (basePath) tokenInfos.push({ token: basePath, path: basePath });
      if (meta.doc_id && meta.doc_id !== basePath) tokenInfos.push({ token: meta.doc_id, path: basePath });
      const filenameStem = meta.raw_filename?.endsWith('.md') ? meta.raw_filename.slice(0, -3) : meta.raw_filename;
      if (filenameStem && filenameStem !== basePath) tokenInfos.push({ token: filenameStem, path: basePath });
      if (meta.aliases) meta.aliases.forEach(a => a && tokenInfos.push({ token: a, path: basePath }));
    }

    // Deduplicate by token keeping first path association
    const seen = new Set<string>();
    const tokensOrdered: { token: string; path: string }[] = [];
    for (const info of tokenInfos.sort((a,b)=> b.token.length - a.token.length)) {
      if (!seen.has(info.token)) { seen.add(info.token); tokensOrdered.push(info); }
    }

    let result = html;
    for (const { token, path } of tokensOrdered) {
      if (!/[A-Za-z0-9]/.test(token)) continue;
      // Use word boundaries unless token has '/' which breaks word boundary semantics
      const hasSlash = token.includes('/');
      const boundaryWrapped = hasSlash ? escapeRegExp(token) : `\\b${escapeRegExp(token)}\\b`;
      const regex = new RegExp(boundaryWrapped, 'g');
      result = result.replace(regex, (match) => {
        // Avoid wrapping if already inside a sop-ref span
        // Quick heuristic: if preceding 30 chars contain 'sop-ref"', skip
        const preceding = result.slice(Math.max(0, result.indexOf(match) - 30), result.indexOf(match));
        if (preceding.includes('sop-ref"')) return match;
        return `<span class="sop-ref" data-doc-path="${path}">${match}</span>`;
      });
    }
    return result;
  };

  const renderPreview = (markdown: string) => {
    let html = markdown;

    // Headers
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]+?)```/g, '<pre><code>$2</code></pre>');

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    // Highlight SOP doc references
    html = highlightContent(html);
    return html;
  };

  // Click logic for popup showing raw document body; closes on outside click
  useEffect(() => {
    if (!showPreview) return;
    const el = previewRef.current;
    if (!el) return;

    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target && target.classList.contains('sop-ref')) {
        const docPath = target.getAttribute('data-doc-path');
        if (!docPath) return;
        const openModal = (content: string, loading=false) => setModal({ open: true, content, docPath, loading });
        if (docCache.current[docPath]) {
          openModal(docCache.current[docPath]);
        } else {
          openModal('Loading...', true);
          sopDocsService.getRaw(docPath)
            .then(raw => {
              if (raw && raw.content) {
                docCache.current[docPath] = raw.content;
                openModal(raw.content, false);
              } else {
                openModal('Failed to load document', false);
              }
            })
            .catch(() => openModal('Error loading document', false));
        }
      } else {
        // Outside any sop-ref span -> close modal if open
        if (modal.open) setModal(m => ({ ...m, open: false }));
      }
    };

    document.addEventListener('click', handleClick);
    return () => {
      document.removeEventListener('click', handleClick);
    };
  }, [showPreview, allMetaSummaries, modal.open]);

  return (
    <div className="markdown-editor">
      <div className="editor-toolbar">
        <div className="toolbar-left">
          <button
            className={`toolbar-btn ${!showPreview ? 'active' : ''}`}
            onClick={() => setShowPreview(false)}
          >
            Edit
          </button>
          <button
            className={`toolbar-btn ${showPreview ? 'active' : ''}`}
            onClick={() => setShowPreview(true)}
          >
            Preview
          </button>
        </div>
        <div className="toolbar-right">
          <button className="toolbar-btn" onClick={insertSection}>
            + Insert Section
          </button>
        </div>
      </div>

      <div className="editor-sections-list">
        <strong>Sections:</strong>{' '}
        {currentSections.length > 0 ? (
          currentSections.map((section, idx) => (
            <span key={idx} className="section-tag">
              {section}
            </span>
          ))
        ) : (
          <span className="no-sections">No sections defined</span>
        )}
      </div>

      {showPreview ? (
        <div style={{ position: 'relative' }}>
          <div
            ref={previewRef}
            className="editor-preview"
            dangerouslySetInnerHTML={{ __html: renderPreview(value) }}
          />
          {modal.open && (
            <div className="sop-ref-modal-overlay">
              <div className="sop-ref-modal" role="dialog" aria-modal="true">
                <div className="sop-ref-modal-header">
                  <span>{modal.docPath}</span>
                  <button className="sop-ref-modal-close" onClick={() => setModal(m => ({...m, open: false}))}>✕</button>
                </div>
                <div className="sop-ref-modal-body">
                  <pre><code>{modal.content}</code></pre>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <textarea
          className="editor-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="## parameters.prompt&#10;&#10;Your markdown content here..."
          spellCheck={false}
        />
      )}
    </div>
  );
};
