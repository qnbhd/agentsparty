import { DiagramFrame } from './diagram-frame';
import styles from './diagram.module.css';
import { buildBoardGraph } from './flow-data';
import { FlowView } from './flow-view';
import type { BoardDataset } from './types';

export type BoardViewProps = {
  dataset: BoardDataset;
  title: string;
  caption: string;
  description: string;
};

export function BoardView({ dataset, title, caption, description }: BoardViewProps) {
  return (
    <DiagramFrame
      id={dataset.id}
      title={title}
      caption={caption}
      description={description}
      fallback={
        <ul className={styles.staticList}>
          {dataset.nodes.map((n) => (
            <li key={n.id}>
              {n.label}
              {n.detail ? ` — ${n.detail}` : ''}
            </li>
          ))}
          {(dataset.edges ?? []).map((e, i) => (
            <li key={`e-${i}`}>
              {e.from} → {e.to}
              {e.label ? `: ${e.label}` : ''}
            </li>
          ))}
        </ul>
      }
    >
      <FlowView graph={buildBoardGraph(dataset)} ariaLabel={title} />
    </DiagramFrame>
  );
}
