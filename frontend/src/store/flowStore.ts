import { create } from 'zustand';
import type {
  BlockState,
  FixSuggestion,
  Intent,
  ParsedRepo,
  TraceEvent,
} from '../types';

interface FlowStore {
  repo: ParsedRepo | null;
  repoHistory: string[];
  intents: Intent[];
  isLoading: boolean;
  loadingStep: string;
  error: string | null;
  traceWarning: string | null;

  activeIntent: Intent | null;
  blockStates: Record<string, BlockState>;
  traceEvents: TraceEvent[];
  isTracing: boolean;
  traceComplete: boolean;

  playbackIndex: number;
  isPlaying: boolean;
  totalSteps: number;
  fitViewNonce: number;

  sessionId: string | null;
  traceId: string | null;

  fixSuggestion: FixSuggestion | null;
  isFixLoading: boolean;

  setRepo: (repo: ParsedRepo) => void;
  addRepoHistory: (repoName: string) => void;
  setIntents: (intents: Intent[]) => void;
  setLoading: (loading: boolean, step?: string) => void;
  setError: (error: string | null) => void;
  setTraceWarning: (warning: string | null) => void;

  startTrace: (intent: Intent, sessionId: string, traceId: string) => void;
  applyTraceEvent: (event: TraceEvent) => void;
  completeTrace: () => void;
  setPlaybackIndex: (index: number) => void;
  togglePlayback: () => void;
  requestFitView: () => void;
  resetTrace: () => void;

  setFixSuggestion: (fix: FixSuggestion | null) => void;
  setFixLoading: (loading: boolean) => void;
}

function buildInitialBlockStates(repo: ParsedRepo, activeIntent: Intent | null): Record<string, BlockState> {
  const flowSet = new Set(activeIntent?.flow_ids ?? []);
  const states: Record<string, BlockState> = {};
  for (const fn of repo.functions) {
    states[fn.id] = { status: flowSet.size === 0 || flowSet.has(fn.id) ? 'idle' : 'dimmed' };
  }
  return states;
}

function replayBlockStates(repo: ParsedRepo, activeIntent: Intent | null, traceEvents: TraceEvent[], index: number) {
  const states = buildInitialBlockStates(repo, activeIntent);
  const events = traceEvents.slice(0, index);

  for (let idx = 0; idx < events.length; idx += 1) {
    const event = events[idx];
    const callStep = events.slice(0, idx + 1).filter((e) => e.event_type === 'call').length;

    if (event.event_type === 'call') {
      states[event.fn_id] = {
        ...states[event.fn_id],
        status: 'calling',
        stepNumber: callStep,
        inputs: event.inputs,
      };
      continue;
    }

    if (event.event_type === 'return') {
      states[event.fn_id] = {
        ...states[event.fn_id],
        status: 'returned',
        outputs: event.outputs,
        durationMs: event.duration_ms,
      };
      continue;
    }

    if (event.event_type === 'error') {
      states[event.fn_id] = {
        ...states[event.fn_id],
        status: 'error',
        error: `${event.error_type}: ${event.error}`,
      };
    }
  }

  return states;
}

export const useFlowStore = create<FlowStore>((set, get) => ({
  repo: null,
  repoHistory:
    typeof window !== 'undefined'
      ? JSON.parse(window.localStorage.getItem('codeflow_repo_history') || '[]')
      : [],
  intents: [],
  isLoading: false,
  loadingStep: '',
  error: null,
  traceWarning: null,

  activeIntent: null,
  blockStates: {},
  traceEvents: [],
  isTracing: false,
  traceComplete: false,

  playbackIndex: 0,
  isPlaying: false,
  totalSteps: 0,
  fitViewNonce: 0,

  sessionId: null,
  traceId: null,

  fixSuggestion: null,
  isFixLoading: false,

  setRepo: (repo) =>
    set({
      repo,
      intents: repo.intents,
      blockStates: buildInitialBlockStates(repo, null),
      error: null,
    }),

  addRepoHistory: (repoName) =>
    set((state) => {
      const next = [repoName, ...state.repoHistory.filter((r) => r !== repoName)].slice(0, 20);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('codeflow_repo_history', JSON.stringify(next));
      }
      return { repoHistory: next };
    }),

  setIntents: (intents) => set({ intents }),

  setLoading: (isLoading, loadingStep = '') => set({ isLoading, loadingStep }),

  setError: (error) => set({ error, isLoading: false }),
  setTraceWarning: (traceWarning) => set({ traceWarning }),

  startTrace: (intent, sessionId, traceId) => {
    const { repo } = get();
    if (!repo) return;

    set({
      activeIntent: intent,
      sessionId,
      traceId,
      blockStates: buildInitialBlockStates(repo, intent),
      traceEvents: [],
      isTracing: true,
      traceComplete: false,
      playbackIndex: 0,
      isPlaying: false,
      totalSteps: 0,
      fixSuggestion: null,
      error: null,
      traceWarning: null,
    });
  },

  applyTraceEvent: (event) => {
    set((state) => {
      const traceEvents = [...state.traceEvents, event];
      const totalSteps = traceEvents.length;

      if (!state.repo) {
        return { traceEvents, totalSteps } as Partial<FlowStore>;
      }

      const blockStates = replayBlockStates(
        state.repo,
        state.activeIntent,
        traceEvents,
        totalSteps
      );

      return {
        traceEvents,
        blockStates,
        totalSteps,
        playbackIndex: totalSteps,
      };
    });
  },

  completeTrace: () => set({ isTracing: false, traceComplete: true, isPlaying: false }),

  setPlaybackIndex: (playbackIndex) => {
    const { repo, activeIntent, traceEvents } = get();
    if (!repo) {
      set({ playbackIndex, isPlaying: false });
      return;
    }
    const normalized = Math.max(0, Math.min(playbackIndex, traceEvents.length));
    const blockStates = replayBlockStates(repo, activeIntent, traceEvents, normalized);
    set({ playbackIndex: normalized, blockStates, isPlaying: false });
  },

  togglePlayback: () =>
    set((state) => {
      if (!state.traceComplete || state.traceEvents.length === 0) {
        return { isPlaying: false };
      }
      const nextPlaying = !state.isPlaying;
      const nextIndex =
        nextPlaying && state.playbackIndex >= state.traceEvents.length ? 0 : state.playbackIndex;
      return { isPlaying: nextPlaying, playbackIndex: nextIndex };
    }),

  requestFitView: () => set((state) => ({ fitViewNonce: state.fitViewNonce + 1 })),

  resetTrace: () => {
    const { repo } = get();
    set({
      activeIntent: null,
      traceEvents: [],
      isTracing: false,
      traceComplete: false,
      playbackIndex: 0,
      isPlaying: false,
      totalSteps: 0,
      sessionId: null,
      traceId: null,
      blockStates: repo ? buildInitialBlockStates(repo, null) : {},
      fixSuggestion: null,
      traceWarning: null,
    });
  },

  setFixSuggestion: (fixSuggestion) => set({ fixSuggestion }),
  setFixLoading: (isFixLoading) => set({ isFixLoading }),
}));
