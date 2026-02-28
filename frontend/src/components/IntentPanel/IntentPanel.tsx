import type { Intent } from '../../types';

interface IntentPanelProps {
  intents: Intent[];
  activeIntentId?: string;
  onRunIntent: (intent: Intent) => void;
}

function confidenceBadge(confidence: number): string {
  if (confidence >= 0.85) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

export function IntentPanel({ intents, activeIntentId, onRunIntent }: IntentPanelProps) {
  return (
    <aside className="intent-panel">
      <div className="panel-title">Intents</div>
      <div className="intent-list">
        {intents.length === 0 && <div className="empty">No intents found yet.</div>}
        {intents.map((intent) => {
          const confidence = confidenceBadge(intent.confidence);
          const isActive = activeIntentId === intent.id;
          return (
            <button
              key={intent.id}
              className={`intent-item ${isActive ? 'active' : ''}`}
              onClick={() => onRunIntent(intent)}
            >
              <div className="intent-main">
                <span>{intent.icon}</span>
                <span>{intent.label}</span>
              </div>
              <div className="intent-meta">
                <span>{intent.group}</span>
                <span className={`confidence ${confidence}`}>{confidence}</span>
                <span>{Math.round(intent.confidence * 100)}%</span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
