import type {
  ApiEnvelope,
  FixSuggestion,
  Intent,
  ParsedRepo,
  TraceSession,
} from '../types';
import type { TraceHeaders } from './useTraceContext';
import { API_BASE } from '../config/runtime';

function printable(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return '';
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { headers: initHeaders, ...restInit } = init ?? {};
  const mergedHeaders = {
    'Content-Type': 'application/json',
    ...(initHeaders || {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...restInit,
      headers: mergedHeaders,
    });
  } catch (err) {
    const reason = err instanceof Error ? err.message : printable(err);
    throw new Error(`Network error for ${path}: ${reason}`);
  }
  const text = await res.text();
  let parsed: unknown = null;
  try {
    parsed = JSON.parse(text);
  } catch {
    parsed = null;
  }

  const body = parsed as ApiEnvelope<T> | { detail?: string } | null;
  const detail = body && typeof body === 'object' && 'detail' in body ? printable(body.detail) : '';
  const envelopeError =
    body && typeof body === 'object' && 'error' in body
      ? printable((body as ApiEnvelope<T>).error || '')
      : '';
  const okEnvelope =
    body && typeof body === 'object' && 'success' in body
      ? Boolean((body as ApiEnvelope<T>).success)
      : res.ok;

  if (!res.ok || !okEnvelope) {
    throw new Error(detail || envelopeError || `Request failed for ${path}`);
  }
  if (!body || typeof body !== 'object' || !('data' in body)) {
    throw new Error(`Invalid API response for ${path}`);
  }
  return (body as ApiEnvelope<T>).data;
}

export function useApi() {
  return {
    parseRepo: (repo: string, token?: string, traceHeaders?: TraceHeaders, bustCache = false) =>
      request<ParsedRepo>('/parse', {
        method: 'POST',
        headers: traceHeaders ? { traceparent: traceHeaders.traceparent } : undefined,
        body: JSON.stringify({ repo, token: token || undefined, bust_cache: bustCache }),
      }),

    getIntents: (repo: string) =>
      request<{ repo: string; branch: string; count: number; intents: Intent[] }>(
        `/intents?repo=${encodeURIComponent(repo)}`
      ),

    startTrace: (
      repo: string,
      intentId: string,
      mode: 'simulation' | 'otel' | 'live' = 'simulation',
      simulateErrorAtStep?: number,
      traceHeaders?: TraceHeaders,
      projectRoot?: string,
      command?: string[]
    ) =>
      request<{
        session_id: string;
        trace_id: string;
        root_span_id?: string;
        parent_span_id?: string;
        ws_path: string;
        mode: 'simulation' | 'otel' | 'live';
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
          project_root: projectRoot ?? '',
          command: command ?? [],
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
