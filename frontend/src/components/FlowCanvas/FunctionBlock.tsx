import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { BlockState, FunctionType, ParsedFunction } from '../../types';

interface Props {
  data: {
    fn: ParsedFunction;
    state: BlockState;
  };
}

const TYPE_COLORS: Record<FunctionType, string> = {
  component: '#28a98a',
  hook: '#8c6cf8',
  route: '#3b82f6',
  handler: '#0ea5a4',
  service: '#2563eb',
  db: '#f59e0b',
  auth: '#f43f5e',
  util: '#64748b',
  other: '#475569'
};

export const FunctionBlock = memo(({ data }: Props) => {
  const { fn, state } = data;
  const color = TYPE_COLORS[fn.type];

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    try {
      const text = JSON.stringify(value);
      return text.length > 80 ? `${text.slice(0, 80)}...` : text;
    } catch {
      return String(value);
    }
  };

  return (
    <div className={`fn-block state-${state.status}`} style={{ borderLeftColor: color }}>
      <Handle type="target" position={Position.Left} className="fn-handle" />

      {state.stepNumber !== undefined && <div className="step-badge">{state.stepNumber}</div>}

      <div className="fn-header">
        <span className="fn-type" style={{ borderColor: color, color }}>
          {fn.type}
        </span>
        <span className="fn-name">{fn.name}</span>
        {state.durationMs !== undefined && <span className="fn-time">{Math.round(state.durationMs)}ms</span>}
      </div>

      <div className="fn-file">
        {fn.file}:{fn.line}
      </div>

      <div className="fn-body">
        {fn.params.slice(0, 5).map((p) => {
          const runtime = state.inputs?.find((v) => v.name === p.name) || state.outputs?.find((v) => v.name === p.name);
          return (
            <div key={p.name} className="fn-param">
              <span>{p.direction === 'in' ? '→' : '←'}</span>
              <span>{p.name}</span>
              <span>{runtime ? formatValue(runtime.value) : p.type}</span>
            </div>
          );
        })}

        {state.error && <div className="fn-error">{state.error}</div>}
      </div>

      <Handle type="source" position={Position.Right} className="fn-handle" />
    </div>
  );
});
