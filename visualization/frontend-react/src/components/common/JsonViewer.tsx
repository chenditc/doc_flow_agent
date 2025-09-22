import React, { useState } from 'react';

interface JsonViewerProps {
  src: any;
  name?: string | false;
  collapsed?: number | boolean; // number = depth
  collapseStringsAfterLength?: number;
}

// Lightweight JSON viewer (collapsible) to avoid heavy external deps.
export const JsonViewer: React.FC<JsonViewerProps> = ({
  src,
  name = false,
  collapsed = 1,
  collapseStringsAfterLength = 120,
}) => {
  const renderNode = (key: string | null, value: any, depth: number): React.ReactNode => {
    const isObject = value && typeof value === 'object' && !Array.isArray(value);
    const isArray = Array.isArray(value);
    const isCollapsible = isObject || isArray;
    const [open, setOpen] = useState(() => {
      if (typeof collapsed === 'boolean') return !collapsed;
      if (typeof collapsed === 'number') return depth >= collapsed ? false : true;
      return true;
    });

    const displayKey = key !== null ? <span className="text-blue-700 mr-1">{key}:</span> : null;

    const formatPrimitive = (val: any) => {
      if (val === null) return <span className="text-pink-700">null</span>;
      switch (typeof val) {
        case 'string': {
          let s = val;
          if (collapseStringsAfterLength && s.length > collapseStringsAfterLength) {
            s = s.slice(0, collapseStringsAfterLength) + '…';
          }
          return <span className="text-green-700 break-all">"{s}"</span>;
        }
        case 'number':
        case 'bigint':
          return <span className="text-purple-700">{String(val)}</span>;
        case 'boolean':
          return <span className="text-orange-600">{String(val)}</span>;
        default:
          return <span className="text-gray-600">{String(val)}</span>;
      }
    };

    if (!isCollapsible) {
      return (
        <div className="pl-2">
          {displayKey}
          {formatPrimitive(value)}
        </div>
      );
    }

    const entries = isArray ? value.map((v: any, i: number) => [String(i), v]) : Object.entries(value);

    return (
      <div className="pl-2">
        <div className="flex items-center cursor-pointer select-none" onClick={() => setOpen(o => !o)}>
          <span className="mr-1 text-xs px-1 border rounded bg-white text-gray-600">{open ? '-' : '+'}</span>
          {displayKey}
          <span className="text-gray-700 font-mono">
            {isArray ? `[${value.length}]` : `{${entries.length}}`}
          </span>
        </div>
        {open && (
          <div className="ml-4 border-l border-gray-200">
            {entries.map(([k, v]) => (
              <div key={k}>{renderNode(k, v, depth + 1)}</div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="font-mono text-[11px] leading-relaxed">
      {name && <div className="font-semibold mb-1">{name}</div>}
      {renderNode(null, src, 0)}
    </div>
  );
};
