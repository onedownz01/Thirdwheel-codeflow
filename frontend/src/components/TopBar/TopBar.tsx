import { useEffect, useState } from 'react';

interface TopBarProps {
  repo: string;
  onParse: (repo: string) => Promise<void>;
  loading: boolean;
  loadingStep: string;
  simulateError: boolean;
  onToggleSimError: (next: boolean) => void;
  traceMode: 'simulation' | 'otel';
  onModeChange: (mode: 'simulation' | 'otel') => void;
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
        />
        <button
          className="primary-btn"
          disabled={loading || !value.trim()}
          onClick={() => onParse(value.trim())}
        >
          {loading ? 'Parsing...' : 'Parse Repo'}
        </button>
      </div>
      <div className="topbar-status">{loadingStep}</div>
      <select
        className="mode-select"
        value={traceMode}
        onChange={(e) => onModeChange(e.target.value as 'simulation' | 'otel')}
      >
        <option value="simulation">Simulation</option>
        <option value="otel">OTel</option>
      </select>
      <label className="sim-toggle">
        <input
          type="checkbox"
          checked={simulateError}
          onChange={(e) => onToggleSimError(e.target.checked)}
        />
        Sim Error
      </label>
    </header>
  );
}
