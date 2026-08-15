'use client';

import { useRef, useState } from 'react';
import { DiagramFrame } from './diagram-frame';
import frameStyles from './diagram.module.css';
import styles from './home.module.css';
import type { ProjectionDataset } from './types';

export type LinkedProjectionProps = {
  dataset: ProjectionDataset;
  title: string;
  caption: string;
  description: string;
};

/** Arrow keys move the selection; the moved-to row takes focus. */
const ARROW_STEP: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 };

/** Colour is carried by the `!`/`?` symbol itself, so it survives greyscale. */
const SYMBOL_CLASS: Record<string, string> = { '!': styles.projSend, '?': styles.projRecv };

/** `!Reviewer : Draft(str)` reads as a coloured symbol plus a neutral rest. */
function LocalLine({ line }: { line: string }) {
  const symbol = line.slice(0, 1);
  const cls = SYMBOL_CLASS[symbol];
  if (!cls) return <>{line}</>;
  return (
    <>
      <span className={cls}>{symbol}</span>
      {line.slice(1)}
    </>
  );
}

/**
 * One grid: a global line and its three local counterparts share a row band,
 * so a projection is read straight across. Selecting a row lights the whole
 * band — including the empty cell of a role the message never reaches.
 */
export function LinkedProjection({ dataset, title, caption, description }: LinkedProjectionProps) {
  const [active, setActive] = useState(0);
  const rows = useRef<(HTMLButtonElement | null)[]>([]);

  function move(event: React.KeyboardEvent, from: number) {
    const step = ARROW_STEP[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const next = (from + step + dataset.global.length) % dataset.global.length;
    setActive(next);
    rows.current[next]?.focus();
  }

  return (
    <DiagramFrame
      id={dataset.id}
      title={title}
      caption={caption}
      description={description}
      fallback={<pre className={frameStyles.renderText}>{dataset.renderText}</pre>}
    >
      <div className={styles.projGrid}>
        <div className={styles.projHead}>
          <span>Global protocol</span>
          <span className={styles.projRule} aria-hidden="true" />
          {dataset.endpoints.map((col) => (
            <span key={col.role}>{col.role}</span>
          ))}
        </div>
        {dataset.global.map((line, i) => (
          <button
            key={line}
            type="button"
            ref={(el) => {
              rows.current[i] = el;
            }}
            className={styles.projRow}
            aria-current={active === i ? 'true' : undefined}
            tabIndex={active === i ? 0 : -1}
            onClick={() => setActive(i)}
            onFocus={() => setActive(i)}
            onKeyDown={(event) => move(event, i)}
          >
            <span className={styles.projGlobalCell}>{line}</span>
            <span className={styles.projRule} aria-hidden="true" />
            {dataset.endpoints.map((col) => {
              const local = (col.slots ?? col.lines)[i] ?? null;
              return (
                <span key={col.role} className={styles.projLocalCell}>
                  {local === null ? (
                    <span className={styles.projNone} role="img" aria-label="not in this endpoint">
                      ·
                    </span>
                  ) : (
                    <LocalLine line={local} />
                  )}
                </span>
              );
            })}
          </button>
        ))}
      </div>
      <p className={styles.projHint}>
        Pick a global message (↑/↓ to walk): it becomes <span className={styles.projSend}>!</span>{' '}
        for the sender, <span className={styles.projRecv}>?</span> for the receiver, and nothing at
        all for the role it never reaches.
      </p>
    </DiagramFrame>
  );
}
