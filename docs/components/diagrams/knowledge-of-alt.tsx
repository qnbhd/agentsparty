'use client';

import { useState } from 'react';
import { DiagramFrame } from './diagram-frame';
import frameStyles from './diagram.module.css';
import styles from './home.module.css';
import type { KnowledgeDataset } from './types';

export type KnowledgeOfChoiceProps = {
  dataset: KnowledgeDataset;
  title: string;
  caption: string;
  description: string;
};

function StatusLine({ fixed, dataset }: { fixed: boolean; dataset: KnowledgeDataset }) {
  const line = fixed ? dataset.okLine : dataset.errorLine;
  const [call, result] = line.split('→').map((part) => part.trim());
  return (
    <p className={styles.knowledgeStatus}>
      <span className={styles.knowledgeStatusCall}>{call}</span>
      <span aria-hidden="true">→</span>
      <span className={fixed ? styles.knowledgeStatusOk : styles.knowledgeStatusError}>
        {result}
      </span>
    </p>
  );
}

/**
 * Two branch cards (Yes / No) plus the local view of the blind role C. The
 * broken/fixed toggle is a diff: the fixed state adds one informing row in
 * each branch and gives C's local view a common `?A` prefix. The fault tone is
 * used for exactly one thing — the `ProjectionError` outcome.
 */
export function KnowledgeOfChoice({ dataset, description }: KnowledgeOfChoiceProps) {
  const [fixed, setFixed] = useState(false);

  return (
    <DiagramFrame
      id={dataset.id}
      description={description}
      fallback={
        <pre className={frameStyles.renderText}>
          {[dataset.brokenGlobal, dataset.errorMessage, '', dataset.fixedGlobal, '', dataset.fixedLocal].join(
            '\n',
          )}
        </pre>
      }
    >
      <div className={styles.knowledgeToggle} role="group" aria-label="Projection of C: broken or fixed">
        <button
          type="button"
          className={styles.knowledgeToggleButton}
          aria-pressed={!fixed}
          onClick={() => setFixed(false)}
        >
          Broken
        </button>
        <button
          type="button"
          className={styles.knowledgeToggleButton}
          aria-pressed={fixed}
          onClick={() => setFixed(true)}
        >
          Fixed
        </button>
      </div>

      <div className={styles.knowledgeWorlds}>
        {dataset.worlds.map((world) => (
          <div key={world.id} className={styles.knowledgeWorld}>
            <p className={styles.knowledgeWorldTitle}>Branch {world.label}</p>
            <p className={styles.knowledgeRow}>
              {dataset.chooser} -&gt; {dataset.peer} : {world.label}
            </p>
            {fixed ? (
              <p className={`${styles.knowledgeRow} ${styles.knowledgeRowNew}`}>{world.inform}</p>
            ) : null}
            <p className={styles.knowledgeRow}>{world.message}</p>
            <p className={styles.knowledgeRowNote}>{world.action}</p>
          </div>
        ))}
      </div>
      {fixed ? <p className={styles.knowledgeNewNote}>{dataset.newNote}</p> : null}

      <div className={styles.knowledgeLocal}>
        <p className={styles.knowledgeLocalTitle}>Local view of {dataset.blind}</p>
        {fixed ? (
          <div className={styles.knowledgeCode}>
            {dataset.localViewFixed.map((line, i) => (
              <p key={i} className={styles.knowledgeCodeLine}>
                {i === 0 ? (
                  <>
                    <span className={styles.knowledgeCommonPrefix}>
                      {line.slice(0, line.indexOf(' '))}
                    </span>
                    {line.slice(line.indexOf(' '))}
                  </>
                ) : (
                  line
                )}
              </p>
            ))}
          </div>
        ) : (
          <div className={styles.knowledgeHalves}>
            <div>
              <p className={styles.knowledgeHalfCaption}>if Yes ran</p>
              <div className={styles.knowledgeHalf}>{dataset.localViewBroken[0]}</div>
            </div>
            <div className={styles.knowledgeNeq} aria-hidden="true">
              ≠
            </div>
            <div>
              <p className={styles.knowledgeHalfCaption}>if No ran</p>
              <div className={styles.knowledgeHalf}>{dataset.localViewBroken[1]}</div>
            </div>
          </div>
        )}
        <p className={styles.knowledgeNote}>{fixed ? dataset.fixedNote : dataset.note}</p>
      </div>

      <StatusLine fixed={fixed} dataset={dataset} />
    </DiagramFrame>
  );
}
