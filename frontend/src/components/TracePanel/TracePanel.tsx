import { PlaybackScrubber } from './PlaybackScrubber';
import { useFlowStore } from '../../store/flowStore';

export function TracePanel() {
  const {
    traceEvents,
    isTracing,
    traceComplete,
    activeIntent,
    sessionId,
    traceId,
  } = useFlowStore();

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
    </aside>
  );
}
