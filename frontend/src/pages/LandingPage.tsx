import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/* ─────────────────────────────────────────────────────────────
   Agentbase design system — exact spec
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

const sans: React.CSSProperties  = { fontFamily: "'Geist', system-ui, sans-serif" };
const mono: React.CSSProperties  = { fontFamily: "'DM Mono', 'SF Mono', monospace" };

// ── Corner brackets ──────────────────────────────────────────
function Brackets({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  const b = 'rgba(255,255,255,0.3)';
  const corner = (top: boolean, left: boolean): React.CSSProperties => ({
    position: 'absolute',
    [top ? 'top' : 'bottom']: -1,
    [left ? 'left' : 'right']: -1,
  });
  const h: React.CSSProperties = { position: 'absolute', width: 10, height: 1, background: b };
  const v: React.CSSProperties = { position: 'absolute', width: 1, height: 10, background: b };
  return (
    <div style={{ position: 'relative', ...style }}>
      {/* TL */}
      <span style={{ ...corner(true, true) }}><span style={{ ...h, top: 0, left: 0 }} /><span style={{ ...v, top: 0, left: 0 }} /></span>
      {/* TR */}
      <span style={{ ...corner(true, false) }}><span style={{ ...h, top: 0, right: 0 }} /><span style={{ ...v, top: 0, right: 0 }} /></span>
      {/* BL */}
      <span style={{ ...corner(false, true) }}><span style={{ ...h, bottom: 0, left: 0 }} /><span style={{ ...v, bottom: 0, left: 0 }} /></span>
      {/* BR */}
      <span style={{ ...corner(false, false) }}><span style={{ ...h, bottom: 0, right: 0 }} /><span style={{ ...v, bottom: 0, right: 0 }} /></span>
      {children}
    </div>
  );
}

// ── Label / mono tag ─────────────────────────────────────────
function Label({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ ...mono, fontSize: 10, letterSpacing: '0.06em', textTransform: 'uppercase', color: C.muted, margin: '0 0 20px', fontWeight: 500 }}>
      {children}
    </p>
  );
}

function Divider() {
  return <div style={{ borderTop: `1px solid ${C.border}`, margin: '80px 0' }} />;
}

// ── Data ─────────────────────────────────────────────────────
const FEATURES = [
  { n: '01', tag: 'PARSE',     title: 'Any GitHub repo.',          body: 'Paste a URL. Tree-sitter parses the AST in seconds. Python and TypeScript/React supported.' },
  { n: '02', tag: 'INTENTS',   title: 'Every user-facing action.', body: 'Routes, handlers, CLI commands, class APIs — all surfaced as named Intents with confidence scores.' },
  { n: '03', tag: 'TRACE',     title: 'Full call chain, animated.', body: 'Click an intent. Watch the execution path animate. File, line, and I/O on every block.' },
  { n: '04', tag: 'SIM',       title: 'Static graph simulation.',  body: 'No running service needed. Codeflow walks the call graph and generates a synthetic execution trace.' },
  { n: '05', tag: 'OTEL',      title: 'Real spans from OTel.',     body: 'Receive live OpenTelemetry spans from your service. Real timing, real errors, real values.' },
  { n: '06', tag: 'LIVE',      title: 'sys.settrace, zero setup.', body: 'Attach to a local process. Capture every call, argument, and return — no code changes.' },
  { n: '07', tag: 'AGENTS',    title: 'ParsedRepo for LLMs.',      body: '36% fewer tokens. 100% recall. Pre-built fn_type_index and file_index for O(1) lookups.' },
  { n: '08', tag: 'BENCHMARK', title: '14 repos. 15k+ functions.', body: 'Gemini 2.5 Flash judges retention. 69% average vs raw source. psf/requests hits 90%.' },
  { n: '09', tag: 'OSS',       title: 'Open source.',              body: 'MIT. Run it locally. No accounts, no telemetry in Sim mode. The only external call is GitHub.' },
];

const BENCH = [
  { repo: 'psf/requests',                        saved: '31%', ret: '90%' },
  { repo: 'Textualize/rich',                     saved: '78%', ret: '83%' },
  { repo: 'pallets/flask',                       saved: '16%', ret: '80%' },
  { repo: 'fastapi/full-stack-fastapi-template', saved: '58%', ret: '77%' },
  { repo: 'encode/httpx',                        saved: '40%', ret: '72%' },
  { repo: 'sqlalchemy/sqlalchemy',               saved: '43%', ret: '64%' },
];

