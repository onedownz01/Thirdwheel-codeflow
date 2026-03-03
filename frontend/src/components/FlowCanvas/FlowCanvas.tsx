import { useEffect, useRef } from 'react';
import ELK from 'elkjs/lib/elk.bundled.js';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useFlowStore } from '../../store/flowStore';
import { FunctionBlock } from './FunctionBlock';
import type { ParsedRepo } from '../../types';

const nodeTypes = { functionBlock: FunctionBlock };
const elk = new ELK();
const LARGE_GRAPH_THRESHOLD = 700;
const LARGE_GRAPH_NODE_CAP = 480;
const LARGE_GRAPH_EDGE_CAP = 2200;

async function layoutGraph(nodes: Node[], edges: Edge[]): Promise<Node[]> {
  const graph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.edgeRouting': 'SPLINES',
      'elk.spacing.nodeNode': '40',
      'elk.layered.spacing.nodeNodeBetweenLayers': '90',
      'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES',
      'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
    },
    children: nodes.map((n) => ({ id: n.id, width: 300, height: 140 })),
    edges: edges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };

  const out = await elk.layout(graph as never);
  return nodes.map((node) => {
    const found = out.children?.find((c) => c.id === node.id);
    return {
      ...node,
      position: { x: found?.x ?? 0, y: found?.y ?? 0 },
    };
  });
}

function FlowCanvasInner() {
  const { repo, blockStates, activeIntent, fitViewNonce } = useFlowStore();
  const flow = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const renderIdsRef = useRef<Set<string>>(new Set());
  const repoKeyRef = useRef<string>('');
  const layoutRunRef = useRef(0);

  useEffect(() => {
    if (!repo) {
      renderIdsRef.current = new Set();
      repoKeyRef.current = '';
      setNodes([]);
      setEdges([]);
      return;
    }

    const flowSet = new Set(activeIntent?.flow_ids || []);
    const renderIds = selectRenderableNodeIds(repo, flowSet);
    const repoKey = `${repo.repo}::${repo.functions.length}::${repo.edges.length}`;
    const renderChanged = !sameSet(renderIdsRef.current, renderIds);
    const repoChanged = repoKeyRef.current !== repoKey;
    renderIdsRef.current = renderIds;
    repoKeyRef.current = repoKey;

    const fnById = new Map(repo.functions.map((fn) => [fn.id, fn]));
    const renderFns = Array.from(renderIds)
      .map((id) => fnById.get(id))
      .filter((fn): fn is NonNullable<typeof fn> => Boolean(fn));

    const nextNodes: Node[] = renderFns.map((fn) => ({
      id: fn.id,
      type: 'functionBlock',
      position: { x: 0, y: 0 },
      data: { fn, state: blockStates[fn.id] || { status: 'idle' } },
    }));

    const filteredEdges = repo.edges
      .filter((e) => renderIds.has(e.source) && renderIds.has(e.target))
      .slice(0, repo.functions.length > LARGE_GRAPH_THRESHOLD ? LARGE_GRAPH_EDGE_CAP : repo.edges.length);

    const nextEdges: Edge[] = styleEdges(filteredEdges, flowSet);

    if (!repoChanged && !renderChanged) {
      setEdges(nextEdges);
      return;
    }

    const runId = ++layoutRunRef.current;
    layoutGraph(nextNodes, nextEdges).then((layoutedNodes) => {
      if (runId !== layoutRunRef.current) return;
      setNodes(layoutedNodes);
      setEdges(nextEdges);
    });
  }, [repo, activeIntent, setNodes, setEdges]);

  useEffect(() => {
    setNodes((curr) =>
      curr.map((node) => ({
        ...node,
        data: {
          ...(node.data && typeof node.data === 'object' ? node.data : {}),
          state: blockStates[node.id] || { status: 'idle' },
        },
      }))
    );
  }, [blockStates, setNodes]);

  useEffect(() => {
    if (!repo) return;
    flow.fitView({ padding: 0.15, duration: 300 });
  }, [fitViewNonce, flow, repo]);

  if (!repo) {
    return <div className="canvas-empty">Parse a repository to see function graph.</div>;
  }

  return (
    <div className="canvas-wrap">
      {repo.functions.length > LARGE_GRAPH_THRESHOLD && (
        <div className="canvas-hint">
          Large graph mode: rendering top {Math.min(LARGE_GRAPH_NODE_CAP, repo.functions.length)} nodes.
          Select an intent to prioritize relevant flow nodes.
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        defaultEdgeOptions={{
          type: 'bezier',
          interactionWidth: 20,
          zIndex: 1,
        }}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.1}
        maxZoom={2}
        style={{ background: 'transparent' }}
      >
        <Background color="rgba(127, 138, 158, 0.35)" gap={20} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            const status = n.data?.state?.status;
            if (status === 'calling') return '#0ea5a4';
            if (status === 'returned') return '#22c55e';
            if (status === 'error') return '#dc2626';
            if (status === 'dimmed') return '#cbd5e1';
            return '#94a3b8';
          }}
          style={{
            background: 'rgba(255,255,255,0.58)',
            border: '1px solid rgba(255,255,255,0.75)',
            borderRadius: 14,
            backdropFilter: 'blur(10px)',
            boxShadow: '0 16px 30px -22px rgba(15,23,42,0.4)',
          }}
        />
      </ReactFlow>
    </div>
  );
}

function styleEdges(sourceEdges: ParsedRepo['edges'], flowSet: Set<string>): Edge[] {
  return sourceEdges.map((e) => {
    const active = flowSet.has(e.source) && flowSet.has(e.target);
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'bezier',
      animated: active,
      className: active ? 'edge-active' : 'edge-idle',
      style: {
        stroke: active ? '#111827' : 'rgba(15, 23, 42, 0.28)',
        strokeWidth: active ? 2.4 : 1.45,
        strokeDasharray: active ? '8 5' : undefined,
        strokeLinecap: 'round',
        opacity: active ? 1 : 0.78,
      },
    };
  });
}

function selectRenderableNodeIds(repo: ParsedRepo, flowSet: Set<string>): Set<string> {
  if (repo.functions.length <= LARGE_GRAPH_THRESHOLD) {
    return new Set(repo.functions.map((fn) => fn.id));
  }
  const hasFlowIntersection =
    flowSet.size === 0 ? false : repo.functions.some((fn) => flowSet.has(fn.id));

  const degree = new Map<string, number>();
  for (const fn of repo.functions) degree.set(fn.id, 0);
  for (const edge of repo.edges) {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
  }

  const scored = [...repo.functions].sort((a, b) => {
    const aBoost = hasFlowIntersection && flowSet.has(a.id) ? 1000 : 0;
    const bBoost = hasFlowIntersection && flowSet.has(b.id) ? 1000 : 0;
    const aType = a.type === 'route' || a.type === 'handler' ? 30 : 0;
    const bType = b.type === 'route' || b.type === 'handler' ? 30 : 0;
    const aScore = (degree.get(a.id) || 0) + aBoost + aType;
    const bScore = (degree.get(b.id) || 0) + bBoost + bType;
    return bScore - aScore;
  });

  const selected = new Set<string>(hasFlowIntersection ? [...flowSet] : []);
  for (const fn of scored) {
    if (selected.size >= LARGE_GRAPH_NODE_CAP) break;
    selected.add(fn.id);
  }
  return selected;
}

function sameSet(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const v of a) {
    if (!b.has(v)) return false;
  }
  return true;
}

export function FlowCanvas() {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner />
    </ReactFlowProvider>
  );
}
