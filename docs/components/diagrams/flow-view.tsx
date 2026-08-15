'use client';

import { useEffect, useMemo, useState, type CSSProperties } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type NodeProps,
} from '@xyflow/react';
import ELK from 'elkjs/lib/elk.bundled.js';
import styles from './flow.module.css';
import type { FlowEdge, FlowGraph, FlowNode } from './flow-data';

type FlowViewProps = {
  readonly graph: FlowGraph;
  readonly ariaLabel: string;
  readonly activeNodeIds?: readonly string[];
  readonly activeEdgeIds?: readonly string[];
};

const nodeTypes = { card: FlowCardNode };
const elk = new ELK();

function FlowCardNode({ data, selected }: NodeProps<FlowNode>) {
  const accents: Record<string, string> = {
    cancel: 'var(--diagram-red)',
    alt: 'var(--diagram-amber)',
    endpoint: 'var(--diagram-blue)',
    global: 'var(--diagram-violet)',
    model: 'var(--diagram-blue)',
    replay: 'var(--diagram-cyan)',
    step: 'var(--diagram-amber)',
    tool: 'var(--diagram-green)',
  };
  const accent = accents[data.kind ?? ''] ?? 'var(--diagram-primary)';
  return (
    <>
      <Handle type="target" position={Position.Left} className={styles.handle} />
      <article
        className={`${styles.node} ${data.active ? styles.nodeActive : ''} ${data.dimmed ? styles.nodeDimmed : ''}`}
        data-kind={data.kind}
        data-selected={selected}
        style={{ '--flow-accent': accent } as CSSProperties}
      >
        <span className={styles.nodeLabel}>{data.label}</span>
        {data.detail ? <span className={styles.nodeDetail}>{data.detail}</span> : null}
      </article>
      <Handle type="source" position={Position.Right} className={styles.handle} />
    </>
  );
}

async function layoutGraph(graph: FlowGraph): Promise<FlowGraph> {
  const layout = await elk.layout({
    id: 'diagram',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': graph.direction ?? 'DOWN',
      'elk.spacing.nodeNode': '28',
      'elk.layered.spacing.nodeNodeBetweenLayers': '72',
      'elk.layered.considerModelOrder': 'NODES_AND_EDGES',
    },
    children: graph.nodes.map((node) => ({ id: node.id, width: 190, height: 76 })),
    edges: graph.edges.map((edge) => ({
      id: edge.id,
      sources: [edge.source],
      targets: [edge.target],
    })),
  });
  const positions = new Map(
    (layout.children ?? []).map((node) => [node.id, { x: node.x ?? 0, y: node.y ?? 0 }]),
  );
  return {
    nodes: graph.nodes.map((node) => ({ ...node, position: positions.get(node.id) ?? node.position })),
    edges: graph.edges,
  };
}

function FlowCanvas({ graph, ariaLabel, activeNodeIds, activeEdgeIds }: FlowViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>([...graph.nodes]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>([...graph.edges]);
  const [ready, setReady] = useState(false);
  const { fitView } = useReactFlow();
  const graphKey = useMemo(
    () => `${graph.nodes.map((node) => node.id).join(',')}|${graph.edges.map((edge) => edge.id).join(',')}`,
    [graph],
  );

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    layoutGraph(graph).then((laidOut) => {
      if (cancelled) return;
      setNodes([...laidOut.nodes]);
      setEdges([...laidOut.edges]);
      setReady(true);
      requestAnimationFrame(() => fitView({ padding: 0.2, duration: 450 }));
    });
    return () => {
      cancelled = true;
    };
  }, [fitView, graphKey, setEdges, setNodes]);

  const nodeSet = useMemo(() => new Set(activeNodeIds ?? []), [activeNodeIds]);
  const edgeSet = useMemo(() => new Set(activeEdgeIds ?? []), [activeEdgeIds]);
  const hasActiveNodes = nodeSet.size > 0;
  const hasActiveEdges = edgeSet.size > 0;
  const visibleNodes = nodes.map((node) => ({
    ...node,
    data: { ...node.data, active: nodeSet.has(node.id), dimmed: hasActiveNodes && !nodeSet.has(node.id) },
  }));
  const visibleEdges = edges.map((edge) => ({
    ...edge,
    animated: hasActiveEdges ? edgeSet.has(edge.id) : edge.animated,
    style: { ...edge.style, opacity: hasActiveEdges && !edgeSet.has(edge.id) ? 0.25 : 1 },
  }));

  return (
    <div className={styles.surface} aria-label={ariaLabel}>
      <ReactFlow
        nodes={visibleNodes}
        edges={visibleEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodesConnectable={false}
        edgesReconnectable={false}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2.2}
        nodesDraggable={false}
        selectionOnDrag
        panOnScroll
        aria-label={ariaLabel}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
        <Controls showInteractive={false} />
        <Panel position="top-right" className={styles.hint}>Zoom · pan · select</Panel>
        {!ready ? <Panel className={styles.loading}>Arranging graph…</Panel> : null}
      </ReactFlow>
    </div>
  );
}

export function FlowView(props: FlowViewProps) {
  return (
    <ReactFlowProvider>
      <FlowCanvas {...props} />
    </ReactFlowProvider>
  );
}
