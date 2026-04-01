import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/* ─────────────────────────────────────────────────────────────
   Agentbase design system
   bg #0a0a0a · Geist + DM Mono · radius 0 · weight 300/500
───────────────────────────────────────────────────────────── */

const C = {
  bg:      '#0a0a0a',
  bg2:     '#111111',
  bg3:     '#1a1a1a',
  border:  'rgba(255,255,255,0.07)',
  border2: 'rgba(255,255,255,0.13)',
  text:    '#f0f0f0',
  muted:   '#616161',
  dim:     '#2e2e2e',
};

const sans: React.CSSProperties = { fontFamily: "'Geist', system-ui, sans-serif" };
const mono: React.CSSProperties = { fontFamily: "'DM Mono', 'SF Mono', monospace" };

const gridBg: React.CSSProperties = {
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px)
  `,
  backgroundSize: '56px 56px',
};

// ── Corner brackets ──────────────────────────────────────────
function Brackets({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  const b = 'rgba(255,255,255,0.25)';
  const h: React.CSSProperties = { position: 'absolute', width: 10, height: 1, background: b };
  const v: React.CSSProperties = { position: 'absolute', width: 1, height: 10, background: b };
  return (
    <div style={{ position: 'relative', ...style }}>
      <span style={{ position: 'absolute', top: -1, left: -1 }}>
        <span style={{ ...h, top: 0, left: 0 }} /><span style={{ ...v, top: 0, left: 0 }} />
      </span>
      <span style={{ position: 'absolute', top: -1, right: -1 }}>
        <span style={{ ...h, top: 0, right: 0 }} /><span style={{ ...v, top: 0, right: 0 }} />
      </span>
      <span style={{ position: 'absolute', bottom: -1, left: -1 }}>
        <span style={{ ...h, bottom: 0, left: 0 }} /><span style={{ ...v, bottom: 0, left: 0 }} />
      </span>
      <span style={{ position: 'absolute', bottom: -1, right: -1 }}>
        <span style={{ ...h, bottom: 0, right: 0 }} /><span style={{ ...v, bottom: 0, right: 0 }} />
      </span>
      {children}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ ...mono, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: C.muted, margin: '0 0 20px', fontWeight: 500 }}>
      {children}
    </p>
  );
}

function SectionDivider() {
  return <div style={{ borderTop: `1px solid ${C.border}`, margin: '96px 0' }} />;
}

// ── Data ─────────────────────────────────────────────────────
const FEATURES = [
  { tag: 'PARSE',     title: 'Paste a URL, get a graph',   body: 'Any public GitHub repo. Tree-sitter parses the AST. Python and TypeScript/React supported.' },
  { tag: 'INTENTS',   title: 'Entry points, not file trees', body: 'Routes, handlers, CLI commands, class APIs — each is an Intent. That\'s where tracing starts.' },
  { tag: 'TRACE',     title: 'Click an intent, see the path', body: 'Full call chain animates in the graph. File, line number, and I/O on every node.' },
  { tag: 'SIM',       title: 'No server required',         body: 'Static graph walk. Follows calls from source and simulates the execution path.' },
  { tag: 'OTEL',      title: 'Real spans from your service', body: 'Point your OTel exporter at Codeflow. Real timing, real errors, real return values.' },
  { tag: 'SETTRACE',  title: 'Attach to a local process',  body: 'sys.settrace hooks into Python. Every call and return captured. No code changes.' },
  { tag: 'AGENTS',    title: 'Structured output for agents', body: 'One JSON object: all functions, types, call edges, fn_type_index, file_index. 36% fewer tokens.' },
  { tag: 'BENCHMARK', title: '21 repos benchmarked',        body: '14 scored by Gemini 2.5 Flash. psf/requests: 90% retention. Avg: 69%. 36% token savings.' },
  { tag: 'MIT',       title: 'Self-host it',               body: 'No accounts. No telemetry in sim mode. The only network call is to GitHub.' },
];

const BENCH = [
  { repo: 'psf/requests',                        saved: '31%', ret: '90%' },
  { repo: 'Textualize/rich',                     saved: '78%', ret: '83%' },
  { repo: 'pallets/flask',                       saved: '16%', ret: '80%' },
  { repo: 'fastapi/full-stack-fastapi-template', saved: '58%', ret: '77%' },
  { repo: 'encode/httpx',                        saved: '40%', ret: '72%' },
  { repo: 'sqlalchemy/sqlalchemy',               saved: '43%', ret: '64%' },
];

const TERMINAL_LINES = [
  { t: 'cmd',     s: '$ codeflow parse tiangolo/fastapi' },
  { t: 'muted',   s: '  cloning · tree-sitter · 392 functions indexed' },
  { t: 'gap',     s: '' },
  { t: 'key',     s: '  intents   44' },
  { t: 'key',     s: '  routes    18' },
  { t: 'key',     s: '  handlers  11' },
  { t: 'key',     s: '  auth       3' },
  { t: 'gap',     s: '' },
  { t: 'muted',   s: '  token delta  −36%' },
  { t: 'muted',   s: '  recall       100%' },
  { t: 'gap',     s: '' },
  { t: 'cmd',     s: '$ ready  →  ParsedRepo serialized' },
];

const CODE_SCHEMA = `{
  functions: [{
    id:          "fn:a1b2c3",
    name:        "create_item",
    type:        "route",
    file:        "app/main.py",
    line:        42,
    return_type: "Item",
    docstring:   "Create a new item.",
    calls:       ["fn:d4e5f6", ...]
  }],
  intents:       [...],       // user-facing actions
  fn_type_index: {            // O(1) by type
    "route": ["fn:a1b2c3", ...]
  },
  file_index: {               // O(1) by file
    "app/main.py": [...]
  }
}`;

const INSTALL = `# Python 3.11+  ·  Node 18+

