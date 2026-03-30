import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

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

const STEPS = [
  {
    n: '01',
    label: 'Clone the repo',
    cmd: 'git clone https://github.com/onedownz01/Thirdwheel-codeflow\ncd Thirdwheel-codeflow',
  },
  {
    n: '02',
    label: 'Start the backend',
    cmd: 'python3 -m venv .venv\nsource .venv/bin/activate\npip install -r backend/requirements.txt\nuvicorn backend.main:app --reload --port 8001',
  },
  {
    n: '03',
    label: 'Start the frontend',
    cmd: 'cd frontend\nnpm install\nnpm run dev',
  },
];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button
      onClick={copy}
      style={{
        ...mono, background: 'none', border: `1px solid ${C.border}`,
        color: copied ? C.text : C.muted,
        cursor: 'pointer', fontSize: 9, fontWeight: 500,
        padding: '3px 10px', letterSpacing: '0.06em',
        transition: 'color 0.15s, border-color 0.15s',
        flexShrink: 0,
      }}
      onMouseEnter={e => { if (!copied) e.currentTarget.style.color = C.text; }}
      onMouseLeave={e => { if (!copied) e.currentTarget.style.color = C.muted; }}
    >
      {copied ? 'COPIED' : 'COPY'}
    </button>
  );
}


export default function LaunchPage() {
  const navigate = useNavigate();

  return (
    <div style={{ ...sans, background: C.bg, color: C.text, minHeight: '100vh', fontWeight: 300 }}>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0a0a0a; }
      `}</style>

      {/* Nav */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        background: 'rgba(10,10,10,0.88)', backdropFilter: 'blur(16px)',
        borderBottom: `1px solid ${C.border}`,
        display: 'flex', alignItems: 'stretch', height: 44,
      }}>
        <div style={{
          display: 'flex', alignItems: 'center',
          padding: '0 24px', borderRight: `1px solid ${C.border}`,
        }}>
          <button
            onClick={() => navigate('/')}
            style={{ ...mono, background: 'none', border: 'none', color: C.muted, cursor: 'pointer', fontSize: 12, fontWeight: 500, letterSpacing: '0.08em', padding: 0 }}
            onMouseEnter={e => (e.currentTarget.style.color = C.text)}
            onMouseLeave={e => (e.currentTarget.style.color = C.muted)}
          >
            CODEFLOW
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', padding: '0 20px' }}>
          <span style={{ ...mono, fontSize: 10, color: C.dim, letterSpacing: '0.04em' }}>/ LAUNCH</span>
        </div>
      </nav>

      {/* Content */}
      <div style={{
        maxWidth: 600, margin: '0 auto',
        padding: '120px 32px 80px',
        display: 'flex', flexDirection: 'column', gap: 0,
      }}>
        <p style={{ ...mono, fontSize: 10, color: C.muted, letterSpacing: '0.08em', marginBottom: 16, fontWeight: 500 }}>
          RUN LOCALLY
        </p>
        <h1 style={{ fontSize: 28, fontWeight: 300, color: C.text, letterSpacing: '-0.02em', lineHeight: 1.2, marginBottom: 12 }}>
          Codeflow runs on your machine.
        </h1>
        <p style={{ fontSize: 14, fontWeight: 300, color: C.muted, lineHeight: 1.75, marginBottom: 48 }}>
          Python 3.11+ and Node 18+ required. No accounts, no API keys for sim mode.
          Takes about 60 seconds.
        </p>

        {/* Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, background: C.border }}>
          {STEPS.map(step => (
            <div key={step.n} style={{ background: C.bg }}>
              {/* Step header */}
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '14px 18px 0',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ ...mono, fontSize: 9, color: C.dim, fontWeight: 500 }}>{step.n}</span>
                  <span style={{ fontSize: 13, fontWeight: 500, color: C.text }}>{step.label}</span>
                </div>
                <CopyButton text={step.cmd} />
              </div>
              {/* Code */}
              <pre style={{
                ...mono, fontSize: 12, lineHeight: 1.9,
                padding: '12px 18px 16px',
                margin: 0, color: C.muted, fontWeight: 300,
                overflowX: 'auto',
              }}>
                {step.cmd.split('\n').map((line, i) => (
                  <span key={i} style={{ display: 'block' }}>
                    <span style={{ color: C.dim, userSelect: 'none' }}>$ </span>
                    {line}
                  </span>
                ))}
              </pre>
            </div>
          ))}
        </div>

        {/* Note */}
        <p style={{ ...mono, fontSize: 10, color: C.dim, lineHeight: 1.8, marginTop: 20, fontWeight: 300 }}>
          Optional: set <span style={{ color: C.muted }}>GITHUB_TOKEN</span> in a .env file to avoid GitHub's 60 req/hr rate limit.
        </p>

        {/* CTA */}
        <div style={{ marginTop: 40, display: 'flex', gap: 1, alignItems: 'center' }}>
          <button
            onClick={() => navigate('/app')}
            style={{
              ...mono, background: C.text, color: C.bg,
              border: 'none', cursor: 'pointer',
              padding: '12px 28px', fontSize: 11,
              fontWeight: 500, letterSpacing: '0.06em',
              transition: 'opacity 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.opacity = '0.8')}
            onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
          >
            OPEN APP ↗
          </button>
          <span style={{ ...mono, fontSize: 10, color: C.dim, padding: '0 16px' }}>
            make sure the backend is running first
          </span>
        </div>
      </div>
    </div>
  );
}
