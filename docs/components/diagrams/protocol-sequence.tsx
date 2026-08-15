import { DiagramFrame } from './diagram-frame';
import { buildSequenceGraph } from './flow-data';
import { FlowView } from './flow-view';
import { LifelineSequence } from './lifeline-sequence';
import type { SequenceDataset } from './types';

export type ProtocolSequenceProps = {
  dataset: SequenceDataset;
  title: string;
  caption: string;
  description: string;
  activeId?: string;
};

// SequenceDataset requires kind: 'sequence' at the registry boundary.

export function ProtocolSequence({
  dataset,
  title,
  caption,
  description,
  activeId,
}: ProtocolSequenceProps) {
  if (dataset.variant === 'lifeline') {
    return (
      <LifelineSequence
        dataset={dataset}
        title={title}
        caption={caption}
        description={description}
      />
    );
  }
  return (
    <DiagramFrame
      id={dataset.id}
      title={title}
      caption={caption}
      description={description}
      fallback={
        <ol>
          {dataset.messages.map((m) => (
            <li key={m.id}>
              {m.from} → {m.to}: {m.label}
            </li>
          ))}
        </ol>
      }
    >
      <FlowView
        graph={buildSequenceGraph(dataset)}
        ariaLabel={title}
        activeNodeIds={activeId ? [activeId] : undefined}
      />
    </DiagramFrame>
  );
}