const CODE = `GET /intents?repo=tiangolo/fastapi

→ ParsedRepo {
  functions: [{
    id:          "fn:a1b2c3",
    name:        "create_item",
    type:        "route",
    file:        "app/main.py",
    line:        42,
    return_type: "Item",
    docstring:   "Create a new item.",
    calls:       ["fn:d4e5f6", ...]
  }, ...],                       // 392 functions total
  intents:       [...],          // 44 user-facing actions
  fn_type_index: {               // O(1) lookup by type
    "route":   ["fn:a1b2c3", ...],
    "handler": [...],
    "auth":    [...]
  },
  file_index: {                  // O(1) lookup by file
    "app/main.py": ["fn:a1b2c3", ...]
  }
}`;

const INSTALL = `# Python 3.11+ · Node 18+
./scripts/dev_local.sh

# or manual
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8001

# frontend (new terminal)
cd frontend && npm install && npm run dev`;

const API_ROUTES = [
  { m: 'GET',  path: '/intents?repo={owner/repo}',       desc: 'Full ParsedRepo + all intents' },
  { m: 'GET',  path: '/occurrences?intent_id=…',         desc: 'Call chain for one intent' },
  { m: 'POST', path: '/trace/start',                      desc: 'Start a trace session' },
  { m: 'POST', path: '/trace/ingest',                     desc: 'Ingest OTel spans' },
  { m: 'GET',  path: '/trace/{session_id}',               desc: 'Fetch events' },
  { m: 'WS',   path: '/ws/trace/{session_id}',            desc: 'Live event stream' },
  { m: 'POST', path: '/fix',                              desc: 'AI fix suggestion (opt-in)' },
];

