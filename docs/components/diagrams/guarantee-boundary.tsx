import { DiagramFrame } from './diagram-frame';
import frameStyles from './diagram.module.css';
import styles from './home.module.css';
import type { BoundaryDataset } from './types';

export type GuaranteeBoundaryProps = {
  dataset: BoundaryDataset;
  title: string;
  caption: string;
  description: string;
};

/**
 * One bounded zone for what agentsparty checks, with the rest rendered outside it
 * in neutral grey. Outside is not "bad" — it is outside the domain of
 * definition, and the geometry says so.
 */
export function GuaranteeBoundary({ dataset, title, caption, description }: GuaranteeBoundaryProps) {
  return (
    <DiagramFrame
      id={dataset.id}
      title={title}
      caption={caption}
      description={description}
      fallback={
        <div>
          <p>
            <strong>{dataset.insideLabel}</strong>
          </p>
          <ul className={frameStyles.staticList}>
            {dataset.inside.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p>
            <strong>{dataset.outsideLabel}</strong>
          </p>
          <ul className={frameStyles.staticList}>
            {dataset.outside.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      }
    >
      <div className={styles.boundaryRoot}>
        <p className={styles.boundaryOutsideLabel}>{dataset.outsideLabel}</p>
        <div className={styles.boundaryInside}>
          <p className={styles.boundaryInsideLabel}>{dataset.insideLabel}</p>
          <div className={styles.boundaryChips}>
            {dataset.inside.map((item) => (
              <span key={item} className={styles.boundaryChip}>
                {item}
              </span>
            ))}
          </div>
        </div>
        <div className={styles.boundaryOutsideRow}>
          {dataset.outside.map((item) => (
            <span key={item} className={styles.boundaryChipOutside}>
              {item}
            </span>
          ))}
        </div>
        <p className={styles.boundaryFootnote}>
          Outside the boundary is not “bad” — it is outside the domain of definition.
        </p>
      </div>
    </DiagramFrame>
  );
}
