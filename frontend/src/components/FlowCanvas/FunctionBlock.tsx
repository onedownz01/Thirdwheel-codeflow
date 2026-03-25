import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { BlockState, ParsedFunction } from '../../types';
import { useFlowStore } from '../../store/flowStore';

interface Props {
  data: {
    fn: ParsedFunction;
    state: BlockState;
  };
}

export const FunctionBlock = memo(({ data }: Props) => {
  const { fn, state } = data;
  const { selectedNodeId, setSelectedNode } = useFlowStore();

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) return 'null';
    if (typeof value === 'string') return value.length > 40 ? `${value.slice(0, 40)}…` : value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    try {
      const text = JSON.stringify(value);
      return text.length > 40 ? `${text.slice(0, 40)}…` : text;
    } catch {
      return String(value);
    }
  };

  // Inputs: prefer runtime values, fall back to static params
  const inputRows = state.inputs && state.inputs.length > 0
    ? state.inputs.slice(0, 6).map((v) => ({ name: v.name, val: formatValue(v.value), sensitive: v.is_sensitive }))
    : fn.params.filter((p) => p.direction !== 'out').slice(0, 6).map((p) => ({ name: p.name, val: p.type, sensitive: false }));

  // Outputs: only show when returned
  const outputRows = state.outputs && state.outputs.length > 0
    ? state.outputs.slice(0, 4).map((v) => ({ name: v.name, val: formatValue(v.value), sensitive: v.is_sensitive }))
    : [];

  const isSelected = selectedNodeId === fn.id;

  return (
    <div
      className={`fn-block state-${state.status}${isSelected ? ' fn-block-selected' : ''}`}
      onClick={() => setSelectedNode(isSelected ? null : fn.id)}
    >
      <Handle type="target" position={Position.Left} className="fn-handle" />

      <div className="fn-header">
        {state.stepNumber !== undefined && (
          <span className="fn-step">{state.stepNumber}</span>
        )}
        <span className="fn-name">{fn.name}</span>
        <span className="fn-type-tag">{fn.type}</span>
        {state.durationMs !== undefined && (
          <span className="fn-time">{Math.round(state.durationMs)}ms</span>
        )}
      </div>

      <div className="fn-file">{fn.file}:{fn.line}</div>

      {inputRows.length > 0 && (
        <div className="fn-rows">
          {inputRows.map((row, i) => (
            <div className="fn-row fn-row-in" key={`in-${i}`}>
              <span className="row-dot">◆</span>
              <span className="row-name">{row.name}</span>
              <span className="row-val">{row.sensitive ? '••••••' : row.val}</span>
            </div>
          ))}
        </div>
      )}

      {outputRows.length > 0 && (
        <div className="fn-rows fn-rows-out">
          {outputRows.map((row, i) => (
            <div className="fn-row fn-row-out" key={`out-${i}`}>
              <span className="row-dot">◇</span>
              <span className="row-name">{row.name}</span>
              <span className="row-val">{row.sensitive ? '••••••' : row.val}</span>
            </div>
          ))}
        </div>
      )}

      {state.error && (
        <div className="fn-error">{state.error}</div>
      )}

      <Handle type="source" position={Position.Right} className="fn-handle" />
    </div>
  );
});
