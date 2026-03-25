import { PlaybackScrubber } from './PlaybackScrubber';
import { useFlowStore } from '../../store/flowStore';

function formatFull(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function TracePanel() {
  const {
    traceEvents,
    isTracing,
    traceComplete,
    activeIntent,
    sessionId,
    traceId,
    selectedNodeId,
    setSelectedNode,
    repo,
    blockStates,
  } = useFlowStore();

  const selectedFn   = selectedNodeId ? repo?.functions.find((f) => f.id === selectedNodeId) : null;
  const selectedState = selectedNodeId ? blockStates[selectedNodeId] : null;

  // Build full input rows for detail view
  const detailInputs = selectedState?.inputs && selectedState.inputs.length > 0
    ? selectedState.inputs.map((v) => ({ name: v.name, val: formatFull(v.value), type: v.type_name, sensitive: v.is_sensitive }))
    : selectedFn?.params.filter((p) => p.direction !== 'out').map((p) => ({ name: p.name, val: '', type: p.type, sensitive: false })) ?? [];

  const detailOutputs = selectedState?.outputs && selectedState.outputs.length > 0
    ? selectedState.outputs.map((v) => ({ name: v.name, val: formatFull(v.value), type: v.type_name, sensitive: v.is_sensitive }))
    : [];

  return (
    <aside className="trace-panel">
      <div className="panel-title">
        {selectedFn ? (
          <span className="trace-panel-title-row">
            <span>Function</span>
            <button className="node-detail-close" onClick={() => setSelectedNode(null)}>✕</button>
          </span>
        ) : 'Trace'}
      </div>

      {selectedFn ? (
        /* ── Node detail view ───────────────────────────────── */
        <div className="node-detail">
          <div className="node-detail-header">
            <span className="node-detail-name">{selectedFn.name}</span>
            <span className="node-detail-type">{selectedFn.type.toUpperCase()}</span>
          </div>
          <div className="node-detail-file">
            {selectedFn.file}:{selectedFn.line}
          </div>
          {(selectedState?.stepNumber !== undefined || selectedState?.durationMs !== undefined) && (
            <div className="node-detail-meta">
              {selectedState.stepNumber !== undefined && <span>step {selectedState.stepNumber}</span>}
              {selectedState.durationMs !== undefined && <span>{Math.round(selectedState.durationMs)}ms</span>}
            </div>
          )}

          {detailInputs.length > 0 && (
            <div className="node-detail-section">
              <div className="node-detail-section-label">INPUTS</div>
              {detailInputs.map((row, i) => (
                <div className="node-detail-row" key={`in-${i}`}>
                  <div className="node-detail-row-header">
                    <span className="row-dot">◆</span>
                    <span className="node-detail-row-name">{row.name}</span>
                    {row.type && <span className="node-detail-row-type">{row.type}</span>}
                  </div>
                  {row.val && (
                    <pre className="node-detail-value">
                      {row.sensitive ? '••••••' : row.val}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}

          {detailOutputs.length > 0 && (
            <div className="node-detail-section">
              <div className="node-detail-section-label">OUTPUTS</div>
              {detailOutputs.map((row, i) => (
                <div className="node-detail-row" key={`out-${i}`}>
                  <div className="node-detail-row-header">
                    <span className="row-dot">◇</span>
                    <span className="node-detail-row-name">{row.name}</span>
                    {row.type && <span className="node-detail-row-type">{row.type}</span>}
                  </div>
                  {row.val && (
                    <pre className="node-detail-value">
                      {row.sensitive ? '••••••' : row.val}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}

          {selectedFn.description && (
            <div className="node-detail-section">
              <div className="node-detail-section-label">DESCRIPTION</div>
              <div className="node-detail-desc">{selectedFn.description}</div>
            </div>
          )}
        </div>
      ) : (
        /* ── Default trace view ─────────────────────────────── */
        <>
          <div className="trace-meta">
            <div>Intent: {activeIntent?.label ?? '-'}</div>
            <div>Status: {isTracing ? 'running' : traceComplete ? 'complete' : 'idle'}</div>
            <div>Session: {sessionId ?? '-'}</div>
            <div>Trace: {traceId ?? '-'}</div>
            <div>Events: {traceEvents.length}</div>
            <div>Shortcuts: Space play/pause, R reset, F fit</div>
          </div>

          <PlaybackScrubber />

          <div className="trace-events">
            {traceEvents.map((event) => (
              <div
                className={`trace-event ${event.event_type}`}
                key={`${event.sequence}-${event.fn_id}`}
              >
                <span>{event.sequence}</span>
                <span>{event.event_type}</span>
                <span>{event.fn_name}</span>
                <span>{event.timestamp_ms.toFixed(1)}ms</span>
              </div>
            ))}
          </div>
        </>
      )}
    </aside>
  );
}
