import { useNavigate } from 'react-router-dom';

const S = {
  page: {
    background: '#0a0f1a',
    color: '#e2e8f0',
    fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', monospace",
    minHeight: '100vh',
    lineHeight: 1.6,
  } as React.CSSProperties,

  nav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 48px',
    height: 52,
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    position: 'sticky' as const,
    top: 0,
    background: 'rgba(10,15,26,0.92)',
    backdropFilter: 'blur(12px)',
    zIndex: 100,
  },

  navLogo: {
    fontSize: 13,
    fontWeight: 700,
    color: '#4ade80',
    letterSpacing: '0.12em',
  },

  navLinks: {
    display: 'flex',
    alignItems: 'center',
    gap: 32,
  },

  navLink: {
    fontSize: 12,
    color: '#94a3b8',
    textDecoration: 'none',
    letterSpacing: '0.06em',
    cursor: 'pointer',
    transition: 'color 0.15s',
  },

  launchBtn: {
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.1em',
    color: '#0a0f1a',
    background: '#4ade80',
    border: 'none',
    padding: '7px 18px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  },

  hero: {
    maxWidth: 860,
    margin: '0 auto',
    padding: '100px 48px 80px',
    textAlign: 'center' as const,
  },

  heroEyebrow: {
    fontSize: 11,
    letterSpacing: '0.18em',
    color: '#4ade80',
    marginBottom: 24,
    textTransform: 'uppercase' as const,
  },

  heroTitle: {
    fontSize: 52,
    fontWeight: 800,
    lineHeight: 1.1,
    marginBottom: 24,
    letterSpacing: '-0.02em',
    color: '#f1f5f9',
  },

  heroSub: {
    fontSize: 16,
    color: '#94a3b8',
    maxWidth: 560,
    margin: '0 auto 48px',
    lineHeight: 1.7,
  },

  heroCtas: {
    display: 'flex',
    gap: 16,
    justifyContent: 'center',
    flexWrap: 'wrap' as const,
  },

  ctaPrimary: {
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: '0.1em',
    color: '#0a0f1a',
    background: '#4ade80',
    border: 'none',
    padding: '12px 28px',
    cursor: 'pointer',
    fontFamily: 'inherit',
    textDecoration: 'none',
  },

  ctaSecondary: {
    fontSize: 12,
    fontWeight: 600,
    letterSpacing: '0.08em',
    color: '#94a3b8',
    background: 'transparent',
    border: '1px solid rgba(255,255,255,0.12)',
    padding: '12px 28px',
    cursor: 'pointer',
    fontFamily: 'inherit',
    textDecoration: 'none',
  },

  section: {
    maxWidth: 1000,
    margin: '0 auto',
    padding: '80px 48px',
    borderTop: '1px solid rgba(255,255,255,0.06)',
  },

  sectionLabel: {
    fontSize: 10,
    letterSpacing: '0.2em',
    color: '#4ade80',
    textTransform: 'uppercase' as const,
    marginBottom: 12,
  },

  sectionTitle: {
    fontSize: 28,
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: 12,
    letterSpacing: '-0.01em',
  },

  sectionSub: {
    fontSize: 14,
    color: '#94a3b8',
    marginBottom: 48,
    maxWidth: 560,
  },

  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 24,
  },

  card: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    padding: 32,
  },

  cardTag: {
    fontSize: 10,
    letterSpacing: '0.15em',
    color: '#4ade80',
    textTransform: 'uppercase' as const,
    marginBottom: 12,
  },

  cardTitle: {
    fontSize: 17,
    fontWeight: 700,
    color: '#f1f5f9',
    marginBottom: 10,
  },

  cardBody: {
    fontSize: 13,
    color: '#94a3b8',
    lineHeight: 1.7,
  },

  threeCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: 20,
  },

  modeCard: {
    background: 'rgba(255,255,255,0.025)',
    border: '1px solid rgba(255,255,255,0.07)',
    padding: '28px 24px',
  },

  modeName: {
    fontSize: 13,
    fontWeight: 800,
    color: '#4ade80',
    letterSpacing: '0.1em',
    marginBottom: 8,
  },

  modeTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: '#e2e8f0',
    marginBottom: 10,
  },

  modeBody: {
    fontSize: 12,
    color: '#94a3b8',
    lineHeight: 1.7,
    marginBottom: 16,
  },

  modeReq: {
    fontSize: 11,
    color: '#475569',
    borderTop: '1px solid rgba(255,255,255,0.05)',
    paddingTop: 12,
    marginTop: 8,
  },

  statGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 1,
    background: 'rgba(255,255,255,0.06)',
    marginBottom: 40,
  },

  statCell: {
    background: '#0a0f1a',
    padding: '28px 24px',
    textAlign: 'center' as const,
  },

  statNum: {
    fontSize: 36,
    fontWeight: 800,
    color: '#4ade80',
    letterSpacing: '-0.02em',
  },

  statLabel: {
    fontSize: 11,
    color: '#475569',
    letterSpacing: '0.08em',
    marginTop: 4,
  },

  benchRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: '10px 0',
    borderBottom: '1px solid rgba(255,255,255,0.04)',
  },

  benchRepo: {
    fontSize: 12,
    color: '#94a3b8',
    width: 240,
    flexShrink: 0,
  },

  benchBar: {
    flex: 1,
    height: 6,
    background: 'rgba(255,255,255,0.05)',
    position: 'relative' as const,
  },

  benchVal: {
    fontSize: 11,
    color: '#4ade80',
    fontWeight: 700,
    width: 50,
    textAlign: 'right' as const,
    flexShrink: 0,
  },

  codeBlock: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.07)',
    padding: '20px 24px',
    fontSize: 12,
    color: '#94a3b8',
    lineHeight: 1.8,
    overflowX: 'auto' as const,
  },

  codeComment: {
    color: '#475569',
  },

  codeGreen: {
    color: '#4ade80',
  },

  schemaField: {
    display: 'grid',
    gridTemplateColumns: '180px 1fr',
    gap: 12,
    padding: '8px 0',
    borderBottom: '1px solid rgba(255,255,255,0.04)',
    fontSize: 12,
  },

  fieldName: {
    color: '#4ade80',
    fontFamily: 'inherit',
  },

  fieldDesc: {
    color: '#94a3b8',
  },

  footer: {
    borderTop: '1px solid rgba(255,255,255,0.06)',
    padding: '32px 48px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: 11,
    color: '#334155',
  },
};

