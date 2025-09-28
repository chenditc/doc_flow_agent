import React, { useState, useMemo } from 'react';
import { Box, IconButton, Typography, Collapse } from '@mui/material';
import ReactJson from 'react18-json-view';
import 'react18-json-view/src/style.css';

/**
 * Wrapper around react18-json-view to provide previous API compatibility.
 * We keep props small; any future advanced props can be exposed when needed.
 */
export interface SimpleJsonViewerProps {
  value: unknown;
  collapsed?: boolean; // if true start collapsed (previous meaning inverted vs open)
  maxHeight?: number | string;
  fontSize?: number | string;
  label?: string; // optional header with manual collapse toggle (kept to preserve UX)
}

export const JsonViewer: React.FC<SimpleJsonViewerProps> = ({
  value,
  collapsed = false,
  maxHeight = 400,
  fontSize = 13,
  label,
}) => {
  const [open, setOpen] = useState(!collapsed);

  // react18-json-view accepts src prop, and has own collapse features, but we gate by root collapse for parity
  const jsonValue = useMemo(() => value as any, [value]);

  return (
    <Box
      className="json-viewer"
      sx={{
        fontFamily: 'monospace',
        fontSize,
        maxHeight,
        overflow: 'auto',
        border: '1px solid var(--mui-palette-divider)',
        borderRadius: 1,
        p: 1,
        background: 'var(--mui-palette-background-paper)'
      }}
    >
      {label && (
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
          <IconButton
            size="small"
            onClick={() => setOpen(o => !o)}
            aria-label={open ? 'Collapse JSON' : 'Expand JSON'}
          >
            <Typography component="span" sx={{ fontSize: '0.75rem', fontWeight: 600 }}>
              {open ? '-' : '+'}
            </Typography>
          </IconButton>
          <Typography variant="subtitle2" sx={{ ml: 0.5 }}>{label}</Typography>
        </Box>
      )}
      <Collapse in={open} timeout="auto" unmountOnExit={!label}>
        <ReactJson
          src={jsonValue}
          theme="atom"
          collapsed={false}
          enableClipboard={false}
          style={{
            fontSize: typeof fontSize === 'number' ? `${fontSize}px` : fontSize,
            background: 'transparent',
          }}
        />
      </Collapse>
    </Box>
  );
};

export default JsonViewer;
