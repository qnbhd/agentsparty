import { DiagramFrame } from './diagram-frame';
import styles from './diagram.module.css';
import { buildProjectionGraph } from './flow-data';
import { FlowView } from './flow-view';
import { LinkedProjection } from './linked-projection';
import type { ProjectionDataset } from './types';

export type ProjectionViewProps = {
  dataset: ProjectionDataset;
  title: string;
  caption: string;
  description: string;
};

export function ProjectionView({ dataset, title, caption, description }: ProjectionViewProps) {
  if (dataset.variant === 'linked') {
    return (
      <LinkedProjection
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
        <div>
          <p>
            <strong>Global</strong>
          </p>
          <ul className={styles.staticList}>
            {dataset.global.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {dataset.endpoints.map((col) => (
            <div key={col.role}>
              <p>
                <strong>{col.role}</strong>
              </p>
              <ul className={styles.staticList}>
                {col.lines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      }
    >
      <FlowView graph={buildProjectionGraph(dataset)} ariaLabel={title} />
    </DiagramFrame>
  );
}
