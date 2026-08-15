import { DiagramFrame } from './diagram-frame';
import styles from './diagram.module.css';
import { buildTimelineGraph } from './flow-data';
import { FlowView } from './flow-view';
import type { TimelineDataset } from './types';

export type TimelineProps = {
  dataset: TimelineDataset;
  title: string;
  caption: string;
  description: string;
};

export function Timeline({ dataset, title, caption, description }: TimelineProps) {
  return (
    <DiagramFrame
      id={dataset.id}
      title={title}
      caption={caption}
      description={description}
      fallback={
        <ol className={styles.staticList}>
          {dataset.events.map((e) => (
            <li key={e.id}>
              t={e.at}: {e.label}
              {e.facet ? ` [${e.facet}]` : ''}
            </li>
          ))}
        </ol>
      }
    >
      <FlowView graph={buildTimelineGraph(dataset)} ariaLabel={title} />
    </DiagramFrame>
  );
}