./scripts/dev_local.sh

# or step by step
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8001

# frontend  (new terminal)
cd frontend && npm install && npm run dev`;

const API_ROUTES = [
  { m: 'POST', path: '/parse',                       desc: 'Parse a repo → full ParsedRepo JSON' },
  { m: 'GET',  path: '/intents?repo={owner/repo}',  desc: 'Intents list for an already-parsed repo' },
  { m: 'GET',  path: '/occurrences?intent_id=…',    desc: 'Call chain for one intent' },
  { m: 'POST', path: '/trace/start',                 desc: 'Start a trace session' },
  { m: 'POST', path: '/trace/ingest',                desc: 'Ingest OTel spans' },
  { m: 'GET',  path: '/trace/{session_id}',          desc: 'Fetch events for a session' },
  { m: 'WS',   path: '/ws/trace/{session_id}',       desc: 'Live event stream' },
  { m: 'POST', path: '/fix',                         desc: 'AI fix suggestion (opt-in)' },
];

// ── Shared code/terminal block ────────────────────────────────
function CodeBlock({ code, filename }: { code: string; filename?: string }) {
  return (
    <Brackets>
      <div style={{ border: `1px solid ${C.border}`, overflow: 'hidden' }}>
        {filename && (
          <div style={{
            padding: '7px 14px', borderBottom: `1px solid ${C.border}`,
            background: C.bg2, display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ ...mono, fontSize: 10, color: C.muted, fontWeight: 300, letterSpacing: '0.04em' }}>{filename}</span>
          </div>
        )}
        <pre style={{
          ...mono, fontSize: 12, lineHeight: 1.85, padding: '20px',
          margin: 0, background: C.bg2, color: C.muted,
          overflowX: 'auto', whiteSpace: 'pre', fontWeight: 300,
        }}>
          {code.split('\n').map((line, i) => {
            const isComment = line.trimStart().startsWith('#') || line.includes('// ');
            const isBright  = line.startsWith('{') || line.startsWith('}') || line.includes('ParsedRepo') || line.startsWith('$');
            return (
              <span key={i} style={{ display: 'block', color: isComment ? C.dim : isBright ? C.text : C.muted }}>
                {line || '\u00a0'}
              </span>
            );
          })}
        </pre>
      </div>
    </Brackets>
  );
}

// ── Main ─────────────────────────────────────────────────────
export default function LandingPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'qs' | 'api'>('qs');

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Geist:wght@300;400;500;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); }
        body { background: #0a0a0a; }
      `}</style>

      <div style={{ ...sans, background: C.bg, color: C.text, minHeight: '100vh', fontWeight: 300 }}>

        {/* ── Nav ── */}
        <nav style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
          background: 'rgba(10,10,10,0.88)',
          backdropFilter: 'blur(16px)',
          borderBottom: `1px solid ${C.border}`,
          display: 'flex', alignItems: 'stretch', height: 44,
        }}>
          <div style={{
            display: 'flex', alignItems: 'center',
            padding: '0 24px', borderRight: `1px solid ${C.border}`,
            flexShrink: 0,
          }}>
            <span style={{ ...mono, fontSize: 12, fontWeight: 500, color: C.text, letterSpacing: '0.08em' }}>
              CODEFLOW
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'stretch', flex: 1 }}>
            {[
              { label: 'HOW IT WORKS', id: 'how' },
              { label: 'FEATURES',     id: 'features' },
              { label: 'FOR AGENTS',   id: 'agents' },
              { label: 'BENCHMARK',    id: 'benchmark' },
              { label: 'DOCS',         id: 'docs' },
            ].map(({ label, id }) => (
              <button key={label}
                onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })}
                style={{
                  ...mono, background: 'none', border: 'none',
                  borderRight: `1px solid ${C.border}`,
                  cursor: 'pointer', fontSize: 10, fontWeight: 500,
                  color: C.muted, padding: '0 16px',
                  letterSpacing: '0.06em', whiteSpace: 'nowrap',
                  transition: 'color 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.color = C.text)}
                onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
              >{label}</button>
            ))}
          </div>

          <button
            onClick={() => navigate('/launch')}
            style={{
              ...mono, background: C.text, color: C.bg,
              border: 'none', cursor: 'pointer',
              fontSize: 10, fontWeight: 500,
              padding: '0 24px', letterSpacing: '0.08em',
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >LAUNCH APP ↗</button>
        </nav>

        {/* ── Hero ── */}
        <section style={{
          paddingTop: 44, minHeight: '100vh',
          display: 'flex', alignItems: 'center',
          ...gridBg,
        }}>
          <div style={{ maxWidth: 1100, margin: '0 auto', padding: '80px 48px', width: '100%' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 80, alignItems: 'center' }}>

              {/* Left copy */}
              <div>
                {/* Tag */}
                <div style={{
                  ...mono,
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  border: `1px solid ${C.border2}`,
                  padding: '5px 12px',
                  fontSize: 10, fontWeight: 500,
                  color: C.muted, letterSpacing: '0.06em',
                  marginBottom: 32,
                }}>
                  <span style={{ color: C.text }}>◈</span>
                  BENCHMARK — 14 REPOS · 15K+ FUNCTIONS
                </div>

                <h1 style={{
                  fontSize: 'clamp(36px, 4vw, 60px)',
                  fontWeight: 300,
                  lineHeight: 1.08,
                  letterSpacing: '-0.04em',
                  color: C.text,
                  marginBottom: 24,
                }}>
                  Parse code.<br />
                  Trace intent.<br />
                  Feed agents.
                </h1>

                <p style={{
                  fontSize: 15, fontWeight: 300,
                  color: C.muted, lineHeight: 1.75,
                  marginBottom: 40, maxWidth: 420,
                }}>
                  Give it a GitHub repo. It maps every function, every call, every entry point.
                  The output is a structured JSON your agent can actually use — not a pile of files.
                </p>

                <div style={{ display: 'flex', gap: 1 }}>
                  <button
                    onClick={() => navigate('/launch')}
                    style={{
                      ...mono, background: C.text, color: C.bg,
                      border: 'none', cursor: 'pointer',
                      padding: '12px 28px', fontSize: 11,
                      fontWeight: 500, letterSpacing: '0.06em',
                      transition: 'opacity 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
                    onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
                  >OPEN APP</button>
                  <a
                    href="https://github.com/onedownz01/Thirdwheel-codeflow"
                    target="_blank" rel="noreferrer"
                    style={{
                      ...mono, background: 'transparent',
                      color: C.muted,
                      border: `1px solid ${C.border2}`,
                      borderLeft: `1px solid ${C.border2}`,
                      cursor: 'pointer', padding: '12px 28px',
                      fontSize: 11, fontWeight: 500,
                      letterSpacing: '0.06em', textDecoration: 'none',
                      display: 'inline-flex', alignItems: 'center',
                      transition: 'color 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.color = C.text)}
                    onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
                  >VIEW SOURCE</a>
                </div>
              </div>

              {/* Right terminal */}
              <Brackets>
                <div style={{ border: `1px solid ${C.border}`, overflow: 'hidden' }}>
                  <div style={{
                    padding: '8px 14px', background: C.bg2,
                    borderBottom: `1px solid ${C.border}`,
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    {['#3a3a3a', '#3a3a3a', '#3a3a3a'].map((c, i) => (
                      <span key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: c, display: 'inline-block' }} />
                    ))}
                    <span style={{ ...mono, fontSize: 10, color: C.muted, marginLeft: 6, fontWeight: 300, letterSpacing: '0.04em' }}>terminal</span>
                  </div>
                  <div style={{ background: C.bg2, padding: '20px', fontFamily: "'DM Mono', monospace" }}>
                    {TERMINAL_LINES.map((line, i) => (
                      <div key={i} style={{
                        fontSize: 12, lineHeight: 1.9, fontWeight: 300,
                        color: line.t === 'cmd' ? C.text : line.t === 'key' ? '#9a9a9a' : C.dim,
                        paddingLeft: line.t === 'gap' ? 0 : undefined,
                        minHeight: line.t === 'gap' ? 10 : undefined,
                      }}>
                        {line.s || ''}
                      </div>
                    ))}
                  </div>
                </div>
              </Brackets>

            </div>
          </div>
        </section>

        {/* ── Stats strip ── */}
        <div style={{ borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}` }}>
          <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: C.border }}>
            {[
              { n: '36%',   l: 'avg token savings' },
              { n: '100%',  l: 'function recall' },
              { n: '69%',   l: 'semantic retention' },
              { n: '21',    l: 'repos benchmarked' },
            ].map(s => (
              <div key={s.n} style={{
                background: C.bg, padding: '28px 24px', textAlign: 'center' as const,
              }}>
                <div style={{ ...mono, fontSize: 28, fontWeight: 500, color: C.text, letterSpacing: '-0.02em' }}>{s.n}</div>
                <div style={{ ...mono, fontSize: 9, color: C.muted, marginTop: 6, letterSpacing: '0.08em', fontWeight: 300 }}>{s.l.toUpperCase()}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Content ── */}
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 48px' }}>

          {/* ── How it works ── */}
          <section id="how" style={{ paddingTop: 96 }}>
            <Label>HOW IT WORKS</Label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'start' }}>
              <div>
                <h2 style={{ fontSize: 28, fontWeight: 300, color: C.text, marginBottom: 16, letterSpacing: '-0.02em', lineHeight: 1.2 }}>
                  Starts from what users actually do
                </h2>
                <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.85, marginBottom: 16 }}>
                  Most parsers give you a file tree. Codeflow starts from entry points — routes,
                  handlers, CLI commands — and builds the call graph outward from there.
                </p>
                <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.85 }}>
                  Three trace modes: static walk (no server), live sys.settrace attach, or real
                  OTel spans. Same graph view for all three.
                </p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 1, background: C.border }}>
                {[
                  { step: '01', label: 'PARSE',    desc: 'Clone. Tree-sitter extracts every function — name, type, params, return type, calls.' },
                  { step: '02', label: 'CLASSIFY', desc: 'Each function gets a role: route, handler, util, model, auth, test.' },
                  { step: '03', label: 'ANCHOR',   desc: 'All entry points become Intents. These are the roots of the call trees.' },
                  { step: '04', label: 'TRACE',    desc: 'Walk from any intent. Static, live attach, or OTel. Renders in the graph.' },
                ].map(s => (
                  <div key={s.step} style={{
                    background: C.bg, padding: '18px 20px',
                    display: 'grid', gridTemplateColumns: '32px 68px 1fr', gap: 12, alignItems: 'start',
                    transition: 'background 0.12s',
                  }}
                    onMouseEnter={e => (e.currentTarget.style.background = C.bg2)}
                    onMouseLeave={e => (e.currentTarget.style.background = C.bg)}
                  >
                    <span style={{ ...mono, fontSize: 9, color: C.dim, fontWeight: 500, paddingTop: 2 }}>{s.step}</span>
                    <span style={{ ...mono, fontSize: 9, color: C.muted, fontWeight: 500, letterSpacing: '0.06em', paddingTop: 2 }}>{s.label}</span>
                    <span style={{ fontSize: 12, color: C.muted, fontWeight: 300, lineHeight: 1.7 }}>{s.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <SectionDivider />

          {/* ── Features ── */}
          <section id="features">
            <Label>FEATURES</Label>
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 1, background: C.border, border: `1px solid ${C.border}`,
            }}>
              {FEATURES.map(f => (
                <div key={f.tag}
                  style={{ background: C.bg, padding: '24px 20px', transition: 'background 0.12s', cursor: 'default' }}
                  onMouseEnter={e => (e.currentTarget.style.background = C.bg2)}
                  onMouseLeave={e => (e.currentTarget.style.background = C.bg)}
                >
                  <div style={{ ...mono, fontSize: 9, color: C.dim, fontWeight: 500, letterSpacing: '0.1em', marginBottom: 12 }}>{f.tag}</div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: C.text, marginBottom: 8, lineHeight: 1.3 }}>{f.title}</div>
                  <div style={{ fontSize: 12, fontWeight: 300, color: C.muted, lineHeight: 1.75 }}>{f.body}</div>
                </div>
              ))}
            </div>
          </section>

          <SectionDivider />

          {/* ── For Agents ── */}
          <section id="agents">
            <Label>FOR AGENTS</Label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'start' }}>
              <div>
                <h2 style={{ fontSize: 28, fontWeight: 300, color: C.text, marginBottom: 16, letterSpacing: '-0.02em', lineHeight: 1.2 }}>
                  One call. Everything your agent needs.
                </h2>
                <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.85, marginBottom: 16 }}>
                  <code style={{ ...mono, fontSize: 12, color: C.text, background: C.bg3, padding: '2px 6px', fontWeight: 300 }}>POST /parse</code> returns
                  a{' '}<code style={{ ...mono, fontSize: 12, color: C.text, background: C.bg3, padding: '2px 6px', fontWeight: 300 }}>ParsedRepo</code>{' '}
                  — every function with its name, type, file, line, return type, docstring, and which functions it calls.
                </p>
                <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.85, marginBottom: 24 }}>
                  <code style={{ ...mono, fontSize: 12, color: C.text, background: C.bg3, padding: '2px 6px', fontWeight: 300 }}>fn_type_index</code> and{' '}
                  <code style={{ ...mono, fontSize: 12, color: C.text, background: C.bg3, padding: '2px 6px', fontWeight: 300 }}>file_index</code> are
                  pre-built so your agent doesn't have to scan the full list.
                </p>
                {/* mini stat row */}
                <div style={{ display: 'flex', gap: 1, background: C.border }}>
                  {[['36%', 'token savings'], ['100%', 'recall'], ['69%', 'retention']].map(([n, l]) => (
                    <div key={n} style={{ background: C.bg, flex: 1, padding: '14px 12px' }}>
                      <div style={{ ...mono, fontSize: 18, fontWeight: 500, color: C.text }}>{n}</div>
                      <div style={{ ...mono, fontSize: 9, color: C.muted, marginTop: 4, letterSpacing: '0.06em', fontWeight: 300 }}>{l.toUpperCase()}</div>
                    </div>
                  ))}
                </div>
              </div>
              <CodeBlock code={CODE_SCHEMA} filename="ParsedRepo schema" />
            </div>
          </section>

          <SectionDivider />

          {/* ── Benchmark ── */}
          <section id="benchmark">
            <Label>BENCHMARK — 2026-03-30</Label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 64, alignItems: 'start' }}>
              <div>
                <h2 style={{ fontSize: 28, fontWeight: 300, color: C.text, marginBottom: 16, letterSpacing: '-0.02em', lineHeight: 1.2 }}>
                  Measured. Not claimed.
                </h2>
                <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.85, marginBottom: 16 }}>
                  21 repos, 15,000+ functions. Each repo parsed into ParsedRepo and compared to
                  raw source on three axes: token count, function recall, semantic retention.
                </p>
                <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.85 }}>
                  Retention scored by Gemini 2.5 Flash — not Claude, not the model that built the
                  parser. 5 functions sampled per repo, judged on signature accuracy,
                  docstring fidelity, and call-chain completeness.
                </p>
              </div>

              <Brackets>
                <div style={{ border: `1px solid ${C.border}`, overflow: 'hidden' }}>
                  <div style={{
                    display: 'grid', gridTemplateColumns: '1fr 56px 72px',
                    padding: '8px 16px', background: C.bg2,
                    borderBottom: `1px solid ${C.border}`,
                    ...mono, fontSize: 9, letterSpacing: '0.1em', color: C.muted, fontWeight: 500,
                  }}>
                    <span>REPO</span>
                    <span style={{ textAlign: 'right' as const }}>SAVED</span>
                    <span style={{ textAlign: 'right' as const }}>RETENTION</span>
                  </div>
                  {BENCH.map((row, i) => (
                    <div key={row.repo}
                      style={{
                        display: 'grid', gridTemplateColumns: '1fr 56px 72px',
                        padding: '10px 16px',
                        borderBottom: i < BENCH.length - 1 ? `1px solid ${C.border}` : 'none',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = C.bg2)}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      <span style={{ ...mono, fontSize: 11, color: C.text, fontWeight: 300 }}>{row.repo}</span>
                      <span style={{ ...mono, fontSize: 11, color: C.muted, textAlign: 'right' as const, fontWeight: 300 }}>{row.saved}</span>
                      <span style={{ ...mono, fontSize: 11, color: C.text, textAlign: 'right' as const, fontWeight: 500 }}>{row.ret}</span>
                    </div>
                  ))}
                  <div style={{
                    padding: '9px 16px', borderTop: `1px solid ${C.border}`,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <span style={{ ...mono, fontSize: 10, color: C.muted, fontWeight: 300 }}>6 of 14 shown</span>
                    <a href="https://github.com/onedownz01/Thirdwheel-codeflow/blob/main/benchmark/FINAL_BENCHMARK_REPORT.md"
                      target="_blank" rel="noreferrer"
                      style={{ ...mono, fontSize: 10, color: C.muted, textDecoration: 'none', fontWeight: 300, transition: 'color 0.15s' }}
                      onMouseEnter={e => (e.currentTarget.style.color = C.text)}
                      onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
                    >full report →</a>
                  </div>
                </div>
              </Brackets>
            </div>
          </section>

          <SectionDivider />

          {/* ── Docs ── */}
          <section id="docs">
            <Label>DOCS</Label>
            <h2 style={{ fontSize: 28, fontWeight: 300, color: C.text, marginBottom: 12, letterSpacing: '-0.02em' }}>
              Up in 60 seconds.
            </h2>
            <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.85, marginBottom: 32, maxWidth: 560 }}>
              Python 3.11+ and Node 18+. No database. No config file for sim mode.
            </p>

            {/* Tabs */}
            <div style={{ display: 'flex', borderBottom: `1px solid ${C.border}`, marginBottom: 0 }}>
              {([['qs', 'QUICK START'], ['api', 'API REFERENCE']] as const).map(([key, lbl]) => (
                <button key={key}
                  onClick={() => setActiveTab(key)}
                  style={{
                    ...mono, background: 'none', border: 'none',
                    borderBottom: activeTab === key ? `1px solid ${C.text}` : '1px solid transparent',
                    cursor: 'pointer', fontSize: 10, fontWeight: 500,
                    letterSpacing: '0.06em',
                    color: activeTab === key ? C.text : C.muted,
                    padding: '8px 18px 10px', marginBottom: -1,
                    transition: 'color 0.15s',
                  }}
                >{lbl}</button>
              ))}
            </div>

            <div style={{ maxWidth: 680, marginTop: 0 }}>
              {activeTab === 'qs'
                ? <CodeBlock code={INSTALL} filename="terminal" />
                : (
                  <Brackets>
                    <div style={{ border: `1px solid ${C.border}`, marginTop: 0 }}>
                      {API_ROUTES.map((r, i) => (
                        <div key={r.path}
                          style={{
                            display: 'grid', gridTemplateColumns: '40px 1fr',
                            gap: 14, padding: '11px 16px',
                            borderBottom: i < API_ROUTES.length - 1 ? `1px solid ${C.border}` : 'none',
                            transition: 'background 0.1s',
                          }}
                          onMouseEnter={e => (e.currentTarget.style.background = C.bg2)}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                        >
                          <span style={{ ...mono, fontSize: 9, fontWeight: 500, color: C.muted, background: C.bg3, padding: '3px 4px', textAlign: 'center' as const, letterSpacing: '0.04em', alignSelf: 'flex-start', marginTop: 1 }}>
                            {r.m}
                          </span>
                          <div>
                            <div style={{ ...mono, fontSize: 12, color: C.text, marginBottom: 3, fontWeight: 300 }}>{r.path}</div>
                            <div style={{ fontSize: 11, color: C.muted, fontWeight: 300 }}>{r.desc}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Brackets>
                )
              }
            </div>
          </section>

          {/* ── Footer ── */}
          <div style={{
            borderTop: `1px solid ${C.border}`,
            margin: '96px 0 0', padding: '28px 0 48px',
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', flexWrap: 'wrap', gap: 8,
          }}>
            <span style={{ ...mono, fontSize: 10, color: C.dim, fontWeight: 300 }}>codeflow · mit license</span>
            <a href="https://github.com/onedownz01/Thirdwheel-codeflow" target="_blank" rel="noreferrer"
              style={{ ...mono, fontSize: 10, color: C.muted, textDecoration: 'none', fontWeight: 300, transition: 'color 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.color = C.text)}
              onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
            >github →</a>
          </div>

        </div>{/* end content */}
      </div>
    </>
  );
}
