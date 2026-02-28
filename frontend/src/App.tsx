import { useCallback, useEffect, useMemo, useState } from 'react';
import { FlowCanvas } from './components/FlowCanvas/FlowCanvas';
import { IntentPanel } from './components/IntentPanel/IntentPanel';
import { TopBar } from './components/TopBar/TopBar';
import { TracePanel } from './components/TracePanel/TracePanel';
import { useApi } from './hooks/useApi';
import { useTraceContext } from './hooks/useTraceContext';
import { useTraceSocket } from './hooks/useWebSocket';
import { useFlowStore } from './store/flowStore';
import type { Intent } from './types';

function App() {
  const api = useApi();
  const socket = useTraceSocket();
  const traceContext = useTraceContext();

  const {
    repo,
    intents,
    activeIntent,
    traceEvents,
    isLoading,
    loadingStep,
    error,
    isFixLoading,
    setRepo,
    setIntents,
    setLoading,
    setError,
    startTrace,
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
        setLoading(true, 'Fetching + parsing repository');
        setRepoInput(repoName);
        const parsed = await api.parseRepo(repoName, undefined, traceContext.newHeaders());
        setRepo(parsed);

        setLoading(true, 'Ranking intents');
        const ranked = await api.getIntents(repoName);
        setIntents(ranked.intents);

        setLoading(false, 'Ready');
      } catch (err) {
        setError(String(err));
        setLoading(false, '');
      }
    },
    [api, setError, setIntents, setLoading, setRepo, traceContext]
  );

  const runIntent = useCallback(
    async (intent: Intent) => {
      if (!repo) return;
      try {
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
        setError(String(err));
      }
    },
    [api, repo, setError, simulateError, socket, startTrace, traceContext, traceMode]
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
      setError(String(err));
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
        <IntentPanel intents={intents} activeIntentId={activeIntent?.id} onRunIntent={runIntent} />
        <main className="main-panel">
          {error && <div className="error-banner">{error}</div>}
          <FlowCanvas />
        </main>
        <TracePanel onRequestFix={requestFix} />
      </div>
    </div>
  );
}

export default App;
