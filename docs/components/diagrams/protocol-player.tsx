'use client';

import { useCallback, useEffect, useState } from 'react';
import { DiagramControls } from './diagram-controls';
import { DiagramFrame } from './diagram-frame';
import { playerGraph } from './flow-data';
import { FlowView } from './flow-view';
import styles from './diagram.module.css';
import type { PlayerDataset } from './types';

export type ProtocolPlayerProps = {
  dataset: PlayerDataset;
  caption: string;
  description: string;
  autoplay?: boolean;
};

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function ProtocolPlayer({
  dataset,
  caption,
  description,
  autoplay = false,
}: ProtocolPlayerProps) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const step = dataset.steps[index] ?? dataset.steps[0];
  const count = dataset.steps.length;
  const graph = playerGraph(dataset);
  const activeEdge = index < count - 1
    ? `step-${dataset.steps[index].id}-${dataset.steps[index + 1].id}`
    : undefined;

  const onPrev = useCallback(() => setIndex((i) => Math.max(0, i - 1)), []);
  const onNext = useCallback(() => setIndex((i) => Math.min(count - 1, i + 1)), [count]);
  const onReplay = useCallback(() => {
    setIndex(0);
    setPlaying(false);
  }, []);
  const onPlayPause = useCallback(() => setPlaying((p) => !p), []);

  useEffect(() => {
    if (!autoplay || prefersReducedMotion()) return;
    setPlaying(true);
  }, [autoplay]);

  useEffect(() => {
    if (!playing || prefersReducedMotion()) return;
    if (index >= count - 1) {
      setPlaying(false);
      return;
    }
    const t = window.setTimeout(() => setIndex((i) => i + 1), 1400);
    return () => window.clearTimeout(t);
  }, [playing, index, count]);

  return (
    <DiagramFrame
      id={dataset.id}
      title={dataset.title}
      caption={caption}
      description={description}
      controls={
        <DiagramControls
          stepIndex={index}
          stepCount={count}
          stepLabel={step?.title ?? ''}
          playing={playing}
          onPrev={onPrev}
          onNext={onNext}
          onPlayPause={onPlayPause}
          onReplay={onReplay}
        />
      }
      fallback={
        <div className={styles.printSteps}>
          <ol>
            {dataset.steps.map((s) => (
              <li key={s.id}>
                <strong>{s.title}</strong>: {s.body}
              </li>
            ))}
          </ol>
        </div>
      }
    >
      <FlowView
        graph={graph}
        ariaLabel={dataset.title}
        activeNodeIds={step ? [step.id] : undefined}
        activeEdgeIds={activeEdge ? [activeEdge] : undefined}
      />
      {step ? <p className={styles.currentStep}>{step.body}</p> : null}
      <noscript>
        <ol>
          {dataset.steps.map((s) => (
            <li key={s.id}>
              {s.title}: {s.body}
            </li>
          ))}
        </ol>
      </noscript>
    </DiagramFrame>
  );
}
