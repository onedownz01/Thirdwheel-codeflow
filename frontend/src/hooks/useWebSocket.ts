import { useCallback, useRef } from 'react';
import { useFlowStore } from '../store/flowStore';

const WS_BASE = 'ws://127.0.0.1:8000';

export function useTraceSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { applyTraceEvent, completeTrace, setError } = useFlowStore();

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
          // Keep warnings visible without aborting stream.
          setError(`Trace warning: ${msg.warning || 'unknown warning'}`);
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
  }, [applyTraceEvent, completeTrace, setError]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return { connect, disconnect };
}
