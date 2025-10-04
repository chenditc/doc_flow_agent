/**
 * SOP Document Editor Component
 * Main editor interface with metadata form and markdown editor
 */

import React, { useState, useEffect } from 'react';
import type { SopDoc, SopDocMeta } from '../../types';
import { MetadataForm } from './MetadataForm';
import { MarkdownEditor } from './MarkdownEditor';
import './SopDocEditor.css';

interface SopDocEditorProps {
  doc: SopDoc;
  onSave: (doc: SopDoc) => Promise<boolean>;
  onDelete: (path: string) => Promise<boolean>;
  onCopy: (sourcePath: string, targetPath: string, overrideDocId: boolean) => Promise<boolean>;
  onCreate: (path: string, meta: SopDocMeta, body: string) => Promise<boolean>;
}

export const SopDocEditor: React.FC<SopDocEditorProps> = ({
  doc,
  onSave,
  onDelete,
  onCopy,
}) => {
  const [editedMeta, setEditedMeta] = useState<SopDocMeta>(doc.meta);
  const [editedBody, setEditedBody] = useState<string>(doc.body_markdown);
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCopyDialog, setShowCopyDialog] = useState(false);

  // Reset state when document changes
  useEffect(() => {
    setEditedMeta(doc.meta);
    setEditedBody(doc.body_markdown);
    setIsDirty(false);
  }, [doc]);

  // Track changes
  useEffect(() => {
    const metaChanged = JSON.stringify(editedMeta) !== JSON.stringify(doc.meta);
    const bodyChanged = editedBody !== doc.body_markdown;
    setIsDirty(metaChanged || bodyChanged);
  }, [editedMeta, editedBody, doc]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const success = await onSave({
        ...doc,
        meta: editedMeta,
        body_markdown: editedBody,
      });
      
      if (success) {
        setIsDirty(false);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleRevert = () => {
    setEditedMeta(doc.meta);
    setEditedBody(doc.body_markdown);
    setIsDirty(false);
  };

  const handleDelete = async () => {
    await onDelete(doc.path);
  };

  return (
    <div className="sop-doc-editor">
      <div className="editor-header">
        <div className="editor-title">
          <h2>{doc.path}</h2>
          {isDirty && <span className="dirty-indicator">● Unsaved changes</span>}
        </div>
        <div className="editor-actions">
          <button
            className="btn-secondary"
            onClick={() => setShowCopyDialog(true)}
          >
            Copy
          </button>
          <button
            className="btn-danger"
            onClick={handleDelete}
          >
            Delete
          </button>
          <button
            className="btn-secondary"
            onClick={handleRevert}
            disabled={!isDirty}
          >
            Revert
          </button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={!isDirty || saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      <div className="editor-content">
        <div className="editor-section">
          <h3>Metadata</h3>
          <MetadataForm
            meta={editedMeta}
            onChange={setEditedMeta}
          />
        </div>

        <div className="editor-section">
          <h3>Document Body</h3>
          <MarkdownEditor
            value={editedBody}
            onChange={setEditedBody}
            sections={doc.sections}
          />
        </div>
      </div>

      {showCopyDialog && (
        <CopyDialog
          sourcePath={doc.path}
          onCopy={onCopy}
          onClose={() => setShowCopyDialog(false)}
        />
      )}
    </div>
  );
};

// Simple copy dialog component
interface CopyDialogProps {
  sourcePath: string;
  onCopy: (sourcePath: string, targetPath: string, overrideDocId: boolean) => Promise<boolean>;
  onClose: () => void;
}

const CopyDialog: React.FC<CopyDialogProps> = ({ sourcePath, onCopy, onClose }) => {
  const [targetPath, setTargetPath] = useState(`${sourcePath}_copy`);
  const [overrideDocId, setOverrideDocId] = useState(true);
  const [copying, setCopying] = useState(false);

  const handleCopy = async () => {
    setCopying(true);
    try {
      const success = await onCopy(sourcePath, targetPath, overrideDocId);
      if (success) {
        onClose();
      }
    } finally {
      setCopying(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>Copy Document</h3>
        <div className="form-group">
          <label>Source:</label>
          <input type="text" value={sourcePath} disabled />
        </div>
        <div className="form-group">
          <label>Target path:</label>
          <input
            type="text"
            value={targetPath}
            onChange={(e) => setTargetPath(e.target.value)}
            placeholder="path/to/new/document"
          />
        </div>
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={overrideDocId}
              onChange={(e) => setOverrideDocId(e.target.checked)}
            />
            Update doc_id to match new path
          </label>
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} disabled={copying}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleCopy} disabled={copying || !targetPath}>
            {copying ? 'Copying...' : 'Copy'}
          </button>
        </div>
      </div>
    </div>
  );
};
