import { useNavigate } from 'react-router-dom';

const GH = {
  bg:       '#0d1117',
  bg2:      '#161b22',
  bg3:      '#21262d',
  border:   '#30363d',
  text:     '#e6edf3',
  muted:    '#8b949e',
  dim:      '#484f58',
  green:    '#3fb950',
  blue:     '#58a6ff',
  accent:   '#238636',
};

const sans: React.CSSProperties = { fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif" };
const mono: React.CSSProperties = { fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace" };

const BENCH = [
  { repo: 'psf/requests',                        raw: 41_200,  cf: 28_400,  saved: 31, ret: 90, fns: 312 },
  { repo: 'Textualize/rich',                     raw: 178_000, cf: 39_200,  saved: 78, ret: 83, fns: 1840 },
  { repo: 'pallets/flask',                        raw: 34_800,  cf: 29_200,  saved: 16, ret: 80, fns: 298 },
  { repo: 'fastapi/full-stack-fastapi-template',  raw: 54_600,  cf: 22_900,  saved: 58, ret: 77, fns: 421 },
  { repo: 'encode/httpx',                         raw: 64_300,  cf: 38_600,  saved: 40, ret: 72, fns: 587 },
  { repo: 'sqlalchemy/sqlalchemy',                raw: 418_000, cf: 238_300, saved: 43, ret: 64, fns: 4210 },
  { repo: 'django/django',                        raw: 512_000, cf: 298_000, saved: 42, ret: 61, fns: 5120 },
  { repo: 'tornadoweb/tornado',                   raw: 89_000,  cf: 54_000,  saved: 39, ret: 68, fns: 812 },
  { repo: 'aio-libs/aiohttp',                     raw: 142_000, cf: 88_000,  saved: 38, ret: 65, fns: 1340 },
  { repo: 'pydantic/pydantic',                    raw: 98_000,  cf: 64_000,  saved: 35, ret: 70, fns: 930 },
  { repo: 'tiangolo/fastapi',                     raw: 72_000,  cf: 45_000,  saved: 38, ret: 73, fns: 680 },
  { repo: 'celery/celery',                        raw: 198_000, cf: 128_000, saved: 35, ret: 62, fns: 1920 },
  { repo: 'pytest-dev/pytest',                    raw: 87_000,  cf: 55_000,  saved: 37, ret: 71, fns: 840 },
  { repo: 'python-poetry/poetry',                 raw: 76_000,  cf: 48_000,  saved: 37, ret: 69, fns: 720 },
];

function fmt(n: number) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'k';
  return String(n);
}

// SVG bar chart — horizontal
function BarChart({ data, accessor, color, max = 100, unit = '%' }: {
  data: typeof BENCH;
  accessor: (r: typeof BENCH[0]) => number;
  color: string;
  max?: number;
  unit?: string;
}) {
  const rowH = 28;
  const labelW = 240;
  const barAreaW = 260;
  const valW = 44;
  const totalW = labelW + barAreaW + valW;
  const totalH = data.length * rowH + 20;

  return (
    <svg width="100%" viewBox={`0 0 ${totalW} ${totalH}`} style={{ display: 'block', overflow: 'visible' }}>
      {data.map((row, i) => {
        const val = accessor(row);
        const barW = (val / max) * barAreaW;
        const y = i * rowH + 10;
        const repoName = row.repo.split('/')[1];
        return (
          <g key={row.repo}>
            <text
              x={labelW - 8} y={y + 10}
              textAnchor="end"
              style={{ ...mono, fontSize: 11, fill: GH.muted }}
            >
              {repoName.length > 18 ? repoName.slice(0, 17) + '…' : repoName}
            </text>
            <rect
              x={labelW} y={y + 2}
              width={Math.max(barW, 2)} height={16}
              fill={color} rx={1}
              opacity={0.85}
            />
            <text
              x={labelW + barAreaW + 6} y={y + 12}
              style={{ ...mono, fontSize: 11, fill: GH.text }}
            >
              {val}{unit}
            </text>
          </g>
        );
      })}
      {/* axis line */}
      <line x1={labelW} y1={8} x2={labelW} y2={totalH - 4} stroke={GH.border} strokeWidth={1} />
    </svg>
  );
}

export default function BenchmarkPage() {
  const navigate = useNavigate();
  const totalRaw = BENCH.reduce((s, r) => s + r.raw, 0);
  const totalCf  = BENCH.reduce((s, r) => s + r.cf, 0);
  const avgSaved = Math.round((1 - totalCf / totalRaw) * 100);
  const avgRet   = Math.round(BENCH.reduce((s, r) => s + r.ret, 0) / BENCH.length);

  return (
    <div style={{ ...sans, background: GH.bg, color: GH.text, minHeight: '100vh' }}>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: ${GH.bg3}; border-radius: 3px; }
        body { background: ${GH.bg}; }
      `}</style>

      {/* Nav */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: GH.bg2,
        borderBottom: `1px solid ${GH.border}`,
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
        <span style={{ fontSize: 14, fontWeight: 600, color: GH.text }}>benchmark</span>
        <div style={{ flex: 1 }} />
        <a
          href="https://github.com/onedownz01/Thirdwheel-codeflow/blob/main/benchmark/FINAL_BENCHMARK_REPORT.md"
          target="_blank" rel="noreferrer"
          style={{ ...mono, fontSize: 12, color: GH.muted, textDecoration: 'none' }}
        >
          raw report ↗
        </a>
      </div>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 24px 80px' }}>

        {/* Header */}
        <div style={{ marginBottom: 32, paddingBottom: 24, borderBottom: `1px solid ${GH.border}` }}>
          <h1 style={{ fontSize: 28, fontWeight: 600, color: GH.text, marginBottom: 8 }}>
            Benchmark Report
          </h1>
          <p style={{ fontSize: 14, color: GH.muted, lineHeight: 1.6 }}>
            Codeflow vs raw source on 14 Python repos. Three metrics: token count, function recall, semantic retention.
            Retention judged by Gemini 2.5 Flash on 5 sampled functions per repo.
          </p>
          <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' as const }}>
            {[
              { label: '14 repos' },
              { label: '15,000+ functions' },
              { label: '100% recall' },
              { label: 'Gemini 2.5 Flash judge' },
            ].map(b => (
              <span key={b.label} style={{
                ...mono, fontSize: 11, padding: '2px 10px',
                border: `1px solid ${GH.border}`, color: GH.muted,
                borderRadius: 20,
              }}>
                {b.label}
              </span>
            ))}
          </div>
        </div>

        {/* Key stats */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 1, background: GH.border,
          border: `1px solid ${GH.border}`, borderRadius: 6,
          overflow: 'hidden', marginBottom: 40,
        }}>
          {[
            { n: `${avgSaved}%`,           l: 'avg token savings',    sub: `${fmt(totalRaw)} → ${fmt(totalCf)} tokens` },
            { n: '100%',                   l: 'function recall',      sub: 'zero functions missed' },
            { n: `${avgRet}%`,             l: 'avg semantic retention', sub: 'scored by Gemini 2.5 Flash' },
            { n: `${fmt(BENCH.reduce((s,r)=>s+r.fns,0))}`,
                                           l: 'total functions',      sub: 'across 14 repos' },
          ].map(s => (
            <div key={s.n} style={{ background: GH.bg2, padding: '20px 16px' }}>
              <div style={{ ...mono, fontSize: 24, fontWeight: 600, color: GH.text }}>{s.n}</div>
              <div style={{ fontSize: 12, color: GH.muted, marginTop: 4 }}>{s.l}</div>
              <div style={{ ...mono, fontSize: 10, color: GH.dim, marginTop: 3 }}>{s.sub}</div>
            </div>
          ))}
        </div>

        {/* Charts */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 40 }}>
          <div style={{ background: GH.bg2, border: `1px solid ${GH.border}`, borderRadius: 6, padding: '20px' }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: GH.text, marginBottom: 16 }}>
              Token savings by repo
            </h3>
            <BarChart data={BENCH} accessor={r => r.saved} color={GH.green} />
          </div>
          <div style={{ background: GH.bg2, border: `1px solid ${GH.border}`, borderRadius: 6, padding: '20px' }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: GH.text, marginBottom: 16 }}>
              Semantic retention by repo
            </h3>
            <BarChart data={BENCH} accessor={r => r.ret} color={GH.blue} />
          </div>
        </div>

        {/* Full table */}
        <h2 style={{ fontSize: 16, fontWeight: 600, color: GH.text, marginBottom: 12 }}>All repos</h2>
        <div style={{ border: `1px solid ${GH.border}`, borderRadius: 6, overflow: 'hidden', marginBottom: 40 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' as const, fontSize: 13 }}>
            <thead>
              <tr style={{ background: GH.bg2, borderBottom: `1px solid ${GH.border}` }}>
                {['Repo', 'Functions', 'Raw tokens', 'CF tokens', 'Saved', 'Retention'].map(h => (
                  <th key={h} style={{
                    ...mono, fontSize: 11, padding: '8px 12px',
                    textAlign: 'left' as const, color: GH.muted,
                    fontWeight: 500, letterSpacing: '0.03em',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {BENCH.map((row, i) => (
                <tr key={row.repo} style={{
                  borderBottom: i < BENCH.length - 1 ? `1px solid ${GH.border}` : 'none',
                  background: i % 2 === 0 ? GH.bg : GH.bg2,
                }}>
                  <td style={{ ...mono, padding: '9px 12px', color: GH.blue, fontSize: 12 }}>
                    <a
                      href={`https://github.com/${row.repo}`}
                      target="_blank" rel="noreferrer"
                      style={{ color: GH.blue, textDecoration: 'none' }}
                      onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
                      onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
                    >
                      {row.repo}
                    </a>
                  </td>
                  <td style={{ ...mono, padding: '9px 12px', color: GH.muted, fontSize: 12 }}>{row.fns.toLocaleString()}</td>
                  <td style={{ ...mono, padding: '9px 12px', color: GH.muted, fontSize: 12 }}>{fmt(row.raw)}</td>
                  <td style={{ ...mono, padding: '9px 12px', color: GH.muted, fontSize: 12 }}>{fmt(row.cf)}</td>
                  <td style={{ padding: '9px 12px' }}>
                    <span style={{
                      ...mono, fontSize: 11, padding: '2px 8px',
                      background: `${GH.accent}22`, color: GH.green,
                      border: `1px solid ${GH.accent}44`, borderRadius: 20,
                    }}>
                      −{row.saved}%
                    </span>
                  </td>
                  <td style={{ padding: '9px 12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, height: 4, background: GH.bg3, borderRadius: 2, maxWidth: 80 }}>
                        <div style={{
                          width: `${row.ret}%`, height: '100%',
                          background: row.ret >= 80 ? GH.green : row.ret >= 65 ? GH.blue : GH.dim,
                          borderRadius: 2,
                        }} />
                      </div>
                      <span style={{ ...mono, fontSize: 12, color: GH.text, minWidth: 30 }}>{row.ret}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Methodology */}
        <h2 style={{ fontSize: 16, fontWeight: 600, color: GH.text, marginBottom: 12 }}>Methodology</h2>
        <div style={{ background: GH.bg2, border: `1px solid ${GH.border}`, borderRadius: 6, padding: '20px 24px', fontSize: 14, color: GH.muted, lineHeight: 1.75 }}>
          <p style={{ marginBottom: 12 }}>
            <strong style={{ color: GH.text }}>Token counting.</strong> Raw source: all .py files concatenated with file headers.
            CF output: <code style={{ ...mono, fontSize: 12, background: GH.bg3, padding: '1px 5px', borderRadius: 3 }}>ParsedRepo</code> JSON
            serialized without whitespace. Counted with tiktoken cl100k_base.
          </p>
          <p style={{ marginBottom: 12 }}>
            <strong style={{ color: GH.text }}>Recall.</strong> Every function in the raw AST checked against
            <code style={{ ...mono, fontSize: 12, background: GH.bg3, padding: '1px 5px', borderRadius: 3 }}> ParsedRepo.functions</code> by
            qualified name. 100% across all 14 repos.
          </p>
          <p>
            <strong style={{ color: GH.text }}>Retention.</strong> 5 functions sampled per repo (stratified by type).
            Gemini 2.5 Flash scores each on: (1) signature accuracy, (2) docstring fidelity, (3) call-chain completeness.
            Score is mean across all 3 dimensions, all 5 functions. Judge model was not involved in parsing.
          </p>
        </div>

      </div>
    </div>
  );
}
