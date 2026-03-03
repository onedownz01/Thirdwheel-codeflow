import { useCallback, useEffect, useMemo, useState } from 'react';
import { FlowCanvas } from './components/FlowCanvas/FlowCanvas';
import { IntentPanel } from './components/IntentPanel/IntentPanel';
import { RepoHistoryPanel } from './components/RepoHistoryPanel';
import { TopBar } from './components/TopBar/TopBar';
import { TracePanel } from './components/TracePanel/TracePanel';
import { useApi } from './hooks/useApi';
import { useTraceContext } from './hooks/useTraceContext';
import { useTraceSocket } from './hooks/useWebSocket';
import { useFlowStore } from './store/flowStore';
import type { Intent } from './types';

function normalizeRepoInput(input: string): string {
  const raw = input.trim().replace(/\.git$/i, '');
  const match = raw.match(/github\.com[:/]+([^/]+)\/([^/]+?)(?:\/)?$/i);
  if (match) {
    return `${match[1]}/${match[2]}`;
  }
  return raw;
}

function toErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  try {
    return JSON.stringify(err);
  } catch {
    return String(err);
  }
}

function App() {
  const api = useApi();
  const socket = useTraceSocket();
  const traceContext = useTraceContext();

  const {
    repo,
    repoHistory,
    intents,
    activeIntent,
    traceEvents,
    isLoading,
    loadingStep,
    error,
    traceWarning,
    isFixLoading,
    setRepo,
    setIntents,
    setLoading,
    setError,
    setTraceWarning,
    startTrace,
    addRepoHistory,
    resetTrace,
    requestFitView,
    togglePlayback,
    setFixLoading,
    setFixSuggestion,
  } = useFlowStore();

  const [repoInput, setRepoInput] = useState('tiangolo/fastapi');
  const [simulateError, setSimulateError] = useState(false);
  const [traceMode, setTraceMode] = useState<'simulation' | 'otel'>('simulation');

  const parseRepo = useCallback(
    async (repoName: string) => {
      try {
        setTraceWarning(null);
        setLoading(true, 'Fetching + parsing repository');
        const normalized = normalizeRepoInput(repoName);
        setRepoInput(normalized);
        const parsed = await api.parseRepo(normalized, undefined, traceContext.newHeaders());
        setRepo(parsed);
        addRepoHistory(parsed.repo);

        setLoading(true, 'Ranking intents');
        const ranked = await api.getIntents(normalized);
        setIntents(ranked.intents);

        setLoading(false, 'Ready');
      } catch (err) {
        setError(toErrorMessage(err));
        setLoading(false, '');
      }
    },
    [addRepoHistory, api, setError, setIntents, setLoading, setRepo, setTraceWarning, traceContext]
  );

  const runIntent = useCallback(
    async (intent: Intent) => {
      if (!repo) return;
      try {
        setTraceWarning(null);
        const started = await api.startTrace(
          repo.repo,
          intent.id,
          traceMode,
          simulateError ? 2 : undefined,
          traceContext.newHeaders()
        );
        startTrace(intent, started.session_id, started.trace_id);
        socket.connect(started.ws_path);
      } catch (err) {
        setError(toErrorMessage(err));
      }
    },
    [api, repo, setError, setTraceWarning, simulateError, socket, startTrace, traceContext, traceMode]
  );

  const requestFix = useCallback(async () => {
    if (!repo || !activeIntent) return;
    const latestError = [...traceEvents].reverse().find((e) => e.event_type === 'error');
    if (!latestError) return;

    try {
      setFixLoading(true);
      const payload = {
        session_id: useFlowStore.getState().sessionId,
        error_fn_id: latestError.fn_id,
        trace_session: {
          schema_version: '2.0.0',
          session_id: useFlowStore.getState().sessionId,
          intent_id: activeIntent.id,
          intent_label: activeIntent.label,
          trace_mode: 'simulation',
          trace_id: useFlowStore.getState().traceId,
          events: traceEvents,
          status: 'error',
          total_duration_ms: traceEvents[traceEvents.length - 1]?.timestamp_ms ?? 0,
          error_at_fn_id: latestError.fn_id,
        },
        parsed_repo: repo,
      };

      const fix = await api.getFix(payload);
      setFixSuggestion(fix);
    } catch (err) {
      setError(toErrorMessage(err));
    } finally {
      setFixLoading(false);
    }
  }, [activeIntent, api, repo, setError, setFixLoading, setFixSuggestion, traceEvents]);

  const repoName = useMemo(() => repo?.repo || repoInput, [repo, repoInput]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) {
        return;
      }
      if (event.code === 'Space') {
        event.preventDefault();
        togglePlayback();
      } else if (event.key.toLowerCase() === 'r') {
        resetTrace();
      } else if (event.key.toLowerCase() === 'f') {
        requestFitView();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [requestFitView, resetTrace, togglePlayback]);

  return (
    <div className="app-shell">
      <TopBar
        repo={repoName}
        onParse={parseRepo}
        loading={isLoading}
        loadingStep={loadingStep}
        simulateError={simulateError}
        onToggleSimError={setSimulateError}
        traceMode={traceMode}
        onModeChange={setTraceMode}
      />
      <div className="app-body">
        <RepoHistoryPanel repos={repoHistory} activeRepo={repo?.repo} onSelectRepo={parseRepo} />
        <main className="main-panel">
          {error && <div className="error-banner">{error}</div>}
          {traceWarning && <div className="warning-banner">{traceWarning}</div>}
          <FlowCanvas />
        </main>
        <aside className="right-panel">
          <IntentPanel intents={intents} activeIntentId={activeIntent?.id} onRunIntent={runIntent} />
          <TracePanel onRequestFix={requestFix} />
        </aside>
      </div>
    </div>
  );
}

export default App;
