import { useEffect, useState } from 'react';

interface TopBarProps {
  repo: string;
  onParse: (repo: string) => Promise<void>;
  loading: boolean;
  loadingStep: string;
  simulateError: boolean;
  onToggleSimError: (next: boolean) => void;
  traceMode: 'simulation' | 'otel' | 'live';
  onModeChange: (mode: 'simulation' | 'otel' | 'live') => void;
  projectRoot: string;
  onProjectRootChange: (v: string) => void;
  command: string;
  onCommandChange: (v: string) => void;
}

export function TopBar({
  repo,
  onParse,
  loading,
  loadingStep,
  simulateError,
  onToggleSimError,
  traceMode,
  onModeChange,
  projectRoot,
  onProjectRootChange,
  command,
  onCommandChange,
}: TopBarProps) {
  const [value, setValue] = useState(repo || 'tiangolo/fastapi');
  useEffect(() => {
    setValue(repo || 'tiangolo/fastapi');
  }, [repo]);

  return (
    <header className="topbar">
      <div className="brand">CodeFlow</div>
      <div className="repo-input-wrap">
        <input
          className="repo-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="owner/repo"
          onKeyDown={(e) => e.key === 'Enter' && !loading && value.trim() && onParse(value.trim())}
        />
        {traceMode === 'live' && (
          <>
            <input
              className="live-input"
              value={projectRoot}
              onChange={(e) => onProjectRootChange(e.target.value)}
              placeholder="/path/to/project"
              title="Absolute path to your project on disk"
            />
            <input
              className="live-input"
              value={command}
              onChange={(e) => onCommandChange(e.target.value)}
              placeholder="python -m uvicorn main:app"
              title="Command to run your app"
            />
          </>
        )}
        <button
          className="primary-btn"
          disabled={loading || !value.trim()}
          onClick={() => onParse(value.trim())}
        >
          {loading ? loadingStep || 'Parsing…' : 'Parse'}
        </button>
      </div>
      <div className="topbar-status">{!loading && loadingStep}</div>
      <select
        className="mode-select"
        value={traceMode}
        onChange={(e) => onModeChange(e.target.value as 'simulation' | 'otel' | 'live')}
      >
        <option value="simulation">Sim</option>
        <option value="otel">OTel</option>
        <option value="live">Live</option>
      </select>
      {traceMode !== 'live' && (
        <label className="sim-toggle">
          <input
            type="checkbox"
            checked={simulateError}
            onChange={(e) => onToggleSimError(e.target.checked)}
          />
          err
        </label>
      )}
    </header>
  );
}