// ── Code block ───────────────────────────────────────────────
function CodeBlock({ code, filename }: { code: string; filename?: string }) {
  return (
    <Brackets style={{ marginBottom: 32 }}>
      <div style={{ border: `1px solid ${C.border}`, overflow: 'hidden' }}>
        {filename && (
          <div style={{
            padding: '8px 14px',
            borderBottom: `1px solid ${C.border}`,
            background: C.bg2,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ ...mono, fontSize: 11, color: C.muted, fontWeight: 300 }}>{filename}</span>
          </div>
        )}
        <pre style={{
          ...mono,
          fontSize: 13,
          lineHeight: 1.8,
          padding: '20px',
          margin: 0,
          background: C.bg2,
          color: C.muted,
          overflowX: 'auto',
          whiteSpace: 'pre',
          fontWeight: 300,
        }}>
          {code.split('\n').map((line, i) => {
            const isComment = line.trimStart().startsWith('#') || line.includes('// ');
            const isHeader = line.startsWith('GET') || line.startsWith('→') || line.startsWith('./') || line.startsWith('uvicorn');
            return (
              <span key={i} style={{
                display: 'block',
                color: isComment ? C.dim : isHeader ? C.text : C.muted,
              }}>
                {line}
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

  const gridBg: React.CSSProperties = {
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px)
    `,
    backgroundSize: '56px 56px',
  };

  return (
    <>
      {/* Global styles injected once */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Geist:wght@300;400;500;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); }
        body { background: #0a0a0a; }
      `}</style>

      <div style={{ ...sans, background: C.bg, color: C.text, minHeight: '100vh', fontWeight: 300, ...gridBg }}>

        {/* ── Nav ── */}
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
          background: 'rgba(10,10,10,0.9)',
          backdropFilter: 'blur(20px)',
          borderBottom: `1px solid ${C.border}`,
          display: 'flex', alignItems: 'stretch', height: 44,
          ...sans,
        }}>
          {/* Logo */}
          <div style={{
            display: 'flex', alignItems: 'center',
            padding: '0 24px',
            borderRight: `1px solid ${C.border}`,
            flexShrink: 0,
            gap: 8,
          }}>
            <span style={{ ...mono, fontSize: 12, fontWeight: 500, color: C.text, letterSpacing: '0.06em' }}>
              CODEFLOW
            </span>
          </div>

          {[
            { label: 'README',      id: 'readme' },
            { label: 'FEATURES',    id: 'features' },
            { label: 'BENCHMARK',   id: 'benchmark' },
            { label: 'DOCS',        id: 'docs' },
            { label: 'FOR AGENTS',  id: 'for-agents' },
          ].map(({ label, id }) => (
            <button key={label} onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })}
              style={{
                ...mono, background: 'none', border: 'none',
                borderRight: `1px solid ${C.border}`,
                cursor: 'pointer', fontSize: 10,
                fontWeight: 500, color: C.muted,
                padding: '0 18px', letterSpacing: '0.06em',
                whiteSpace: 'nowrap', transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = C.text)}
              onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
            >{label}</button>
          ))}

          <div style={{ flex: 1 }} />

          <button onClick={() => navigate('/app')}
            style={{
              ...mono, background: C.text, color: C.bg,
              border: 'none', cursor: 'pointer',
              fontSize: 10, fontWeight: 500,
              padding: '0 24px', letterSpacing: '0.08em',
              borderLeft: `1px solid ${C.border}`,
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >LAUNCH APP ↗</button>
        </div>

        {/* ── Split layout ── */}
        <div style={{ display: 'flex', paddingTop: 44, minHeight: '100vh' }}>

          {/* LEFT — sticky */}
          <div style={{
            width: '36%', flexShrink: 0,
            position: 'sticky', top: 44,
            height: 'calc(100vh - 44px)',
            display: 'flex', flexDirection: 'column',
            justifyContent: 'flex-end',
            padding: '48px 40px',
            borderRight: `1px solid ${C.border}`,
            background: C.bg,
            overflow: 'hidden',
          }}>
            {/* Grid bg letters */}
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0,
              fontSize: 360, fontWeight: 700,
              color: C.dim, opacity: 0.12,
              lineHeight: 1, letterSpacing: '-0.06em',
              userSelect: 'none', pointerEvents: 'none',
              fontFamily: 'system-ui',
            }}>CF</div>

            {/* Pill */}
            <div style={{
              ...mono,
              display: 'inline-flex', alignItems: 'center', gap: 8,
              background: C.bg3,
              border: `1px solid ${C.border2}`,
              padding: '5px 12px',
              fontSize: 10, fontWeight: 500,
              color: C.muted,
              letterSpacing: '0.06em',
              marginBottom: 28,
              width: 'fit-content',
            }}>
              ◈  BENCHMARK REPORT PUBLISHED →
            </div>

            {/* H1 */}
            <h1 style={{
              fontSize: 'clamp(30px, 3.5vw, 52px)',
              fontWeight: 300,
              lineHeight: 1.1,
              letterSpacing: '-0.03em',
              color: C.text,
              marginBottom: 20,
            }}>
              The most comprehensive code understanding tool
            </h1>

            <p style={{
              fontSize: 'clamp(13px, 1.3vw, 16px)',
              fontWeight: 300,
              color: C.muted,
              lineHeight: 1.7,
              marginBottom: 36,
            }}>
              Parse any GitHub repo. Trace every intent. Feed structured
              context to LLM agents — 36% fewer tokens, 100% recall.
            </p>

            <div style={{ display: 'flex', gap: 0 }}>
              <button onClick={() => navigate('/app')}
                style={{
                  ...mono, background: C.text, color: C.bg,
                  border: 'none', cursor: 'pointer',
                  padding: '11px 24px', fontSize: 11,
                  fontWeight: 500, letterSpacing: '0.06em',
                  transition: 'opacity 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
                onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
              >GET STARTED</button>
              <a href="https://github.com/onedownz01/Thirdwheel-codeflow"
                target="_blank" rel="noreferrer"
                style={{
                  ...mono, background: 'transparent', color: C.muted,
                  border: `1px solid ${C.border2}`,
                  borderLeft: 'none',
                  cursor: 'pointer', padding: '11px 24px',
                  fontSize: 11, fontWeight: 500,
                  letterSpacing: '0.06em', textDecoration: 'none',
                  display: 'inline-flex', alignItems: 'center',
                  transition: 'color 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.color = C.text)}
                onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
              >GITHUB</a>
            </div>
          </div>

          {/* RIGHT — scrollable */}
          <div style={{ flex: 1, padding: '64px 56px 100px', maxWidth: 760, overflowX: 'hidden' }}>

            {/* ── README ── */}
            <section id="readme">
              <Label>README</Label>
              <h2 style={{ fontSize: 22, fontWeight: 500, color: C.text, marginBottom: 12, letterSpacing: '-0.01em' }}>
                What is Codeflow?
              </h2>
              <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.8, marginBottom: 16 }}>
                Codeflow is an intent-anchored execution tracer. Paste any GitHub URL — it surfaces every
                user-facing action as a named Intent, then lets you trace the full call chain. Zero setup.
                No instrumentation required.
              </p>
              <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.8 }}>
                For LLM agents, Codeflow outputs a single{' '}
                <code style={{ ...mono, fontSize: 12, color: C.text, background: C.bg3, padding: '2px 6px', fontWeight: 300 }}>ParsedRepo</code>{' '}
                JSON object — functions, types, docstrings, call edges, and pre-built indexes — dramatically
                reducing the tokens needed to navigate a codebase.
              </p>
            </section>

            <Divider />

            {/* ── Features ── */}
            <section id="features">
              <Label>FEATURES</Label>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 1,
                background: C.border,
                border: `1px solid ${C.border}`,
              }}>
                {FEATURES.map(f => (
                  <div key={f.n}
                    style={{ background: C.bg, padding: '22px 18px', transition: 'background 0.12s', cursor: 'default' }}
                    onMouseEnter={e => (e.currentTarget.style.background = C.bg2)}
                    onMouseLeave={e => (e.currentTarget.style.background = C.bg)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                      <span style={{ ...mono, fontSize: 9, color: C.muted, letterSpacing: '0.1em', fontWeight: 500 }}>{f.n}</span>
                      <span style={{ ...mono, fontSize: 8, letterSpacing: '0.1em', color: C.muted, opacity: 0.5, fontWeight: 500 }}>{f.tag}</span>
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: C.text, marginBottom: 8, lineHeight: 1.3 }}>{f.title}</div>
                    <div style={{ fontSize: 12, fontWeight: 300, color: C.muted, lineHeight: 1.7 }}>{f.body}</div>
                  </div>
                ))}
              </div>
            </section>

            <Divider />

            {/* ── For Agents ── */}
            <section id="for-agents">
              <Label>FOR AGENTS — PARSED REPO</Label>
              <h2 style={{ fontSize: 22, fontWeight: 500, color: C.text, marginBottom: 12, letterSpacing: '-0.01em' }}>
                One API call. Full repo graph.
              </h2>
              <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.8, marginBottom: 28 }}>
                Every function with type classification, typed params, return type, docstring, and
                outbound calls. <code style={{ ...mono, fontSize: 12, color: C.text, background: C.bg3, padding: '2px 6px', fontWeight: 300 }}>fn_type_index</code> and{' '}
                <code style={{ ...mono, fontSize: 12, color: C.text, background: C.bg3, padding: '2px 6px', fontWeight: 300 }}>file_index</code> give
                agents O(1) lookups without scanning the full list.
              </p>
              <CodeBlock code={CODE} filename="GET /intents?repo=owner/repo" />

              {/* Stat pills */}
              <div style={{ display: 'flex', gap: 1, background: C.border, border: `1px solid ${C.border}` }}>
                {[
                  { n: '36%',   l: 'avg token savings' },
                  { n: '100%',  l: 'function recall' },
                  { n: '69%',   l: 'semantic retention' },
                  { n: '4.6×',  l: 'best compression' },
                ].map(s => (
                  <div key={s.n} style={{ background: C.bg, flex: 1, padding: '20px 16px', textAlign: 'center' as const }}>
                    <div style={{ ...mono, fontSize: 24, fontWeight: 500, color: C.text }}>{s.n}</div>
                    <div style={{ ...mono, fontSize: 9, color: C.muted, marginTop: 4, letterSpacing: '0.06em', fontWeight: 300 }}>{s.l}</div>
                  </div>
                ))}
              </div>
            </section>

            <Divider />

            {/* ── Benchmark ── */}
            <section id="benchmark">
              <Label>BENCHMARK — 2026-03-30</Label>
              <h2 style={{ fontSize: 22, fontWeight: 500, color: C.text, marginBottom: 12, letterSpacing: '-0.01em' }}>
                Measured. Not claimed.
              </h2>
              <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.8, marginBottom: 28 }}>
                14 repos · 15,000+ functions · 70 functions judged by Gemini 2.5 Flash — an independent
                model, not Claude, to avoid circularity. Three passes: token efficiency, ground-truth recall,
                semantic retention.
              </p>

              <Brackets>
                <div style={{ border: `1px solid ${C.border}`, overflow: 'hidden' }}>
                  {/* header */}
                  <div style={{
                    display: 'grid', gridTemplateColumns: '1fr 72px 84px',
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
                        display: 'grid', gridTemplateColumns: '1fr 72px 84px',
                        padding: '11px 16px',
                        borderBottom: i < BENCH.length - 1 ? `1px solid ${C.border}` : 'none',
                        transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = C.bg2)}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      <span style={{ ...mono, fontSize: 12, color: C.text, fontWeight: 300 }}>{row.repo}</span>
                      <span style={{ ...mono, fontSize: 12, color: C.muted, textAlign: 'right' as const, fontWeight: 300 }}>{row.saved}</span>
                      <span style={{ ...mono, fontSize: 12, color: C.text, textAlign: 'right' as const, fontWeight: 500 }}>{row.ret}</span>
                    </div>
                  ))}
                  <div style={{
                    padding: '10px 16px', borderTop: `1px solid ${C.border}`,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}>
                    <span style={{ ...mono, fontSize: 10, color: C.muted, fontWeight: 300 }}>14 repos total</span>
                    <a href="https://github.com/onedownz01/Thirdwheel-codeflow/blob/main/benchmark/FINAL_BENCHMARK_REPORT.md"
                      target="_blank" rel="noreferrer"
                      style={{ ...mono, fontSize: 10, color: C.muted, textDecoration: 'none', fontWeight: 300, transition: 'color 0.15s' }}
                      onMouseEnter={e => (e.currentTarget.style.color = C.text)}
                      onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
                    >full report →</a>
                  </div>
                </div>
              </Brackets>
            </section>

            <Divider />

            {/* ── Docs ── */}
            <section id="docs">
              <Label>DOCS</Label>
              <h2 style={{ fontSize: 22, fontWeight: 500, color: C.text, marginBottom: 12, letterSpacing: '-0.01em' }}>
                Running in 60 seconds.
              </h2>
              <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.8, marginBottom: 28 }}>
                Python 3.11+ and Node 18+. No database, no accounts, no config needed for Sim mode.
              </p>

              {/* Tabs */}
              <div style={{ display: 'flex', borderBottom: `1px solid ${C.border}`, marginBottom: 0, gap: 0 }}>
                {[['qs', 'QUICK START'], ['api', 'API REFERENCE']] .map(([key, lbl]) => (
                  <button key={key} onClick={() => setActiveTab(key as 'qs' | 'api')}
                    style={{
                      ...mono, background: 'none', border: 'none',
                      borderBottom: activeTab === key ? `1px solid ${C.text}` : '1px solid transparent',
                      cursor: 'pointer', fontSize: 10,
                      fontWeight: 500, letterSpacing: '0.06em',
                      color: activeTab === key ? C.text : C.muted,
                      padding: '8px 16px 10px',
                      marginBottom: -1,
                    }}
                  >{lbl}</button>
                ))}
              </div>

              {activeTab === 'qs'
                ? <CodeBlock code={INSTALL} filename="terminal" />
                : (
                  <Brackets style={{ marginTop: 0 }}>
                    <div style={{ border: `1px solid ${C.border}` }}>
                      {API_ROUTES.map((r, i) => (
                        <div key={r.path}
                          style={{
                            display: 'grid', gridTemplateColumns: '44px 1fr',
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
                            <div style={{ ...mono, fontSize: 12, color: C.text, marginBottom: 2, fontWeight: 300 }}>{r.path}</div>
                            <div style={{ fontSize: 11, color: C.muted, fontWeight: 300 }}>{r.desc}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Brackets>
                )
              }
            </section>

            {/* ── Footer ── */}
            <div style={{ borderTop: `1px solid ${C.border}`, marginTop: 80, paddingTop: 28, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <span style={{ ...mono, fontSize: 10, color: C.muted, fontWeight: 300, letterSpacing: '0.04em' }}>
                made by foundarv enggers for internal usecase now for all —{' '}
                <a href="https://foundarv.com" target="_blank" rel="noreferrer"
                  style={{ color: C.text, textDecoration: 'none' }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = '0.7')}
                  onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
                >foundarv.com</a>
              </span>
              <span style={{ ...mono, fontSize: 10, color: C.dim, fontWeight: 300 }}>codeflow · open source</span>
            </div>

          </div>{/* end right */}
        </div>{/* end split */}
      </div>
    </>
  );
}
