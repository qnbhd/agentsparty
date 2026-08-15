'use client';

import { useEffect, useState } from 'react';
import styles from './fixed-review-protocol.module.css';

const PORTS = { R: 110, W: 360, V: 610 } as const;
const COLORS = {
  R: 'var(--role-researcher)',
  W: 'var(--role-writer)',
  V: 'var(--role-reviewer)',
} as const;
const DURATION = 9600;

const STEPS = [
  { from: 'R', to: 'W', label: 'Findings', type: 'Text', y: 110 },
  { from: 'W', to: 'V', label: 'Draft', type: 'Text', y: 160 },
  { from: 'V', to: 'W', label: 'Feedback', type: 'Text', y: 210 },
  { from: 'W', to: 'V', label: 'Revision', type: 'Text', y: 260 },
  { from: 'V', to: 'W', label: 'Approval', type: 'Nothing', y: 310 },
] as const;

const STARTS = [0.04, 0.2, 0.36, 0.52, 0.68];
const STEP_SPAN = 0.11;

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function ease(value: number): number {
  return value < 0.5 ? 2 * value * value : -1 + (4 - 2 * value) * value;
}

function prefersReducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

function Message({
  step,
  index,
  progress,
}: {
  step: (typeof STEPS)[number];
  index: number;
  progress: number;
}) {
  const x1 = PORTS[step.from];
  const x2 = PORTS[step.to];
  const minX = Math.min(x1, x2);
  const distance = Math.abs(x2 - x1);
  const direction = x2 > x1 ? 1 : -1;
  const phase = clamp01((progress - STARTS[index]) / STEP_SPAN);
  const position = ease(phase);
  const width = position * distance;
  const clipX = direction === 1 ? minX : Math.max(x1, x2) - width;
  const visible = progress >= STARTS[index];
  const color = COLORS[step.from];
  const marker = step.from === 'R' ? 'pdsArrowRust' : step.from === 'W' ? 'pdsArrowTeal' : 'pdsArrowBrass';

  return (
    <>
      <clipPath id={`pdsClip${index}`}>
        <rect x={clipX} y={step.y - 12} width={Math.max(0, width)} height="24" />
      </clipPath>
      <g clipPath={`url(#pdsClip${index})`}>
        <line x1={x1} x2={x2} y1={step.y} y2={step.y} stroke={color} strokeWidth="2" strokeDasharray={step.type === 'Nothing' ? '5 5' : undefined} markerEnd={`url(#${marker})`} />
      </g>
      <circle className={styles.pulse} cx={x1 + direction * position * distance} cy={step.y} r="4.5" fill={color} style={{ opacity: phase > 0 && phase < 1 ? 1 : 0, color }} />
      <text className={styles.messageLabel} x={(x1 + x2) / 2} y={step.y - 9} textAnchor="middle" fill={color} style={{ opacity: visible ? 1 : 0 }}>{step.label}</text>
      <text className={styles.messageType} x={(x1 + x2) / 2} y={step.y + 15} textAnchor="middle" style={{ opacity: visible ? 0.9 : 0 }}>{step.type} →</text>
    </>
  );
}

