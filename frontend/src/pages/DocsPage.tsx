import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const GH = {
  bg:     '#0d1117',
  bg2:    '#161b22',
  bg3:    '#21262d',
  border: '#30363d',
  text:   '#e6edf3',
  muted:  '#8b949e',
  dim:    '#484f58',
  green:  '#3fb950',
  blue:   '#58a6ff',
  orange: '#d29922',
};

const sans: React.CSSProperties = { fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif" };
const mono: React.CSSProperties = { fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace" };

function Code({ children, lang }: { children: string; lang?: string }) {
  return (
    <div style={{ position: 'relative', marginBottom: 16 }}>
      {lang && (
        <div style={{
          ...mono, fontSize: 10, color: GH.muted,
          background: GH.bg3, border: `1px solid ${GH.border}`,
          borderBottom: 'none', padding: '4px 12px',
          borderRadius: '6px 6px 0 0', display: 'inline-block',
        }}>
          {lang}
        </div>
      )}
      <pre style={{
        ...mono, fontSize: 13, lineHeight: 1.7,
        background: GH.bg2, color: GH.text,
        border: `1px solid ${GH.border}`,
        borderRadius: lang ? '0 6px 6px 6px' : 6,
        padding: '16px',
        margin: 0, overflowX: 'auto',
      }}>
        <code>{children}</code>
      </pre>
    </div>
  );
}

function InlineCode({ children }: { children: string }) {
  return (
    <code style={{
      ...mono, fontSize: 12,
      background: GH.bg3, color: GH.text,
      border: `1px solid ${GH.border}`,
      padding: '1px 6px', borderRadius: 4,
    }}>
      {children}
    </code>
  );
}

function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} style={{
      fontSize: 20, fontWeight: 600, color: GH.text,
      paddingBottom: 8, marginBottom: 16, marginTop: 40,
      borderBottom: `1px solid ${GH.border}`,
    }}>
      {children}
    </h2>
  );
}

function H3({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h3 id={id} style={{
      fontSize: 16, fontWeight: 600, color: GH.text,
      marginBottom: 12, marginTop: 28,
    }}>
      {children}
    </h3>
  );
}

function P({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ fontSize: 14, color: GH.muted, lineHeight: 1.75, marginBottom: 16 }}>
      {children}
    </p>
  );
}

const NAV = [
  { id: 'overview',  label: 'Overview' },
  { id: 'quickstart', label: 'Quick start' },
  { id: 'schema',    label: 'ParsedRepo schema' },
  { id: 'api',       label: 'API reference' },
  { id: 'modes',     label: 'Trace modes' },
  { id: 'agents',    label: 'Using with agents' },
  { id: 'env',       label: 'Configuration' },
];

