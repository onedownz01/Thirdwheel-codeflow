import type {
  ApiEnvelope,
  FixSuggestion,
  Intent,
  ParsedRepo,
  TraceSession,
} from '../types';
import type { TraceHeaders } from './useTraceContext';

const API_BASE = 'http://127.0.0.1:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  });

  const body = (await res.json()) as ApiEnvelope<T>;
  if (!res.ok || !body.success) {
    throw new Error(body.error || `Request failed for ${path}`);
  }
  return body.data;
}

export function useApi() {
  return {
    parseRepo: (repo: string, token?: string, traceHeaders?: TraceHeaders) =>
      request<ParsedRepo>('/parse', {
        method: 'POST',
        headers: traceHeaders ? { traceparent: traceHeaders.traceparent } : undefined,
        body: JSON.stringify({ repo, token: token || undefined }),
      }),

    getIntents: (repo: string) =>
      request<{ repo: string; branch: string; count: number; intents: Intent[] }>(
        `/intents?repo=${encodeURIComponent(repo)}`
      ),

    startTrace: (
      repo: string,
      intentId: string,
      mode: 'simulation' | 'otel' = 'simulation',
      simulateErrorAtStep?: number,
      traceHeaders?: TraceHeaders
    ) =>
      request<{
        session_id: string;
        trace_id: string;
        root_span_id?: string;
        parent_span_id?: string;
        ws_path: string;
        mode: 'simulation' | 'otel';
        warnings?: string[];
        simulate_error_at_step?: number;
      }>('/trace/start', {
        method: 'POST',
        headers: traceHeaders ? { traceparent: traceHeaders.traceparent } : undefined,
        body: JSON.stringify({
          repo,
          intent_id: intentId,
          mode,
          simulate_error_at_step: simulateErrorAtStep,
        }),
      }),

    getTrace: (sessionId: string) =>
      request<{ session: TraceSession; event_count: number; error_count: number }>(`/trace/${sessionId}`),

    getFix: (payload: unknown) =>
      request<FixSuggestion>('/fix', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  };
}
