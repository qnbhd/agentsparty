'use client';

import styles from './diagram.module.css';

export type DiagramControlsProps = {
  stepIndex: number;
  stepCount: number;
  stepLabel: string;
  playing: boolean;
  onPrev: () => void;
  onNext: () => void;
  onPlayPause: () => void;
  onReplay: () => void;
};

export function DiagramControls({
  stepIndex,
  stepCount,
  stepLabel,
  playing,
  onPrev,
  onNext,
  onPlayPause,
  onReplay,
}: DiagramControlsProps) {
  return (
    <div className={styles.controls} role="group" aria-label="Diagram step controls">
      <button type="button" onClick={onPrev} disabled={stepIndex <= 0} aria-label="Previous step">
        Previous
      </button>
      <button type="button" onClick={onPlayPause} aria-label={playing ? 'Pause' : 'Play'}>
        {playing ? 'Pause' : 'Play'}
      </button>
      <button
        type="button"
        onClick={onNext}
        disabled={stepIndex >= stepCount - 1}
        aria-label="Next step"
      >
        Next
      </button>
      <button type="button" onClick={onReplay} aria-label="Replay from start">
        Replay
      </button>
      <span className={styles.stepLabel} aria-live="polite">
        Step {stepIndex + 1}/{stepCount}: {stepLabel}
      </span>
    </div>
  );
}