const BENCH_DATA = [
  { repo: 'Textualize/rich',                       saved: 78.3, retention: 83 },
  { repo: 'fastapi/full-stack-fastapi-template',   saved: 58.3, retention: 77 },
  { repo: 'pydantic/pydantic',                     saved: 48.3, retention: 56 },
  { repo: 'sqlalchemy/sqlalchemy',                 saved: 42.6, retention: 64 },
  { repo: 'encode/httpx',                          saved: 39.8, retention: 72 },
  { repo: 'psf/requests',                          saved: 31.4, retention: 90 },
  { repo: 'anthropics/anthropic-sdk-python',       saved: 24.0, retention: 74 },
  { repo: 'pallets/flask',                         saved: 15.9, retention: 80 },
];

const SCHEMA_FIELDS = [
  { name: 'functions[]',     desc: 'All functions — name, type, file, params, return_type, docstring, calls' },
  { name: 'intents[]',       desc: 'User-facing actions — routes, handlers, CLI commands, form events' },
  { name: 'edges[]',         desc: 'Call graph edges — source → target function IDs' },
  { name: 'fn_type_index',   desc: 'O(1) lookup: { "route": [...ids], "handler": [...ids], ... }' },
  { name: 'file_index',      desc: 'O(1) lookup: { "path/to/file.py": [...ids], ... }' },
];

