/**
 * Markdown Editor Component
 * Simple textarea with preview toggle for editing document body
 */

import React, { useState, useMemo } from 'react';
import './MarkdownEditor.css';

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  sections: Record<string, string>;
}

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  value,
  onChange,
}) => {
  const [showPreview, setShowPreview] = useState(false);

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

    return html;
  };

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
        <div
          className="editor-preview"
          dangerouslySetInnerHTML={{ __html: renderPreview(value) }}
        />
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
