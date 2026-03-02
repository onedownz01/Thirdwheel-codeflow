interface RepoHistoryPanelProps {
  repos: string[];
  activeRepo?: string;
  onSelectRepo: (repo: string) => void;
}

export function RepoHistoryPanel({ repos, activeRepo, onSelectRepo }: RepoHistoryPanelProps) {
  return (
    <aside className="repo-history-panel">
      <div className="panel-title">Repo History</div>
      <div className="repo-history-list">
        {repos.length === 0 && <div className="empty">No recent repos.</div>}
        {repos.map((repo) => (
          <button
            key={repo}
            className={`repo-history-item ${activeRepo === repo ? 'active' : ''}`}
            onClick={() => onSelectRepo(repo)}
          >
            {repo}
          </button>
        ))}
      </div>
    </aside>
  );
}
