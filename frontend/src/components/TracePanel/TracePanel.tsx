import { PlaybackScrubber } from './PlaybackScrubber';
import { useFlowStore } from '../../store/flowStore';

interface TracePanelProps {
  onRequestFix: () => Promise<void>;
}

export function TracePanel({ onRequestFix }: TracePanelProps) {
  const {
    traceEvents,
    isTracing,
    traceComplete,
    activeIntent,
    sessionId,
    traceId,
    fixSuggestion,
    isFixLoading,
  } = useFlowStore();

  const latestError = [...traceEvents].reverse().find((e) => e.event_type === 'error');

  return (
    <aside className="trace-panel">
      <div className="panel-title">Trace</div>
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
          <div className={`trace-event ${event.event_type}`} key={`${event.sequence}-${event.fn_id}`}>
            <span>{event.sequence}</span>
            <span>{event.event_type}</span>
            <span>{event.fn_name}</span>
            <span>{event.timestamp_ms.toFixed(1)}ms</span>
          </div>
        ))}
      </div>

      {latestError && (
        <button className="primary-btn" onClick={onRequestFix} disabled={isFixLoading}>
          {isFixLoading ? 'Generating fix...' : 'Fix with AI'}
        </button>
      )}

      {fixSuggestion && (
        <div className="fix-card">
          <div className="fix-title">AI Fix ({fixSuggestion.confidence})</div>
          <div>{fixSuggestion.explanation}</div>
          <div>{fixSuggestion.fix}</div>
          {fixSuggestion.code_diff && <pre>{fixSuggestion.code_diff}</pre>}
        </div>
      )}
    </aside>
  );
}
