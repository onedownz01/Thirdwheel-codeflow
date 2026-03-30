import { useCallback, useRef } from 'react';
import { useFlowStore } from '../store/flowStore';
import { WS_BASE } from '../config/runtime';

export function useTraceSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { applyTraceEvent, completeTrace, setError, setTraceWarning } = useFlowStore();

  const connect = useCallback((wsPath: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE}${wsPath}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'trace_event' && msg.event) {
          applyTraceEvent(msg.event);
        } else if (msg.type === 'trace_warning') {
          const reason = msg.warning
            || msg.event?.attributes?.reason
            || msg.event?.fn_name
            || 'Missing function in graph';
          setTraceWarning(reason);
        } else if (msg.type === 'trace_complete') {
          completeTrace();
        } else if (msg.type === 'trace_error') {
          setError(msg.error || 'Trace stream failed');
          completeTrace();
        }
      } catch (err) {
        setError(`WebSocket parse error: ${String(err)}`);
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      wsRef.current = null;
    };
  }, [applyTraceEvent, completeTrace, setError, setTraceWarning]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return { connect, disconnect };
}
