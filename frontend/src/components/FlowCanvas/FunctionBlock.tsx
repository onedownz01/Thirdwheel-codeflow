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
  component: '#32b67a',
  hook: '#e0a458',
  route: '#3f82d9',
  handler: '#4fb7ff',
  service: '#8dc891',
  db: '#ce7e2f',
  auth: '#c97f45',
  util: '#8a90a6',
  other: '#667085'
};

export const FunctionBlock = memo(({ data }: Props) => {
  const { fn, state } = data;
  const color = TYPE_COLORS[fn.type];

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
              <span>{runtime?.value ?? p.type}</span>
            </div>
          );
        })}

        {state.error && <div className="fn-error">{state.error}</div>}
      </div>

      <Handle type="source" position={Position.Right} className="fn-handle" />
    </div>
  );
});
