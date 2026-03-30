import { useNavigate } from 'react-router-dom';

/* ─────────────────────────────────────────────
   Codeflow landing — inspired by betterauth.com
   Dark-first, clean grid, numbered features,
   real code front-and-centre.
───────────────────────────────────────────── */

const MINT = '#4ade80';
const BG = '#09090b';
const BG2 = '#0f0f12';
const BORDER = 'rgba(255,255,255,0.07)';
const TEXT = '#f4f4f5';
const MUTED = '#71717a';
const DIM = '#3f3f46';

const base: React.CSSProperties = {
  fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
  background: BG,
  color: TEXT,
  minHeight: '100vh',
};

const mono: React.CSSProperties = {
  fontFamily: "'SF Mono', 'Fira Code', monospace",
};

const FEATURES = [
  {
    n: '01',
    title: 'Parse any GitHub repo',
    body: 'Paste a URL. Codeflow fetches, parses with Tree-sitter, and returns a structured graph in seconds. Python and TypeScript/React supported out of the box.',
  },
  {
    n: '02',
    title: 'Intent extraction',
    body: 'Every user-facing action — API routes, form handlers, CLI commands, class entry points — is surfaced as a named Intent with a confidence score.',
  },
  {
    n: '03',
    title: 'Animated call-chain tracer',
    body: 'Click an intent and watch the full execution path animate across the canvas. File, line number, and I/O on every block.',
  },
  {
    n: '04',
    title: 'Three trace modes',
    body: 'Sim walks the static call graph. OTel ingests real spans from your running service. Live attaches sys.settrace to a local process — zero code changes.',
  },
  {
    n: '05',
    title: 'Structured context for agents',
    body: 'ParsedRepo JSON gives LLM agents 36% fewer tokens on average, 100% function recall, and pre-built fn_type_index / file_index for O(1) lookups.',
  },
  {
    n: '06',
    title: 'Benchmarked, not claimed',
    body: '14 repos, 15k+ functions. Gemini 2.5 Flash judges semantic retention: 69% avg vs raw source. psf/requests hits 90%. Full report in the repo.',
  },
];

const STATS = [
  { n: '36%',    label: 'avg token savings' },
  { n: '100%',   label: 'function recall' },
  { n: '69%',    label: 'semantic retention' },
  { n: '14',     label: 'repos benchmarked' },
];

const CODE_SNIPPET = `# One endpoint — full repo graph
GET /intents?repo=tiangolo/fastapi

# Returns ParsedRepo JSON:
{
  "functions": [           # every fn with type, params,
    {                      # return_type, docstring, calls
      "id": "fn:abc123",
      "name": "create_item",
      "type": "route",
      "file": "app/main.py",
      "line": 42,
      "return_type": "Item",
      "docstring": "Create a new item.",
      "calls": ["fn:def456", "fn:ghi789"]
    }
    ...
  ],
  "intents": [...],        # user-facing actions
  "fn_type_index": {       # O(1) by type
    "route":   ["fn:abc123", ...],
    "handler": [...],
    "auth":    [...]
  },
  "file_index": {          # O(1) by file
    "app/main.py": ["fn:abc123", ...]
  }
}`;