export default function LandingPage() {
  const navigate = useNavigate();

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div style={S.page}>
      {/* ── Nav ── */}
      <nav style={S.nav}>
        <span style={S.navLogo}>CODEFLOW</span>
        <div style={S.navLinks}>
          <span style={S.navLink} onClick={() => scrollTo('for-agents')}>For Agents</span>
          <span style={S.navLink} onClick={() => scrollTo('benchmark')}>Benchmark</span>
          <span style={S.navLink} onClick={() => scrollTo('docs')}>Docs</span>
          <button style={S.launchBtn} onClick={() => navigate('/app')}>LAUNCH APP →</button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <div style={S.hero}>
        <div style={S.heroEyebrow}>Intent-anchored execution tracer</div>
        <h1 style={S.heroTitle}>
          See what your code does.<br />
          <span style={{ color: '#4ade80' }}>Not just what it says.</span>
        </h1>
        <p style={S.heroSub}>
          Paste any GitHub URL. Codeflow maps every user-facing action to its full call chain — for
          interactive tracing, for LLM agents, for anyone who needs to understand a codebase fast.
        </p>
        <div style={S.heroCtas}>
          <button style={S.ctaPrimary} onClick={() => navigate('/app')}>LAUNCH APP →</button>
          <button style={S.ctaSecondary} onClick={() => scrollTo('benchmark')}>VIEW BENCHMARK</button>
        </div>
      </div>

      {/* ── For Humans & For Agents ── */}
      <div style={S.section}>
        <div style={S.sectionLabel}>What is it</div>
        <h2 style={S.sectionTitle}>Built for two audiences.</h2>
        <p style={S.sectionSub}>
          Most tools pick one. Codeflow serves both — an interactive canvas for engineers,
          and a structured JSON format for agents.
        </p>
        <div style={S.twoCol}>
          <div style={S.card}>
            <div style={S.cardTag}>For Humans</div>
            <div style={S.cardTitle}>Interactive execution tracer</div>
            <div style={S.cardBody}>
              Paste a GitHub repo URL. Every user-facing action surfaces as an intent — buttons,
              routes, CLI commands, form handlers. Click one and watch the call chain animate
              in real time. Every function block shows file path, line number, and I/O at each step.<br /><br />
              Three trace modes: simulate from the static call graph, receive real OpenTelemetry
              spans from a running service, or attach directly to a local process.
            </div>
          </div>
          <div id="for-agents" style={S.card}>
            <div style={S.cardTag}>For Agents</div>
            <div style={S.cardTitle}>ParsedRepo — structured context for LLMs</div>
            <div style={S.cardBody}>
              Every repository becomes a single <code style={{ color: '#4ade80' }}>ParsedRepo</code> JSON object.
              Functions with typed signatures, docstrings, call edges, and pre-built indexes — everything an
              agent needs to navigate a codebase without reading raw files.<br /><br />
              Benchmarked across 14 repos: <strong style={{ color: '#f1f5f9' }}>36% average token savings</strong>,{' '}
              <strong style={{ color: '#f1f5f9' }}>100% function recall</strong>,{' '}
              <strong style={{ color: '#f1f5f9' }}>69% semantic retention</strong> vs raw source (Gemini 2.5 Flash judge).
            </div>
          </div>
        </div>
      </div>

      {/* ── Modes ── */}
      <div style={S.section}>
        <div style={S.sectionLabel}>Trace Modes</div>
        <h2 style={S.sectionTitle}>Three ways to trace.</h2>
        <p style={S.sectionSub}>Start with Sim — no setup needed. Upgrade to OTel or Live when you need real data.</p>
        <div style={S.threeCol}>
          <div style={S.modeCard}>
            <div style={S.modeName}>SIM</div>
            <div style={S.modeTitle}>Static call graph simulation</div>
            <div style={S.modeBody}>
              Walks the parsed call graph and generates a synthetic execution trace with
              realistic I/O values. No running service required — works on any public repo instantly.
            </div>
            <div style={S.modeReq}>Requires: any public GitHub URL</div>
          </div>
          <div style={S.modeCard}>
            <div style={S.modeName}>OTEL</div>
            <div style={S.modeTitle}>Real OpenTelemetry spans</div>
            <div style={S.modeBody}>
              Receives live spans from your running service via the OTel SDK. Point your
              collector at Codeflow's ingest endpoint — real timing, real values, real errors.
            </div>
            <div style={S.modeReq}>Requires: OTel SDK pointed at Codeflow</div>
          </div>
          <div style={S.modeCard}>
            <div style={S.modeName}>LIVE</div>
            <div style={S.modeTitle}>sys.settrace instrumentation</div>
            <div style={S.modeBody}>
              Attaches Python's <code style={{ color: '#4ade80' }}>sys.settrace</code> directly to a local
              process. Captures every function call, argument, and return value with zero
              code changes.
            </div>
            <div style={S.modeReq}>Requires: local repo + run command</div>
          </div>
        </div>
      </div>

      {/* ── Benchmark ── */}
      <div id="benchmark" style={S.section}>
        <div style={S.sectionLabel}>Benchmark</div>
        <h2 style={S.sectionTitle}>Measured. Not claimed.</h2>
        <p style={S.sectionSub}>
          14 repos, 15,000+ functions, 70 functions judged by Gemini 2.5 Flash.
          Three independent passes: token efficiency, ground-truth recall, semantic retention.
        </p>

        <div style={S.statGrid}>
          <div style={S.statCell}>
            <div style={S.statNum}>36%</div>
            <div style={S.statLabel}>avg token savings</div>
          </div>
          <div style={S.statCell}>
            <div style={S.statNum}>100%</div>
            <div style={S.statLabel}>function recall</div>
          </div>
          <div style={S.statCell}>
            <div style={S.statNum}>69%</div>
            <div style={S.statLabel}>semantic retention</div>
          </div>
          <div style={S.statCell}>
            <div style={S.statNum}>4.6×</div>
            <div style={S.statLabel}>best compression (rich)</div>
          </div>
        </div>

        <div style={{ marginBottom: 12, fontSize: 11, color: '#475569', letterSpacing: '0.1em' }}>
          TOKEN SAVINGS PER REPO
        </div>
        {BENCH_DATA.map((row) => (
          <div key={row.repo} style={S.benchRow}>
            <div style={S.benchRepo}>{row.repo}</div>
            <div style={S.benchBar}>
              <div style={{
                position: 'absolute',
                left: 0, top: 0, bottom: 0,
                width: `${Math.max(0, row.saved)}%`,
                background: row.saved >= 50 ? '#22c55e' : '#4ade80',
                opacity: 0.8,
              }} />
            </div>
            <div style={S.benchVal}>{row.saved.toFixed(1)}%</div>
          </div>
        ))}

        <div style={{ marginTop: 32, textAlign: 'center' }}>
          <a
            href="https://github.com/onedownz01/Thirdwheel-codeflow/blob/main/benchmark/FINAL_BENCHMARK_REPORT.md"
            target="_blank"
            rel="noreferrer"
            style={{ ...S.ctaSecondary, display: 'inline-block' }}
          >
            VIEW FULL REPORT →
          </a>
        </div>
      </div>

      {/* ── ParsedRepo Schema ── */}
      <div style={S.section}>
        <div style={S.sectionLabel}>For Agents — Schema</div>
        <h2 style={S.sectionTitle}>What an agent receives.</h2>
        <p style={S.sectionSub}>
          One API call to <code style={{ color: '#4ade80' }}>GET /intents?repo=owner/repo</code> returns
          a fully structured ParsedRepo. No prompt engineering needed.
        </p>
        <div style={{ ...S.codeBlock, marginBottom: 24 }}>
          <span style={S.codeComment}># Agent usage</span><br />
          <span style={S.codeGreen}>GET</span> /intents?repo=<span style={S.codeGreen}>tiangolo/fastapi</span><br />
          <br />
          <span style={S.codeComment}># Returns ParsedRepo JSON with:</span>
        </div>
        <div style={{ ...S.card, padding: '8px 24px' }}>
          {SCHEMA_FIELDS.map((f) => (
            <div key={f.name} style={S.schemaField}>
              <span style={S.fieldName}>{f.name}</span>
              <span style={S.fieldDesc}>{f.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Docs ── */}
      <div id="docs" style={S.section}>
        <div style={S.sectionLabel}>Documentation</div>
        <h2 style={S.sectionTitle}>Get running in 60 seconds.</h2>
        <p style={S.sectionSub}>Python 3.11+ and Node 18+ required. No database, no accounts.</p>

        <div style={{ ...S.codeBlock, marginBottom: 24 }}>
          <span style={S.codeComment}># One command</span><br />
          <span style={S.codeGreen}>./scripts/dev_local.sh</span>
          <br /><br />
          <span style={S.codeComment}># Or manual</span><br />
          python3 -m venv .venv && source .venv/bin/activate<br />
          pip install -r backend/requirements.txt<br />
          uvicorn backend.main:app --reload --port 8001<br />
          <br />
          <span style={S.codeComment}># Frontend (new terminal)</span><br />
          cd frontend && npm install && npm run dev
        </div>

        <div style={{ marginBottom: 20, fontSize: 11, color: '#475569', letterSpacing: '0.1em' }}>API REFERENCE</div>
        <div style={{ ...S.card, padding: '8px 24px' }}>
          {[
            ['GET', '/intents?repo={owner/repo}', 'All intents + ParsedRepo for a repository'],
            ['GET', '/occurrences?repo=...&intent_id=...', 'Call chain for a specific intent'],
            ['POST', '/trace/start', 'Start a new trace session'],
            ['POST', '/trace/ingest', 'Ingest OTel spans'],
            ['GET', '/trace/{session_id}', 'Fetch trace events'],
            ['POST', '/fix', 'AI fix suggestion (opt-in, requires ANTHROPIC_API_KEY)'],
            ['WS', '/ws/trace/{session_id}', 'Live trace event stream'],
          ].map(([method, path, desc]) => (
            <div key={path} style={{ ...S.schemaField, gridTemplateColumns: '60px 280px 1fr' }}>
              <span style={{ color: method === 'GET' ? '#4ade80' : method === 'WS' ? '#a78bfa' : '#fb923c', fontSize: 11, fontWeight: 700 }}>{method}</span>
              <span style={{ color: '#e2e8f0', fontSize: 11 }}>{path}</span>
              <span style={S.fieldDesc}>{desc}</span>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 24, ...S.codeBlock }}>
          <span style={S.codeComment}># Optional env vars (.env in project root)</span><br />
          GITHUB_TOKEN=ghp_...          <span style={S.codeComment}># higher rate limits on large repos</span><br />
          ANTHROPIC_API_KEY=sk-ant-...  <span style={S.codeComment}># AI fix suggestions (never auto-called)</span>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer style={S.footer}>
        <span>
          made by foundarv enggers for internal usecase now for all —{' '}
          <a href="https://foundarv.com" target="_blank" rel="noreferrer" style={{ color: '#4ade80', textDecoration: 'none' }}>
            foundarv.com
          </a>
        </span>
        <span style={{ color: '#1e293b' }}>codeflow · open source</span>
      </footer>
    </div>
  );
}
