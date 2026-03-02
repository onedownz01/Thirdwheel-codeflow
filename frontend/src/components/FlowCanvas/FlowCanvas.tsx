import { useEffect } from 'react';
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

const nodeTypes = { functionBlock: FunctionBlock };
const elk = new ELK();

async function layoutGraph(nodes: Node[], edges: Edge[]): Promise<Node[]> {
  const graph = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'RIGHT',
      'elk.edgeRouting': 'ORTHOGONAL',
      'elk.spacing.nodeNode': '45',
      'elk.layered.spacing.nodeNodeBetweenLayers': '95',
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

  useEffect(() => {
    if (!repo) return;

    const nextNodes: Node[] = repo.functions.map((fn) => ({
      id: fn.id,
      type: 'functionBlock',
      position: { x: 0, y: 0 },
      data: { fn, state: blockStates[fn.id] || { status: 'idle' } },
    }));

    const flowSet = new Set(activeIntent?.flow_ids || []);
    const nextEdges: Edge[] = repo.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      animated: flowSet.has(e.source) && flowSet.has(e.target),
      className: flowSet.has(e.source) ? 'edge-active' : 'edge-idle',
      style: {
        stroke: flowSet.has(e.source) ? '#4fb7ff' : '#344054',
        strokeWidth: flowSet.has(e.source) ? 2 : 1,
        strokeDasharray: flowSet.has(e.source) ? '6 4' : '2 6',
      },
    }));

    layoutGraph(nextNodes, nextEdges).then((layoutedNodes) => {
      setNodes(layoutedNodes);
      setEdges(nextEdges);
    });
  }, [repo, blockStates, activeIntent, setNodes, setEdges]);

  useEffect(() => {
    if (!repo) return;
    flow.fitView({ padding: 0.15, duration: 300 });
  }, [fitViewNonce, flow, repo]);

  if (!repo) {
    return <div className="canvas-empty">Parse a repository to see function graph.</div>;
  }

  return (
    <div className="canvas-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.1}
        maxZoom={2}
      >
        <Background color="#2a3441" gap={28} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            const status = n.data?.state?.status;
            if (status === 'calling') return '#4fb7ff';
            if (status === 'returned') return '#32b67a';
            if (status === 'error') return '#dc2626';
            if (status === 'dimmed') return '#1f2937';
            return '#64748b';
          }}
        />
      </ReactFlow>
    </div>
  );
}

export function FlowCanvas() {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner />
    </ReactFlowProvider>
  );
}
