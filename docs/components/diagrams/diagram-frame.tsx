import type { ReactNode } from 'react';
import styles from './diagram.module.css';

export type DiagramFrameProps = {
  id?: string;
  title?: string;
  caption?: string;
  description: string;
  children: ReactNode;
  controls?: ReactNode;
  fallback?: ReactNode;
};

/**
 * Shared chrome for every diagram: optional title/caption, accessible
 * description, optional controls, and a no-JS / print fallback slot.
 */
export function DiagramFrame({
  id,
  title,
  caption,
  description,
  children,
  controls,
  fallback,
}: DiagramFrameProps) {
  const descId = `diagram-desc-${(title ?? 'diagram').replace(/\s+/g, '-').toLowerCase().slice(0, 40)}`;
  return (
    <figure className={styles.frame} data-diagram-id={id} aria-describedby={descId}>
      {title || caption ? (
        <figcaption>
          {title ? <p className={styles.title}>{title}</p> : null}
          {caption ? <p className={styles.caption}>{caption}</p> : null}
        </figcaption>
      ) : null}
      <p id={descId} className={styles.description}>
        {description}
      </p>
      <div className={styles.canvas}>{children}</div>
      {controls}
      {fallback ? (
        <details className={styles.fallback}>
          <summary>Text version</summary>
          {fallback}
        </details>
      ) : null}
    </figure>
  );
}
