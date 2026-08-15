import type { Edge, Node, Position } from '@xyflow/react';
import type {
  BoardDataset,
  PlayerDataset,
  ProjectionDataset,
  SequenceDataset,
  TimelineDataset,
} from './types';

export type FlowNodeData = {
  readonly label: string;
  readonly detail?: string;
  readonly kind?: string;
  readonly layoutColumn?: number;
  readonly active?: boolean;
  readonly dimmed?: boolean;
};

export type FlowNode = Node<FlowNodeData, 'card'>;
export type FlowEdge = Edge<{ readonly kind?: string }>;

export type FlowGraph = {
  readonly nodes: readonly FlowNode[];
  readonly edges: readonly FlowEdge[];
  readonly direction?: 'DOWN' | 'RIGHT';
};

const card = (id: string, label: string, detail?: string, layoutColumn?: number): FlowNode => ({
  id,
  type: 'card',
  position: { x: 0, y: 0 },
  sourcePosition: 'right' as Position,
  targetPosition: 'left' as Position,
  data: { label, detail, layoutColumn },
});

// Arrowhead colour follows the same palette as the edge stroke (flow.module.css).
const MARKER_COLORS: Record<string, string> = {
  alt: 'var(--diagram-amber)',
  model: 'var(--diagram-blue)',
  tool: 'var(--diagram-green)',
  cancel: 'var(--diagram-red)',
  replay: 'var(--diagram-cyan)',
  projection: 'var(--diagram-violet)',
};

const link = (
  id: string,
  source: string,
  target: string,
  label?: string,
  kind?: string,
): FlowEdge => ({
  id,
  source,
  target,
  type: 'smoothstep',
  label,
  animated: true,
  className: kind ? `flow-edge-${kind}` : undefined,
  data: { kind },
  markerEnd: {
    type: 'arrowclosed',
    color: MARKER_COLORS[kind ?? ''] ?? 'var(--diagram-primary)',
    width: 16,
    height: 16,
  },
});

const sequenceGraph = (dataset: SequenceDataset): FlowGraph => ({
  nodes: dataset.roles.map((role, index) => {
    const messages = dataset.messages.filter((message) => message.from === role || message.to === role);
    return {
      ...card(role, role, `${messages.length} messages`, index),
      data: { label: role, detail: `${messages.length} messages`, kind: 'role', layoutColumn: index },
    };
  }),
  edges: dataset.messages.map((message) =>
    link(message.id, message.from, message.to, message.label, message.kind),
  ),
});

const projectionGraph = (dataset: ProjectionDataset): FlowGraph => ({
  nodes: [
    {
      ...card('global', 'Global protocol', dataset.global.join('\n'), 0),
      data: { label: 'Global protocol', detail: dataset.global.join('\n'), kind: 'global', layoutColumn: 0 },
    },
    ...dataset.endpoints.map((endpoint, index) => ({
      ...card(endpoint.role, endpoint.role, endpoint.lines.join('\n'), index + 1),
      data: { label: endpoint.role, detail: endpoint.lines.join('\n'), kind: 'endpoint', layoutColumn: index + 1 },
    })),
  ],
  edges: dataset.endpoints.map((endpoint) =>
    link(`global-${endpoint.role}`, 'global', endpoint.role, 'projection', 'projection'),
  ),
});

const timelineGraph = (dataset: TimelineDataset): FlowGraph => ({
  nodes: dataset.events.map((event, index) => ({
    ...card(event.id, event.label, `t=${event.at}${event.facet ? ` · ${event.facet}` : ''}`, index),
    data: {
      label: event.label,
      detail: `t=${event.at}${event.facet ? ` · ${event.facet}` : ''}`,
      kind: event.kind,
      layoutColumn: index,
    },
  })),
  edges: dataset.events.slice(1).map((event, index) =>
    link(`timeline-${dataset.events[index].id}-${event.id}`, dataset.events[index].id, event.id),
  ),
});

const boardGraph = (dataset: BoardDataset): FlowGraph => {
  const columnIds = dataset.columns ?? [dataset.nodes.map((node) => node.id)];
  const columns = new Map(
    columnIds.flatMap((ids, column) => ids.map((id) => [id, column] as const)),
  );
  const edges = (dataset.edges ?? []).map((edge, index) =>
    link(`board-${index}-${edge.from}-${edge.to}`, edge.from, edge.to, edge.label, 'board'),
  );
  const layoutEdges = edges.length
    ? []
    : columnIds.flatMap((ids) =>
        ids.slice(1).map((id, index) => ({
          ...link(`layout-${ids[index]}-${id}`, ids[index], id),
          hidden: true,
          animated: false,
        })),
      );
  return {
    nodes: dataset.nodes.map((node) => ({
      ...card(node.id, node.label, node.detail, columns.get(node.id)),
      data: { label: node.label, detail: node.detail, kind: 'board', layoutColumn: columns.get(node.id) },
    })),
    edges: [...edges, ...layoutEdges],
  };
};

export const playerGraph = (dataset: PlayerDataset): FlowGraph => ({
  nodes: dataset.steps.map((step, index) => ({
    ...card(step.id, step.title, step.body, index),
    data: { label: step.title, detail: step.body, kind: 'step', layoutColumn: index },
  })),
  edges: dataset.steps.slice(1).map((step, index) =>
    link(`step-${dataset.steps[index].id}-${step.id}`, dataset.steps[index].id, step.id, 'next', 'step'),
  ),
});

export const buildSequenceGraph = sequenceGraph;
export const buildProjectionGraph = projectionGraph;
export const buildTimelineGraph = timelineGraph;
export const buildBoardGraph = boardGraph;
