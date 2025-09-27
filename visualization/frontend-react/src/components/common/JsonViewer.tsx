import React, { useState } from 'react';
import { Box, IconButton, Typography, Collapse } from '@mui/material';

/**
 * Minimal JSON viewer component to avoid pulling @textea/json-viewer (peer dep mismatch with React 19 / MUI 7)
 * Features:
 *  - Pretty-print JSON with indentation
 *  - Collapsible root (optional)
 *  - Syntax highlighting for basic types via spans + data-type attributes for theming
 */
export interface SimpleJsonViewerProps {
  value: unknown;
  collapsed?: boolean;
  maxHeight?: number | string;
  fontSize?: number | string;
  label?: string;
}

function renderValue(val: unknown, depth = 0): React.ReactNode {
  const indent = '  '.repeat(depth);
  if (val === null) return <span data-type="null">null</span>;
  switch (typeof val) {
    case 'number':
      return <span data-type="number">{String(val)}</span>;
    case 'boolean':
      return <span data-type="boolean">{String(val)}</span>;
    case 'string':
      return <span data-type="string">"{val}"</span>;
    case 'undefined':
      return <span data-type="undefined">undefined</span>;
    case 'object':
      if (Array.isArray(val)) {
        if (val.length === 0) return <span>[]</span>;
        return (
          <>
            [
            {val.map((item, i) => (
              <div key={i} style={{ paddingLeft: 16 }}>
                {renderValue(item, depth + 1)}{i < val.length - 1 ? ',' : ''}
              </div>
            ))}
            {indent}]
          </>
        );
      }
      if (val) {
        const entries = Object.entries(val as Record<string, unknown>);
        if (entries.length === 0) return <span>{'{}'}</span>;
        return (
          <>
            {'{'}
            {entries.map(([k, v], i) => (
              <div key={k} style={{ paddingLeft: 16 }}>
                <span data-type="key">"{k}"</span>: {renderValue(v, depth + 1)}{i < entries.length - 1 ? ',' : ''}
              </div>
            ))}
            {indent + '}'}
          </>
        );
      }
      return <span>{'{}'}</span>;
    default:
      return <span data-type="unknown">{String(val)}</span>;
  }
}

export const JsonViewer: React.FC<SimpleJsonViewerProps> = ({ value, collapsed = false, maxHeight = 400, fontSize = 13, label }) => {
  const [open, setOpen] = useState(!collapsed);
  return (
    <Box className="json-viewer" sx={{ fontFamily: 'monospace', fontSize, maxHeight, overflow: 'auto', border: '1px solid var(--mui-palette-divider)', borderRadius: 1, p: 1, background: 'var(--mui-palette-background-paper)' }}>
      {label && (
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
          <IconButton size="small" onClick={() => setOpen(o => !o)} aria-label={open ? 'Collapse JSON' : 'Expand JSON'}>
            <Typography component="span" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
              {open ? '-' : '+'}
            </Typography>
          </IconButton>
          <Typography variant="subtitle2" sx={{ ml: 0.5 }}>{label}</Typography>
        </Box>
      )}
      <Collapse in={open} timeout="auto" unmountOnExit={!label}>
        <Box component="pre" sx={{ m: 0, fontFamily: 'inherit', fontSize: 'inherit' }}>
          {renderValue(value)}
        </Box>
      </Collapse>
    </Box>
  );
};

export default JsonViewer;