export default function DocsPage() {
  const navigate = useNavigate();
  const [active, setActive] = useState('overview');

  useEffect(() => {
    const onScroll = () => {
      for (const item of [...NAV].reverse()) {
        const el = document.getElementById(item.id);
        if (el && el.getBoundingClientRect().top <= 80) {
          setActive(item.id);
          return;
        }
      }
      setActive('overview');
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <div style={{ ...sans, background: GH.bg, color: GH.text, minHeight: '100vh' }}>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: ${GH.bg3}; border-radius: 3px; }
        body { background: ${GH.bg}; }
        a { color: ${GH.blue}; text-decoration: none; }
        a:hover { text-decoration: underline; }
      `}</style>

      {/* Nav */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: GH.bg2, borderBottom: `1px solid ${GH.border}`,
        padding: '0 24px', height: 48,
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <button
          onClick={() => navigate('/')}
          style={{ ...mono, background: 'none', border: 'none', color: GH.blue, cursor: 'pointer', fontSize: 13, padding: 0 }}
        >
          ← codeflow
        </button>
        <span style={{ color: GH.dim }}>/</span>
        <span style={{ fontSize: 14, fontWeight: 600, color: GH.text }}>docs</span>
      </div>

      <div style={{ display: 'flex', maxWidth: 1100, margin: '0 auto' }}>

        {/* Sidebar */}
        <aside style={{
          width: 220, flexShrink: 0,
          position: 'sticky', top: 48,
          height: 'calc(100vh - 48px)',
          overflowY: 'auto',
          padding: '24px 0',
          borderRight: `1px solid ${GH.border}`,
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: GH.muted, padding: '0 16px', marginBottom: 8, letterSpacing: '0.06em', textTransform: 'uppercase' as const }}>
            On this page
          </div>
          {NAV.map(item => (
            <button
              key={item.id}
              onClick={() => {
                document.getElementById(item.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                setActive(item.id);
              }}
              style={{
                display: 'block', width: '100%', textAlign: 'left' as const,
                background: active === item.id ? GH.bg3 : 'none',
                border: 'none',
                borderLeft: active === item.id ? `2px solid ${GH.blue}` : '2px solid transparent',
                padding: '6px 16px',
                fontSize: 13,
                color: active === item.id ? GH.text : GH.muted,
                cursor: 'pointer',
                transition: 'all 0.1s',
              }}
            >
              {item.label}
            </button>
          ))}
        </aside>

        {/* Main */}
        <main style={{ flex: 1, padding: '32px 40px 80px', minWidth: 0 }}>

          {/* Overview */}
          <H2 id="overview">Overview</H2>
          <P>
            Codeflow parses any public GitHub repo and builds a directed call graph anchored to user-facing
            entry points (routes, handlers, CLI commands). You can trace execution statically, attach to a live
            process, or ingest real OpenTelemetry spans — all in the same graph view.
          </P>
          <P>
            For LLM agents, Codeflow exposes a <InlineCode>ParsedRepo</InlineCode> JSON object with every function,
            its type, call edges, and pre-built indexes. No need to pass raw source files.
          </P>

          <div style={{
            background: GH.bg2, border: `1px solid ${GH.border}`,
            borderLeft: `3px solid ${GH.orange}`,
            borderRadius: '0 6px 6px 0',
            padding: '12px 16px', marginBottom: 24,
            fontSize: 13, color: GH.muted, lineHeight: 1.6,
          }}>
            <strong style={{ color: GH.orange }}>Note:</strong>{' '}
            Python and TypeScript/React repos are supported. Other languages will parse partially.
          </div>

          {/* Quick start */}
          <H2 id="quickstart">Quick start</H2>
          <P>Requirements: Python 3.11+, Node 18+.</P>

          <H3 id="qs-auto">One command</H3>
          <Code lang="bash">{`./scripts/dev_local.sh`}</Code>

          <H3 id="qs-manual">Manual setup</H3>
          <Code lang="bash">{`# 1. clone
git clone https://github.com/onedownz01/Thirdwheel-codeflow
cd Thirdwheel-codeflow

# 2. python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8001

# 3. frontend  (new terminal)
cd frontend
npm install
npm run dev`}</Code>

          <P>
            Open <InlineCode>http://localhost:5173</InlineCode>. The frontend proxies all API calls to
            port 8001. For sim mode no GitHub token is needed; for large repos or frequent parses
            set <InlineCode>GITHUB_TOKEN</InlineCode> to avoid rate limits.
          </P>

          {/* Schema */}
          <H2 id="schema">ParsedRepo schema</H2>
          <P>
            <InlineCode>GET /intents?repo=owner/repo</InlineCode> returns an <InlineCode>ApiEnvelope</InlineCode> where{' '}
            <InlineCode>data.parsed_repo</InlineCode> is a <InlineCode>ParsedRepo</InlineCode> object.
          </P>
          <Code lang="typescript">{`interface Function {
  id:          string;      // "fn:a1b2c3"
  name:        string;      // "create_item"
  type:        FnType;      // "route" | "handler" | "util" | "model" | "auth" | "test"
  file:        string;      // "app/main.py"
  line:        number;      // 42
  return_type: string;      // "Item"
  docstring:   string;      // extracted from source
  calls:       string[];    // ids of called functions
  params:      Param[];     // { name, type, default }
}

interface ParsedRepo {
  functions:     Function[];
  intents:       Intent[];        // user-facing entry points
  edges:         Edge[];          // all call edges
  fn_type_index: Record<FnType, string[]>;   // O(1) by type
  file_index:    Record<string, string[]>;   // O(1) by file
  schema_version: string;
}`}</Code>

          <H3 id="schema-intent">Intent object</H3>
          <Code lang="typescript">{`interface Intent {
  id:          string;      // "intent:b2c3d4"
  name:        string;      // "POST /items"
  fn_id:       string;      // root function id
  confidence:  number;      // 0.0 – 1.0
  method:      string;      // "GET" | "POST" | "CLI" | ...
  path:        string;      // "/items/{id}"
}`}</Code>

          <H3 id="schema-types">Function types</H3>
          <div style={{ border: `1px solid ${GH.border}`, borderRadius: 6, overflow: 'hidden', marginBottom: 16 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' as const, fontSize: 13 }}>
              <thead>
                <tr style={{ background: GH.bg2, borderBottom: `1px solid ${GH.border}` }}>
                  {['Type', 'What it means'].map(h => (
                    <th key={h} style={{ ...mono, fontSize: 11, padding: '8px 14px', textAlign: 'left' as const, color: GH.muted, fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ['route',   'HTTP route handler (FastAPI, Flask, Django view)'],
                  ['handler', 'event handler, message consumer, webhook receiver'],
                  ['auth',    'authentication / authorization function'],
                  ['model',   'data model method (ORM, Pydantic, dataclass)'],
                  ['util',    'shared utility, helper, or library function'],
                  ['test',    'test function or fixture'],
                ].map(([t, d], i) => (
                  <tr key={t} style={{ borderBottom: i < 5 ? `1px solid ${GH.border}` : 'none' }}>
                    <td style={{ ...mono, padding: '8px 14px', fontSize: 12, color: GH.green }}>{t}</td>
                    <td style={{ padding: '8px 14px', fontSize: 13, color: GH.muted }}>{d}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* API */}
          <H2 id="api">API reference</H2>
          <P>All endpoints served on port 8001. CORS is open in dev mode.</P>

          {[
            {
              method: 'GET', path: '/intents?repo={owner/repo}',
              desc: 'Parse a repo and return the full ParsedRepo + intents. Results are cached — subsequent calls for the same repo are instant.',
              ret: 'ApiEnvelope<{ parsed_repo: ParsedRepo, intents: Intent[] }>',
            },
            {
              method: 'GET', path: '/occurrences?intent_id={id}',
              desc: 'Return the full call chain for one intent. Resolves the call graph recursively.',
              ret: 'ApiEnvelope<Occurrence[]>',
            },
            {
              method: 'POST', path: '/trace/start',
              desc: 'Create a trace session. Returns a session_id for subsequent ingestion.',
              ret: '{ session_id: string }',
            },
            {
              method: 'POST', path: '/trace/ingest',
              desc: 'Ingest OpenTelemetry spans into an active session. Body: OTel JSON span array.',
              ret: '{ ingested: number }',
            },
            {
              method: 'GET', path: '/trace/{session_id}',
              desc: 'Fetch all events for a session.',
              ret: 'TraceEvent[]',
            },
            {
              method: 'WS', path: '/ws/trace/{session_id}',
              desc: 'WebSocket stream for live events. Emits TraceEvent JSON as they arrive.',
              ret: 'stream: TraceEvent',
            },
            {
              method: 'GET', path: '/health',
              desc: 'Health check.',
              ret: '{ status: "ok" }',
            },
          ].map(r => (
            <div key={r.path} style={{
              border: `1px solid ${GH.border}`, borderRadius: 6,
              overflow: 'hidden', marginBottom: 12,
            }}>
              <div style={{
                background: GH.bg2, padding: '10px 16px',
                borderBottom: `1px solid ${GH.border}`,
                display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <span style={{
                  ...mono, fontSize: 11, fontWeight: 600,
                  color: r.method === 'GET' ? GH.green : r.method === 'POST' ? GH.blue : GH.orange,
                  background: r.method === 'GET' ? `${GH.green}15` : r.method === 'POST' ? `${GH.blue}15` : `${GH.orange}15`,
                  padding: '2px 8px', borderRadius: 4,
                }}>
                  {r.method}
                </span>
                <code style={{ ...mono, fontSize: 13, color: GH.text }}>{r.path}</code>
              </div>
              <div style={{ padding: '12px 16px', background: GH.bg }}>
                <p style={{ fontSize: 13, color: GH.muted, marginBottom: 8, lineHeight: 1.6 }}>{r.desc}</p>
                <div style={{ ...mono, fontSize: 11, color: GH.dim }}>
                  returns: <span style={{ color: GH.muted }}>{r.ret}</span>
                </div>
              </div>
            </div>
          ))}

          {/* Trace modes */}
          <H2 id="modes">Trace modes</H2>

          <H3 id="modes-sim">Sim (static)</H3>
          <P>
            Default mode. Codeflow walks the static call graph from an intent and generates a synthetic
            execution trace. No service needs to be running. Works on any parsed repo immediately.
          </P>
          <P>
            Limitation: can't resolve dynamic dispatch, runtime-generated routes, or calls behind conditionals
            that depend on runtime state.
          </P>

          <H3 id="modes-otel">OTel (live spans)</H3>
          <P>
            Point your service's OTel exporter at <InlineCode>http://localhost:8001/trace/ingest</InlineCode>.
            Start a session first via <InlineCode>POST /trace/start</InlineCode>, then run your service and
            trigger some requests. Spans stream in real time via the WebSocket.
          </P>
          <Code lang="python">{`# Example: instrument FastAPI with OTel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
exporter = OTLPSpanExporter(endpoint="http://localhost:8001/trace/ingest")
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)`}</Code>

          <H3 id="modes-live">Live (sys.settrace)</H3>
          <P>
            Attaches to a running local Python process via <InlineCode>sys.settrace</InlineCode>.
            Every function call and return is captured with actual argument values.
            No code changes or instrumentation needed.
          </P>
          <P>
            Best for: debugging a specific code path, capturing I/O that OTel doesn't surface,
            or profiling without adding dependencies.
          </P>

          {/* Agents */}
          <H2 id="agents">Using with agents</H2>
          <P>
            The recommended pattern for LLM agents is to call <InlineCode>GET /intents</InlineCode> once
            at the start of a session and pass the entire <InlineCode>ParsedRepo</InlineCode> as context.
            36% fewer tokens than raw source, 100% function recall.
          </P>

          <H3 id="agents-lookup">Efficient lookups</H3>
          <Code lang="python">{`import httpx, json

repo = httpx.get("http://localhost:8001/intents?repo=tiangolo/fastapi").json()
parsed = repo["data"]["parsed_repo"]

# All route functions — O(1)
routes = [
    parsed["fn_type_index"]["route"]  # list of fn ids
]

# All functions in a specific file — O(1)
main_fns = parsed["file_index"].get("app/main.py", [])

# Look up a function by id
fn_map = {f["id"]: f for f in parsed["functions"]}
fn = fn_map["fn:a1b2c3"]`}</Code>

          <H3 id="agents-intents">Intents as task anchors</H3>
          <P>
            Each <InlineCode>Intent</InlineCode> represents something a user can do. Pass the intent list
            to your agent so it can map user tasks to code paths without reading every file.
          </P>
          <Code lang="python">{`intents = repo["data"]["intents"]
# [{ "name": "POST /items", "fn_id": "fn:a1b2c3", "confidence": 0.94, ... }]

# Give your agent a lookup: "what code handles POST /items?"
intent_map = {i["name"]: i["fn_id"] for i in intents}`}</Code>

          {/* Config */}
          <H2 id="env">Configuration</H2>
          <div style={{ border: `1px solid ${GH.border}`, borderRadius: 6, overflow: 'hidden', marginBottom: 16 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' as const, fontSize: 13 }}>
              <thead>
                <tr style={{ background: GH.bg2, borderBottom: `1px solid ${GH.border}` }}>
                  {['Variable', 'Default', 'Description'].map(h => (
                    <th key={h} style={{ ...mono, fontSize: 11, padding: '8px 14px', textAlign: 'left' as const, color: GH.muted, fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ['GITHUB_TOKEN', '—', 'GitHub personal access token. Required for >60 req/hr or private repos.'],
                  ['PORT', '8001', 'Backend port.'],
                  ['VITE_DEV_API_TARGET', 'http://127.0.0.1:8001', 'Frontend proxy target for local dev.'],
                ].map(([k, def, desc], i) => (
                  <tr key={k} style={{ borderBottom: i < 2 ? `1px solid ${GH.border}` : 'none' }}>
                    <td style={{ ...mono, padding: '8px 14px', fontSize: 12, color: GH.green }}>{k}</td>
                    <td style={{ ...mono, padding: '8px 14px', fontSize: 12, color: GH.dim }}>{def}</td>
                    <td style={{ padding: '8px 14px', fontSize: 13, color: GH.muted }}>{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <P>
            Put these in a <InlineCode>.env</InlineCode> file at the repo root. The backend loads it on startup.
          </P>

        </main>
      </div>
    </div>
  );
}
