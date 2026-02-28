import { useCallback } from 'react';

export interface TraceHeaders {
  traceparent: string;
}

function randomHex(bytes: number): string {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return Array.from(buf)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export function useTraceContext() {
  const newHeaders = useCallback((): TraceHeaders => {
    const traceId = randomHex(16);
    const spanId = randomHex(8);
    return {
      traceparent: `00-${traceId}-${spanId}-01`,
    };
  }, []);

  return { newHeaders };
}