function ProtocolSvg({ progress }: { progress: number }) {
  const activeIndex = STEPS.reduce((active, _, index) => (
    progress >= STARTS[index] && progress < STARTS[index] + STEP_SPAN + 0.03 ? index : active
  ), -1);
  const activeRoles = activeIndex < 0 ? [] : [STEPS[activeIndex].from, STEPS[activeIndex].to];

  return (
    <svg className={styles.svg} aria-label="Animated sequence diagram of the review protocol" viewBox="0 0 720 380" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="pdsArrowRust" markerHeight="8" markerWidth="8" orient="auto" refX="6" refY="3"><path d="M0,0 L6,3 L0,6 Z" fill="#b85c39" /></marker>
        <marker id="pdsArrowTeal" markerHeight="8" markerWidth="8" orient="auto" refX="6" refY="3"><path d="M0,0 L6,3 L0,6 Z" fill="#2f6f6a" /></marker>
        <marker id="pdsArrowBrass" markerHeight="8" markerWidth="8" orient="auto" refX="6" refY="3"><path d="M0,0 L6,3 L0,6 Z" fill="#a67c27" /></marker>
      </defs>
      <line className={styles.rail} x1="110" x2="110" y1="70" y2="330" />
      <line className={styles.rail} x1="360" x2="360" y1="70" y2="330" />
      <line className={styles.rail} x1="610" x2="610" y1="70" y2="330" />
      {[110, 360, 610].map((x) => Array.from({ length: 21 }, (_, index) => (
        <line key={`${x}-${index}`} className={styles.tick} x1={x - 3} x2={x + 3} y1={78 + index * 12} y2={78 + index * 12} />
      )))}
      {(['R', 'W', 'V'] as const).map((role) => (
        <g key={role} className={styles.port} transform={`translate(${PORTS[role]},40)`}>
          <rect height="32" rx="8" stroke={COLORS[role]} width="48" x="-24" y="-16" style={{ strokeWidth: activeRoles.includes(role) ? 3 : 1.6 }} />
          <text fill={COLORS[role]} textAnchor="middle" x="0" y="5">{role}</text>
          <text className={styles.role} textAnchor="middle" x="0" y="-24">{role === 'R' ? 'Researcher' : role === 'W' ? 'Writer' : 'Reviewer'}</text>
        </g>
      ))}
      {STEPS.map((step, index) => <Message key={step.label} step={step} index={index} progress={progress} />)}
    </svg>
  );
}

export function FixedReviewProtocol() {
  const [progress, setProgress] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    setReduced(prefersReducedMotion());
  }, []);

  useEffect(() => {
    if (reduced) {
      setProgress(0.99);
      return undefined;
    }
    if (paused) return undefined;
    let startTime: number | undefined;
    let frame = 0;
    const animate = (now: number) => {
      startTime ??= now;
      setProgress(((now - startTime) % DURATION) / DURATION);
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [paused, reduced]);

  const toggle = () => setPaused((value) => !value);
  const assertionOpacity = progress < 0.86 ? 0 : progress < 0.985 ? clamp01((progress - 0.86) / 0.05) : 1 - clamp01((progress - 0.985) / 0.015);

  return (
    <div className={styles.root}>
      <div className={styles.card}>
        <div className={styles.head}>
          <div>
            <div className={styles.eyebrow}>agentsparty · protocol</div>
            <div className={styles.title}>A fixed review protocol</div>
            <div className={styles.sub}>One shared value carries the whole exchange — five hops, one contract per port.</div>
          </div>
          <button type="button" aria-pressed={paused} className={styles.button} onClick={toggle} title={`${paused ? 'Play' : 'Pause'} animation`}>
            <svg fill="currentColor" viewBox="0 0 12 12"><path d={paused ? 'M2 1h3v10H2zM7 1h3v10H7z' : 'M2 1l9 5-9 5V1z'} /></svg>
            <span>{paused ? 'Play' : 'Pause'}</span>
          </button>
        </div>
        <div className={styles.ruler}><span className={styles.mono}>seq</span><div className={styles.rulerTrack}><div className={styles.rulerLine} />{Array.from({ length: 9 }, (_, index) => <div key={index} className={styles.rulerTick} style={{ left: `${(index + 1) * 10}%` }} />)}<div className={styles.rulerMarker} style={{ left: `${progress * 100}%` }} /></div><span className={styles.mono}>.close()</span></div>
        <ProtocolSvg progress={progress} />
        <div className={styles.assertion} style={{ opacity: assertionOpacity, transform: `translateY(${4 - 4 * assertionOpacity}px)` }}><span className={styles.mono}>assert</span> roles == <b>[Researcher, Writer, Reviewer]</b></div>
        <div className={styles.legend}><span><i className={styles.researcher} /> Researcher →</span><span><i className={styles.writer} /> Writer →</span><span><i className={styles.reviewer} /> Reviewer →</span><span><i className={styles.dashed} /> Nothing payload</span></div>
      </div>
    </div>
  );
}