export default function LandingPage() {
  const navigate = useNavigate();

  const scrollTo = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });

  return (
    <div style={base}>

      {/* ── Nav ── */}
      <header style={{
        borderBottom: `1px solid ${BORDER}`,
        position: 'sticky',
        top: 0,
        background: 'rgba(9,9,11,0.85)',
        backdropFilter: 'blur(16px)',
        zIndex: 50,
      }}>
        <div style={{
          maxWidth: 1100,
          margin: '0 auto',
          padding: '0 32px',
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 24,
        }}>
          <span style={{ ...mono, fontSize: 14, fontWeight: 700, color: MINT, letterSpacing: '0.1em' }}>
            CODEFLOW
          </span>
          <nav style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
            {['Features', 'Benchmark', 'Docs'].map(label => (
              <button
                key={label}
                onClick={() => scrollTo(label.toLowerCase())}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontSize: 13, color: MUTED, padding: 0,
                  fontFamily: 'inherit',
                  transition: 'color 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.color = TEXT)}
                onMouseLeave={e => (e.currentTarget.style.color = MUTED)}
              >
                {label}
              </button>
            ))}
          </nav>
          <button
            onClick={() => navigate('/app')}
            style={{
              background: MINT, color: BG,
              border: 'none', cursor: 'pointer',
              padding: '8px 20px',
              fontSize: 13, fontWeight: 700,
              fontFamily: 'inherit',
              letterSpacing: '0.04em',
              borderRadius: 6,
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            Launch App →
          </button>
        </div>
      </header>

      {/* ── Hero ── */}
      <section style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '96px 32px 80px',
        textAlign: 'center',
      }}>
        <div style={{
          display: 'inline-block',
          ...mono,
          fontSize: 11,
          letterSpacing: '0.16em',
          color: MINT,
          background: 'rgba(74,222,128,0.08)',
          border: `1px solid rgba(74,222,128,0.2)`,
          padding: '4px 14px',
          borderRadius: 99,
          marginBottom: 32,
        }}>
          intent-anchored execution tracer
        </div>

        <h1 style={{
          fontSize: 'clamp(36px, 6vw, 68px)',
          fontWeight: 800,
          lineHeight: 1.08,
          letterSpacing: '-0.03em',
          marginBottom: 24,
          color: TEXT,
        }}>
          The most comprehensive<br />
          <span style={{ color: MINT }}>code understanding tool</span><br />
          for humans and agents.
        </h1>

        <p style={{
          fontSize: 17,
          color: MUTED,
          maxWidth: 540,
          margin: '0 auto 48px',
          lineHeight: 1.7,
        }}>
          Paste any GitHub URL. Get every user-facing action, a full call-chain
          tracer, and a structured JSON graph your LLM agents can actually use.
        </p>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => navigate('/app')}
            style={{
              background: MINT, color: BG,
              border: 'none', cursor: 'pointer',
              padding: '12px 28px',
              fontSize: 14, fontWeight: 700,
              fontFamily: 'inherit',
              borderRadius: 8,
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            Launch the tracer
          </button>
          <button
            onClick={() => scrollTo('benchmark')}
            style={{
              background: 'transparent', color: TEXT,
              border: `1px solid ${BORDER}`, cursor: 'pointer',
              padding: '12px 28px',
              fontSize: 14, fontWeight: 500,
              fontFamily: 'inherit',
              borderRadius: 8,
              transition: 'border-color 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = DIM)}
            onMouseLeave={e => (e.currentTarget.style.borderColor = BORDER)}
          >
            View benchmark
          </button>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <div style={{
        borderTop: `1px solid ${BORDER}`,
        borderBottom: `1px solid ${BORDER}`,
        background: BG2,
      }}>
        <div style={{
          maxWidth: 1100,
          margin: '0 auto',
          padding: '0 32px',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
        }}>
          {STATS.map((s, i) => (
            <div
              key={s.n}
              style={{
                padding: '32px 24px',
                textAlign: 'center',
                borderRight: i < STATS.length - 1 ? `1px solid ${BORDER}` : 'none',
              }}
            >
              <div style={{ ...mono, fontSize: 36, fontWeight: 800, color: MINT, letterSpacing: '-0.02em' }}>
                {s.n}
              </div>
              <div style={{ fontSize: 12, color: MUTED, marginTop: 4, letterSpacing: '0.04em' }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Features ── */}
      <section id="features" style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '96px 32px',
      }}>
        <div style={{ marginBottom: 56, textAlign: 'center' }}>
          <p style={{ ...mono, fontSize: 11, letterSpacing: '0.16em', color: MINT, marginBottom: 12 }}>
            WHAT IT DOES
          </p>
          <h2 style={{ fontSize: 36, fontWeight: 700, letterSpacing: '-0.02em' }}>
            Everything you need to understand a codebase.
          </h2>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 1,
          background: BORDER,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          overflow: 'hidden',
        }}>
          {FEATURES.map((f) => (
            <div
              key={f.n}
              style={{
                background: BG,
                padding: '32px 28px',
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = BG2)}
              onMouseLeave={e => (e.currentTarget.style.background = BG)}
            >
              <div style={{ ...mono, fontSize: 11, color: DIM, marginBottom: 16, letterSpacing: '0.1em' }}>
                {f.n}
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: TEXT, marginBottom: 10 }}>
                {f.title}
              </div>
              <div style={{ fontSize: 13, color: MUTED, lineHeight: 1.7 }}>
                {f.body}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── For Agents — code block ── */}
      <section id="for-agents" style={{
        borderTop: `1px solid ${BORDER}`,
        background: BG2,
      }}>
        <div style={{
          maxWidth: 1100,
          margin: '0 auto',
          padding: '96px 32px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 64,
          alignItems: 'center',
        }}>
          <div>
            <p style={{ ...mono, fontSize: 11, letterSpacing: '0.16em', color: MINT, marginBottom: 12 }}>
              FOR AGENTS
            </p>
            <h2 style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 16, lineHeight: 1.2 }}>
              One API call.<br />Full repo graph.
            </h2>
            <p style={{ fontSize: 14, color: MUTED, lineHeight: 1.8, marginBottom: 32 }}>
              Every function with type classification, typed params, return type,
              docstring, and outbound calls. Pre-built indexes so agents skip
              the full function scan — <code style={{ ...mono, color: MINT, fontSize: 13 }}>fn_type_index</code> and{' '}
              <code style={{ ...mono, color: MINT, fontSize: 13 }}>file_index</code> give O(1) access.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                '100% function recall across 14 repos',
                '36% avg token savings vs raw source',
                '69% semantic retention (Gemini 2.5 Flash judge)',
              ].map(item => (
                <div key={item} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 13, color: MUTED }}>
                  <span style={{ color: MINT, marginTop: 1, flexShrink: 0 }}>✓</span>
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div style={{
            background: BG,
            border: `1px solid ${BORDER}`,
            borderRadius: 10,
            overflow: 'hidden',
          }}>
            <div style={{
              padding: '10px 16px',
              borderBottom: `1px solid ${BORDER}`,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              {['#ef4444','#f59e0b','#22c55e'].map(c => (
                <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />
              ))}
              <span style={{ ...mono, fontSize: 11, color: DIM, marginLeft: 8 }}>parsed_repo.json</span>
            </div>
            <pre style={{
              ...mono,
              fontSize: 12,
              lineHeight: 1.7,
              padding: '20px 20px',
              margin: 0,
              color: '#a1a1aa',
              overflowX: 'auto',
              whiteSpace: 'pre',
            }}>
              {CODE_SNIPPET.split('\n').map((line, i) => {
                const isComment = line.trimStart().startsWith('#');
                const isKey = /^\s+"[a-z_]+":\s/.test(line);
                const isMint = /GET|"type"|"route"|"handler"|"auth"/.test(line);
                return (
                  <span key={i} style={{
                    color: isComment ? '#3f3f46' : isMint ? MINT : isKey ? '#e4e4e7' : '#71717a',
                    display: 'block',
                  }}>
                    {line}
                  </span>
                );
              })}
            </pre>
          </div>
        </div>
      </section>

      {/* ── Trace Modes ── */}
      <section style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '96px 32px',
      }}>
        <div style={{ marginBottom: 56, textAlign: 'center' }}>
          <p style={{ ...mono, fontSize: 11, letterSpacing: '0.16em', color: MINT, marginBottom: 12 }}>
            TRACE MODES
          </p>
          <h2 style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em' }}>
            Three ways to trace. Start in 30 seconds.
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            {
              mode: 'Sim',
              tagline: 'No setup needed',
              desc: 'Walks the static call graph and generates a synthetic execution trace. Works on any public repo instantly — no running service required.',
              req: 'Any public GitHub URL',
              highlight: true,
            },
            {
              mode: 'OTel',
              tagline: 'Real spans',
              desc: 'Receives live OpenTelemetry spans from your running service. Real timing, real values, real errors. Point your collector at the ingest endpoint.',
              req: 'OTel SDK + running service',
              highlight: false,
            },
            {
              mode: 'Live',
              tagline: 'Zero instrumentation',
              desc: "Attaches Python's sys.settrace directly to a local process. Captures every call, argument, and return value without touching a single line of your code.",
              req: 'Local repo + run command',
              highlight: false,
            },
          ].map(m => (
            <div
              key={m.mode}
              style={{
                background: m.highlight ? 'rgba(74,222,128,0.05)' : BG2,
                border: `1px solid ${m.highlight ? 'rgba(74,222,128,0.2)' : BORDER}`,
                borderRadius: 10,
                padding: '28px 24px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                <span style={{ ...mono, fontSize: 16, fontWeight: 800, color: m.highlight ? MINT : TEXT }}>
                  {m.mode}
                </span>
                <span style={{
                  ...mono,
                  fontSize: 10,
                  letterSpacing: '0.1em',
                  color: m.highlight ? MINT : MUTED,
                  background: m.highlight ? 'rgba(74,222,128,0.1)' : 'rgba(255,255,255,0.04)',
                  padding: '2px 8px',
                  borderRadius: 99,
                }}>
                  {m.tagline}
                </span>
              </div>
              <p style={{ fontSize: 13, color: MUTED, lineHeight: 1.7, marginBottom: 20 }}>
                {m.desc}
              </p>
              <div style={{
                ...mono,
                fontSize: 11,
                color: DIM,
                borderTop: `1px solid ${BORDER}`,
                paddingTop: 14,
              }}>
                Requires: {m.req}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Benchmark ── */}
      <section id="benchmark" style={{
        borderTop: `1px solid ${BORDER}`,
        background: BG2,
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '96px 32px' }}>
          <div style={{ marginBottom: 48 }}>
            <p style={{ ...mono, fontSize: 11, letterSpacing: '0.16em', color: MINT, marginBottom: 12 }}>
              BENCHMARK — 2026-03-30
            </p>
            <h2 style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 12 }}>
              Measured. Not claimed.
            </h2>
            <p style={{ fontSize: 14, color: MUTED, maxWidth: 520 }}>
              14 repos, 15,000+ functions, 70 functions judged by Gemini 2.5 Flash (independent judge — not Claude).
              Three passes: token efficiency, ground-truth recall, semantic retention.
            </p>
          </div>

          <div style={{
            border: `1px solid ${BORDER}`,
            borderRadius: 10,
            overflow: 'hidden',
          }}>
            {/* header */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '2fr 100px 100px 100px',
              padding: '10px 20px',
              background: 'rgba(255,255,255,0.02)',
              borderBottom: `1px solid ${BORDER}`,
              ...mono,
              fontSize: 10,
              letterSpacing: '0.1em',
              color: DIM,
            }}>
              <span>REPO</span><span style={{textAlign:'right'}}>SAVED</span>
              <span style={{textAlign:'right'}}>RETENTION</span>
              <span style={{textAlign:'right'}}>GRADE</span>
            </div>

            {[
              { repo: 'psf/requests',                         saved: '31.4%', ret: '90%', grade: 'A' },
              { repo: 'Textualize/rich',                      saved: '78.3%', ret: '83%', grade: 'A' },
              { repo: 'pallets/flask',                        saved: '15.9%', ret: '80%', grade: 'A' },
              { repo: 'fastapi/full-stack-fastapi-template',  saved: '58.3%', ret: '77%', grade: 'B+' },
              { repo: 'anthropics/anthropic-sdk-python',      saved: '24.0%', ret: '74%', grade: 'B+' },
              { repo: 'encode/httpx',                         saved: '39.8%', ret: '72%', grade: 'B+' },
              { repo: 'sqlalchemy/sqlalchemy',                saved: '42.6%', ret: '64%', grade: 'B' },
              { repo: 'openai/openai-python',                 saved:  '1.1%', ret: '62%', grade: 'B' },
            ].map((row, i) => (
              <div
                key={row.repo}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '2fr 100px 100px 100px',
                  padding: '14px 20px',
                  borderBottom: i < 7 ? `1px solid ${BORDER}` : 'none',
                  alignItems: 'center',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span style={{ ...mono, fontSize: 13, color: TEXT }}>{row.repo}</span>
                <span style={{ ...mono, fontSize: 13, color: MINT, textAlign: 'right' }}>{row.saved}</span>
                <span style={{ ...mono, fontSize: 13, color: MUTED, textAlign: 'right' }}>{row.ret}</span>
                <span style={{
                  ...mono, fontSize: 11, fontWeight: 700, textAlign: 'right',
                  color: row.grade === 'A' ? MINT : row.grade.startsWith('B+') ? '#a3e635' : MUTED,
                }}>{row.grade}</span>
              </div>
            ))}

            <div style={{
              padding: '14px 20px',
              borderTop: `1px solid ${BORDER}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span style={{ fontSize: 12, color: MUTED }}>14 repos total · full report in repo</span>
              <a
                href="https://github.com/onedownz01/Thirdwheel-codeflow/blob/main/benchmark/FINAL_BENCHMARK_REPORT.md"
                target="_blank"
                rel="noreferrer"
                style={{ ...mono, fontSize: 11, color: MINT, textDecoration: 'none' }}
              >
                View full report →
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Docs / Quick start ── */}
      <section id="docs" style={{ maxWidth: 1100, margin: '0 auto', padding: '96px 32px' }}>
        <div style={{ marginBottom: 48 }}>
          <p style={{ ...mono, fontSize: 11, letterSpacing: '0.16em', color: MINT, marginBottom: 12 }}>
            QUICK START
          </p>
          <h2 style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em' }}>
            Running in 60 seconds.
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          {/* setup */}
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: `1px solid ${BORDER}`, background: BG2, display: 'flex', gap: 6, alignItems: 'center' }}>
              {['#ef4444','#f59e0b','#22c55e'].map(c => <div key={c} style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />)}
              <span style={{ ...mono, fontSize: 11, color: DIM, marginLeft: 8 }}>terminal</span>
            </div>
            <pre style={{ ...mono, fontSize: 12, lineHeight: 1.9, padding: '20px', margin: 0, color: MUTED, overflowX: 'auto' }}>
              <span style={{ color: DIM }}># Python 3.11+ · Node 18+{'\n'}</span>
              <span style={{ color: MINT }}>./scripts/dev_local.sh{'\n'}</span>
              <span style={{ color: DIM }}>{'\n'}# or manual{'\n'}</span>
              <span>python3 -m venv .venv{'\n'}</span>
              <span>source .venv/bin/activate{'\n'}</span>
              <span>pip install -r backend/requirements.txt{'\n'}</span>
              <span style={{ color: MINT }}>uvicorn backend.main:app --reload --port 8001{'\n'}</span>
              <span style={{ color: DIM }}>{'\n'}# frontend (new terminal){'\n'}</span>
              <span>cd frontend && npm install{'\n'}</span>
              <span style={{ color: MINT }}>npm run dev</span>
            </pre>
          </div>

          {/* api ref */}
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: `1px solid ${BORDER}`, background: BG2 }}>
              <span style={{ ...mono, fontSize: 11, color: DIM }}>API reference</span>
            </div>
            <div style={{ padding: '8px 0' }}>
              {[
                { method: 'GET',  path: '/intents?repo={owner/repo}',      desc: 'ParsedRepo + all intents' },
                { method: 'GET',  path: '/occurrences?repo=…&intent_id=…', desc: 'Call chain for intent' },
                { method: 'POST', path: '/trace/start',                     desc: 'Start trace session' },
                { method: 'POST', path: '/trace/ingest',                    desc: 'Ingest OTel spans' },
                { method: 'GET',  path: '/trace/{session_id}',              desc: 'Fetch trace events' },
                { method: 'WS',   path: '/ws/trace/{session_id}',           desc: 'Live event stream' },
                { method: 'POST', path: '/fix',                             desc: 'AI fix suggestion (opt-in)' },
              ].map(r => (
                <div key={r.path} style={{
                  display: 'grid',
                  gridTemplateColumns: '44px 1fr',
                  gap: 12,
                  padding: '8px 16px',
                  alignItems: 'start',
                  borderBottom: `1px solid rgba(255,255,255,0.03)`,
                }}>
                  <span style={{
                    ...mono, fontSize: 10, fontWeight: 700,
                    color: r.method === 'GET' ? MINT : r.method === 'WS' ? '#a78bfa' : '#fb923c',
                    paddingTop: 1,
                  }}>
                    {r.method}
                  </span>
                  <div>
                    <div style={{ ...mono, fontSize: 11, color: TEXT }}>{r.path}</div>
                    <div style={{ fontSize: 11, color: MUTED, marginTop: 1 }}>{r.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer style={{
        borderTop: `1px solid ${BORDER}`,
        padding: '28px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        maxWidth: 1100,
        margin: '0 auto',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <span style={{ fontSize: 12, color: DIM }}>
          made by foundarv enggers for internal usecase now for all —{' '}
          <a href="https://foundarv.com" target="_blank" rel="noreferrer"
            style={{ color: MINT, textDecoration: 'none' }}>foundarv.com</a>
        </span>
        <span style={{ ...mono, fontSize: 11, color: DIM }}>codeflow · open source</span>
      </footer>
      <div style={{ borderTop: `1px solid ${BORDER}` }} />

    </div>
  );
}
