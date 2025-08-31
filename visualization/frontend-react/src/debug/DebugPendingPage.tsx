import React from 'react';
import { useTrace } from '../hooks/useTraceData';
import { Timeline } from '../components/Timeline/Timeline';

// This component is a minimal debug surface to inspect why pending tasks might not render
// Usage: /?debug=pending&traceId=<TRACE_ID>
export const DebugPendingPage: React.FC = () => {
  // We won't rely on react-router actually being present; provide a safe fallback
  const [traceId, setTraceId] = React.useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('traceId');
  });

  const { data: trace, isLoading, error } = useTrace(traceId);

  const [inputId, setInputId] = React.useState<string>(traceId || 'session_20250903_113121_15a5ca06');

  const reloadWithId = () => {
    const newParams = new URLSearchParams(window.location.search);
    if (inputId) newParams.set('traceId', inputId);
    else newParams.delete('traceId');
    const newUrl = `${window.location.pathname}?${newParams.toString()}`;
    window.history.replaceState({}, '', newUrl);
    setTraceId(inputId || null);
  };

  const getPendingTasks = React.useCallback((): string[] => {
    // Mirror Timeline logic: use last execution's engine_state_before.task_stack; fallback to end snapshot
    if (!trace) return [];

    const execs = trace.task_executions || [];
    if (execs.length > 0) {
      const lastExec = execs[execs.length - 1] as any;
      const beforeStack = lastExec?.engine_state_before?.task_stack as string[] | undefined;
      if (Array.isArray(beforeStack)) {
        return [...beforeStack].reverse();
      }
    }

    const endStack = trace.engine_snapshots?.end?.task_stack as string[] | undefined;
    if (Array.isArray(endStack)) {
      return [...endStack].reverse();
    }
    return [];
  }, [trace]);

  const pending = getPendingTasks();

  return (
    <div className="space-y-4">
      <div className="bg-white p-4 rounded border">
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700">Trace ID</label>
            <input
              className="mt-1 w-full rounded border px-3 py-2 text-sm"
              placeholder="session_..."
              value={inputId}
              onChange={(e) => setInputId(e.target.value)}
            />
          </div>
          <button
            className="inline-flex items-center rounded bg-blue-600 text-white px-3 py-2 text-sm hover:bg-blue-700"
            onClick={reloadWithId}
          >
            Load
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">Tip: add debug=pending&traceId=... to the URL query.</p>
      </div>

      <div className="bg-white p-4 rounded border">
        <h3 className="font-semibold mb-2">Trace Fetch Status</h3>
        <div className="text-sm">
          <div><span className="font-medium">isLoading:</span> {String(isLoading)}</div>
          {error && (
            <div className="text-red-600"><span className="font-medium">error:</span> {String(error)}</div>
          )}
          <div><span className="font-medium">hasTrace:</span> {String(!!trace)}</div>
        </div>
      </div>

      <div className="bg-white p-4 rounded border">
        <h3 className="font-semibold mb-2">High-level Shape</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div><span className="font-medium">task_executions length:</span> {trace?.task_executions?.length ?? 0}</div>
            <div><span className="font-medium">start_time:</span> {trace?.start_time ? new Date(trace.start_time).toLocaleString() : '—'}</div>
            <div><span className="font-medium">end_time:</span> {trace?.end_time ? new Date(trace.end_time).toLocaleString() : '—'}</div>
          </div>
          <div>
            <div><span className="font-medium">has engine_snapshots:</span> {String(!!trace?.engine_snapshots)}</div>
            <div><span className="font-medium">has engine_snapshots.end:</span> {String(!!trace?.engine_snapshots?.end)}</div>
            <div><span className="font-medium">has end.task_stack:</span> {String(!!trace?.engine_snapshots?.end?.task_stack)}</div>
          </div>
        </div>
      </div>

      <div className="bg-white p-4 rounded border">
        <h3 className="font-semibold mb-2">Raw end.task_stack (top of stack first)</h3>
        {pending.length === 0 ? (
          <div className="text-sm text-gray-600">No pending tasks found on engine_snapshots.end.task_stack</div>
        ) : (
          <ul className="list-disc pl-6 text-sm text-gray-800">
            {pending.map((p, i) => (
              <li key={i}>
                <span className="font-mono">[{i}]</span> {p}
                {i === 0 && <span className="ml-2 text-gray-500">(next to execute)</span>}
              </li>
            ))}
          </ul>
        )}
        <p className="text-xs text-gray-500 mt-2">Note: Currently executing is the last task in task_executions, not here.</p>
      </div>

      <div className="bg-white p-4 rounded border">
        <h3 className="font-semibold mb-2">Why might it not display?</h3>
        <ul className="list-disc pl-6 text-sm text-gray-700 space-y-1">
          <li>task_executions exists but end.task_stack is empty → pending section won’t render.</li>
          <li>engine_snapshots.end is missing or has a different shape → Timeline can’t locate task_stack.</li>
          <li>Trace not loaded (wrong traceId) → nothing to render.</li>
        </ul>
      </div>

      <div className="bg-white p-4 rounded border">
        <h3 className="font-semibold mb-2">Timeline Preview</h3>
        <p className="text-xs text-gray-500 mb-2">This is the live Timeline component for the same trace.</p>
        <Timeline trace={trace || null} onTaskClick={() => { /* no-op */ }} isLoading={isLoading} />
      </div>
    </div>
  );
};
