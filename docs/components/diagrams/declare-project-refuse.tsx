'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { DiagramControls } from './diagram-controls';
import { DiagramFrame } from './diagram-frame';
import frameStyles from './diagram.module.css';
import styles from './home.module.css';
import type { PlayerDataset } from './types';

export type DeclareProjectRefuseProps = {
  dataset: PlayerDataset;
  caption: string;
  description: string;
  autoplay?: boolean;
};

const NODE_W = 150;
const NODE_H = 56;
const AXIS_Y = 90;

/** Node x positions on the horizontal strip. */
const NODES = [
  { x: 40, label: 'declare', sub: 'one conversation' },
  { x: 260, label: 'project', sub: 'one view per role' },
  { x: 480, label: 'gate', sub: 'knowledge checked' },
  { x: 720, label: 'run', sub: 'Cast.run' },
];

const MARKER = 'hero-arrow-declare-project-refuse';

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function DeclareProjectRefuse({
  dataset,
  caption,
  description,
  autoplay = true,
}: DeclareProjectRefuseProps) {
  const count = dataset.steps.length;
  const [index, setIndex] = useState(count - 1);
  const [playing, setPlaying] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (autoplay && !prefersReducedMotion()) {
      setIndex(0);
      setPlaying(true);
    } else {
      // Reduced motion (or no autoplay): land on the static final frame.
      setIndex(count - 1);
    }
  }, [autoplay, count]);

  useEffect(() => {
    if (!playing || prefersReducedMotion()) return;
    if (index >= count - 1) {
      setPlaying(false);
      return;
    }
    const t = window.setTimeout(() => setIndex((i) => i + 1), 1300);
    return () => window.clearTimeout(t);
  }, [playing, index, count]);

  const onPrev = useCallback(() => setIndex((i) => Math.max(0, i - 1)), []);
  const onNext = useCallback(() => setIndex((i) => Math.min(count - 1, i + 1)), [count]);
  const onReplay = useCallback(() => {
    setIndex(0);
    setPlaying(true);
  }, []);
  const onPlayPause = useCallback(() => setPlaying((p) => !p), []);

  const step = dataset.steps[index] ?? dataset.steps[count - 1];
  const showError = index >= 2;
  const showRunArrow = index >= 3;
  const nodeState = (i: number) => (i === index ? 'active' : i < index ? 'done' : 'future');

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
        <div className={frameStyles.printSteps}>
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
      <svg
        viewBox="0 0 900 300"
        className={styles.heroSvg}
        role="img"
        aria-label="declare, project, gate, run: the gate refuses a blind role before the model"
      >
        <defs>
          <marker
            id={MARKER}
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 9 5 L 0 9 z" fill="context-stroke" />
          </marker>
        </defs>

        {/* arrows between nodes */}
        <line
          x1={NODES[0].x + NODE_W}
          y1={AXIS_Y}
          x2={NODES[1].x}
          y2={AXIS_Y}
          className={`${styles.heroArrow} ${index >= 1 ? styles.heroArrowActive : ''}`}
          markerEnd={`url(#${MARKER})`}
        />
        <line
          x1={NODES[1].x + NODE_W}
          y1={AXIS_Y}
          x2={NODES[2].x}
          y2={AXIS_Y}
          className={`${styles.heroArrow} ${index >= 2 ? styles.heroArrowActive : ''}`}
          markerEnd={`url(#${MARKER})`}
        />
        {/* gate → run stays neutral: the refusal is the fault branch */}
        <line
          x1={NODES[2].x + NODE_W}
          y1={AXIS_Y}
          x2={NODES[3].x}
          y2={AXIS_Y}
          className={`${styles.heroArrow} ${showRunArrow ? styles.heroArrowActive : ''}`}
          markerEnd={`url(#${MARKER})`}
        />

        {/* gate: refusal branch that breaks before the model */}
        {showError ? (
          <g>
            <path
              d={`M ${NODES[2].x + NODE_W / 2} ${AXIS_Y + NODE_H / 2} L ${NODES[2].x + NODE_W / 2} 176`}
              className={styles.heroErrorPath}
            />
            <line
              x1={NODES[2].x + NODE_W / 2 - 9}
              y1={178}
              x2={NODES[2].x + NODE_W / 2 + 9}
              y2={178}
              className={styles.heroErrorStop}
            />
            <rect
              x={NODES[2].x + NODE_W / 2 - 88}
              y={190}
              width={176}
              height={34}
              rx={17}
              className={styles.heroErrorPill}
            />
            <text x={NODES[2].x + NODE_W / 2} y={212} className={styles.heroErrorText}>
              ProjectionError ✕
            </text>
          </g>
        ) : null}

        {/* model icon: to the right of the gate, physically behind the run arrow */}
        <g className={styles.heroModelGroup}>
          <circle cx={678} cy={128} r={17} className={styles.heroModelRing} />
          <path
            d="M 678 121 l 4.2 2.4 v 4.8 l -4.2 2.4 l -4.2 -2.4 v -4.8 z"
            className={styles.heroModelGlyph}
          />
          <text x={678} y={162} className={styles.heroModelLabel}>
            model
          </text>
        </g>

        {/* nodes */}
        {NODES.map((node, i) => {
          const state = nodeState(i);
          return (
            <g key={node.label} className={state === 'future' ? styles.heroNodeDim : undefined}>
              <rect
                x={node.x}
                y={AXIS_Y - NODE_H / 2}
                width={NODE_W}
                height={NODE_H}
                rx={12}
                className={`${styles.heroNode} ${state === 'active' ? styles.heroNodeActive : ''}`}
              />
              <text x={node.x + NODE_W / 2} y={AXIS_Y - 8} className={styles.heroNodeLabel}>
                {node.label}
              </text>
              <text x={node.x + NODE_W / 2} y={AXIS_Y + 12} className={styles.heroNodeSub}>
                {node.sub}
              </text>
            </g>
          );
        })}
      </svg>
      <p className={frameStyles.currentStep}>{step?.body}</p>
    </DiagramFrame>
  );
}
