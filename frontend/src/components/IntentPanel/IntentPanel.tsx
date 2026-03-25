import { useState } from 'react';
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
  const [query, setQuery] = useState('');

  const filtered = query.trim()
    ? intents.filter((i) => i.label.toLowerCase().includes(query.toLowerCase()))
    : intents;

  const grouped = filtered.reduce<Record<string, Intent[]>>((acc, intent) => {
    const key = intent.group || 'Actions';
    if (!acc[key]) acc[key] = [];
    acc[key].push(intent);
    return acc;
  }, {});

  const groups = Object.entries(grouped).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <section className="intent-panel">
      <div className="panel-title">Intents</div>
      {intents.length > 0 && (
        <div className="intent-search-wrap">
          <input
            className="intent-search"
            placeholder="filter intents…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            spellCheck={false}
          />
          {query && (
            <button className="intent-search-clear" onClick={() => setQuery('')}>✕</button>
          )}
        </div>
      )}
      <div className="intent-list">
        {intents.length === 0 && <div className="empty">No intents found yet.</div>}
        {filtered.length === 0 && intents.length > 0 && (
          <div className="empty">No match for "{query}"</div>
        )}
        {groups.map(([group, groupIntents], idx) => (
          <details key={group} className="intent-group" open={idx < 2 || !!query}>
            <summary>
              <span>{group}</span>
              <span className="intent-group-count">{groupIntents.length}</span>
            </summary>
            <div className="intent-group-items">
              {groupIntents.map((intent) => {
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
                      <span>{intent.trigger}</span>
                      <span className={`confidence ${confidence}`}>{confidence}</span>
                      <span>{Math.round(intent.confidence * 100)}%</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
