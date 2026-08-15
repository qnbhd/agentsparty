'use client';

import { useState } from 'react';
import styles from './knowledge-miniatures.module.css';

type Branch = {
  readonly label: string;
  readonly from: string;
  readonly to: string;
  readonly payload: string;
};

type Scene = {
  readonly id: string;
  readonly title: string;
  readonly chooser: string;
  readonly informed: string;
  readonly blind: string;
  readonly branches: readonly [Branch, Branch];
  readonly merges: boolean;
  readonly verdict: string;
};

/** What the blind role has to do inside one branch. Its message always touches that role. */
function duty(branch: Branch, blind: string) {
  if (branch.to === blind) {
    return { dir: 'recv' as const, peer: branch.from, glyph: '?', verb: 'receives' };
  }
  return { dir: 'send' as const, peer: branch.to, glyph: '!', verb: 'sends' };
}

const blindScene: Scene = {
  id: 'blind',
  title: 'no branch signal',
  chooser: 'A',
  informed: 'B',
  blind: 'C',
  branches: [
    { label: 'Yes', from: 'A', to: 'C', payload: 'Y' },
    { label: 'No', from: 'C', to: 'A', payload: 'N' },
  ],
  merges: false,
  verdict: 'C cannot merge ? with ! — projection refuses',
};

const repairedScene: Scene = {
  id: 'repaired',
  title: 'each branch talks to the blind role',
  chooser: 'Reviewer',
  informed: 'Writer',
  blind: 'Reader',
  branches: [
    { label: 'Approve', from: 'Writer', to: 'Reader', payload: 'Final' },
    { label: 'Reject', from: 'Writer', to: 'Reader', payload: 'Rejected' },
  ],
  merges: true,
  verdict: 'Reader merges into one endpoint: Writer ? { Final | Rejected }',
};

type ColumnProps = {
  readonly branch: Branch;
  readonly blind: string;
  readonly side: -1 | 1;
  readonly active: boolean;
};

/** One branch, read top to bottom: the labelled edge, its message, the duty it leaves. */
function BranchColumn({ branch, blind, side, active }: ColumnProps) {
  const cx = 288 + side * 138;
  const { dir, peer, glyph, verb } = duty(branch, blind);
  const edge = `M ${288 + side * 26} 62 C ${288 + side * 70} 76, ${cx - side * 30} 74, ${cx} 84`;
  return (
    <g className={`${styles.column} ${active ? styles.columnActive : ''}`}>
      <path className={styles.edge} d={edge} markerEnd="url(#knowledge-arrow)" />
      <path className={styles.travel} pathLength="100" d={edge} />
      <text className={styles.branchLabel} x={288 + side * 84} y="70">{branch.label}</text>

      <rect className={styles.chip} x={cx - 102} y="84" width="204" height="30" rx="8" />
      <text className={styles.chipText} x={cx} y="103">
        {branch.from} → {branch.to} : {branch.payload}
      </text>

      <path className={styles.link} d={`M ${cx} 114 V 136`} />

      <rect
        className={`${styles.duty} ${dir === 'recv' ? styles.dutyRecv : styles.dutySend}`}
        x={cx - 102}
        y="138"
        width="204"
        height="42"
        rx="10"
      />
      <text
        className={`${styles.dutyGlyph} ${dir === 'recv' ? styles.glyphRecv : styles.glyphSend}`}
        x={cx - 84}
        y="165"
      >
        {glyph}
      </text>
      <text className={styles.dutySignature} x={cx + 8} y="159">
        {peer} {glyph} {branch.payload}
      </text>
      <text className={styles.dutyCaption} x={cx + 8} y="173">
        {blind} {verb} {branch.payload}
      </text>
    </g>
  );
}

const widgetDescription =
  'Switching branches shows what the uninformed role must do: on one branch it receives, on the other it sends. The two endpoints only merge once every branch carries a message to that role.';

export function BlindChoiceWidget() {
  const [repaired, setRepaired] = useState(false);
  const [active, setActive] = useState(0);
  const scene = repaired ? repairedScene : blindScene;

  return (
    <figure className={styles.figure}>
      <svg className={styles.svg} viewBox="0 0 576 208" role="img" aria-labelledby="knowledge-widget-title">
        <title id="knowledge-widget-title">{widgetDescription}</title>
        <defs>
          <marker id="knowledge-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="context-stroke" />
          </marker>
        </defs>

        <text className={styles.sectionLabel} x="18" y="16">{scene.title}</text>

        <path className={styles.alt} d="M 288 20 L 372 46 L 288 72 L 204 46 z" />
        <text className={styles.altText} x="288" y="42">alt</text>
        <text className={styles.altSub} x="288" y="58">{scene.chooser} → {scene.informed}</text>

        <g key={`${scene.id}-${active}`} className={styles.duties}>
          <BranchColumn branch={scene.branches[0]} blind={scene.blind} side={-1} active={active === 0} />
          <BranchColumn branch={scene.branches[1]} blind={scene.blind} side={1} active={active === 1} />
        </g>

        <text className={styles.sectionLabel} x="288" y="132" textAnchor="middle">endpoint of {scene.blind}</text>
        <path className={styles.link} d="M 252 159 H 266" />
        <path className={styles.link} d="M 310 159 H 324" />
        <circle
          key={scene.id}
          className={`${styles.mergeCircle} ${scene.merges ? styles.mergeOk : styles.mergeFail}`}
          cx="288"
          cy="159"
          r="18"
        />
        <text
          className={`${styles.mergeGlyph} ${scene.merges ? styles.glyphOk : styles.glyphFail}`}
          x="288"
          y="165"
        >
          {scene.merges ? '✓' : '✗'}
        </text>

        <text
          key={`${scene.id}-verdict`}
          className={`${styles.verdict} ${scene.merges ? styles.verdictOk : styles.verdictFail}`}
          x="288"
          y="199"
        >
          {scene.verdict}
        </text>
      </svg>

      <div className={styles.controls}>
        <div className={styles.segmented} role="group" aria-label="branch">
          {scene.branches.map((branch, index) => (
            <button
              key={branch.label}
              type="button"
              aria-pressed={active === index}
              onClick={() => setActive(index)}
            >
              {branch.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          className={styles.toggle}
          aria-pressed={repaired}
          onClick={() => setRepaired((value) => !value)}
        >
          {repaired ? 'branch signal: added' : 'branch signal: missing'}
        </button>
      </div>

      <figcaption className={styles.caption}>{widgetDescription}</figcaption>
    </figure>
  );
}

type Mark = 'role' | 'alt' | 'send' | 'recv';
type Segment = { readonly text: string; readonly mark?: Mark };
type Placed = { readonly text: string; readonly mark?: Mark; readonly x: number; readonly y: number; readonly width: number };

/** Advance width of one character in the 9px monospace face used by the error text. */
const CHAR = 5.42;

function placeLine(segments: readonly Segment[], x: number, y: number): readonly Placed[] {
  return segments.reduce<Placed[]>((placed, segment) => {
    const last = placed.at(-1);
    const left = last ? last.x + last.width : x;
    return [...placed, { ...segment, x: left, y, width: segment.text.length * CHAR }];
  }, []);
}

const errorLines: readonly (readonly Segment[])[] = [
  [{ text: "ProjectionError: role " }, { text: "'C'", mark: 'role' }, { text: ' cannot' }],
  [{ text: 'tell the branches of the ' }, { text: 'alt A -> B', mark: 'alt' }, { text: ' apart:' }],
  [{ text: "  on 'No' it " }, { text: 'must send N to A', mark: 'send' }, { text: ' (as C),' }],
  [{ text: "  on 'Yes' it " }, { text: 'must receive Y from A', mark: 'recv' }, { text: ' (as C).' }],
];

const markText: Record<Mark, string> = {
  role: styles.textRole,
  alt: styles.textAlt,
  send: styles.textSend,
  recv: styles.textRecv,
};
const markBox: Record<Mark, string> = {
  role: styles.markRole,
  alt: styles.markAlt,
  send: styles.markSend,
  recv: styles.markRecv,
};
const markPointer: Record<Mark, string> = {
  role: styles.pointerRole,
  alt: styles.pointerAlt,
  send: styles.pointerSend,
  recv: styles.pointerRecv,
};

/** Pointers leave from the gutter, never from inside the line: a curve crossing its own
 *  sentence would read as a strike-through. Only the line's baseline is used. */
const pointerPaths: Record<Mark, (from: Placed) => string> = {
  role: (from) => `M 286 ${from.y - 3} C 278 ${from.y + 24}, 282 126, 250 148 L 186 150`,
  alt: (from) => `M 286 ${from.y - 3} C 250 ${from.y - 3}, 220 42, 196 42`,
  send: (from) => `M 286 ${from.y - 3} C 268 ${from.y - 3}, 258 100, 246 100`,
  recv: (from) => `M 286 ${from.y - 3} C 250 ${from.y + 14}, 180 134, 76 118`,
};

const mapDescription =
  'Each phrase of the ProjectionError points at the part of the tree it names: the blind role, the alt it cannot tell apart, and the two duties whose directions disagree.';

export function ProjectionErrorMap() {
  const lines = errorLines.map((segments, index) => placeLine(segments, 296, 40 + index * (index < 2 ? 15 : 20)));
  const marked = lines.flat().filter((segment): segment is Placed & { mark: Mark } => Boolean(segment.mark));

  return (
    <figure className={styles.figure}>
      <svg className={styles.svg} viewBox="0 0 576 196" role="img" aria-labelledby="knowledge-map-title">
        <title id="knowledge-map-title">{mapDescription}</title>
        <defs>
          <marker id="map-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="context-stroke" />
          </marker>
        </defs>

        <text className={styles.sectionLabel} x="18" y="16">protocol</text>
        <text className={styles.sectionLabel} x="296" y="16">ProjectionError</text>

        <path className={styles.alt} d="M 132 22 L 190 42 L 132 62 L 74 42 z" />
        <text className={styles.altText} x="132" y="40">alt</text>
        <text className={styles.altSub} x="132" y="53">A → B</text>

        <path className={styles.edge} d="M 116 56 L 90 82" markerEnd="url(#map-arrow)" />
        <path className={styles.edge} d="M 148 56 L 174 82" markerEnd="url(#map-arrow)" />
        <text className={styles.branchLabel} x="82" y="72">Yes</text>
        <text className={styles.branchLabel} x="182" y="72">No</text>

        <rect className={`${styles.chip} ${styles.targetRecv}`} x="24" y="86" width="100" height="28" rx="8" />
        <text className={styles.chipText} x="74" y="104">A → C : Y</text>
        <rect className={`${styles.chip} ${styles.targetSend}`} x="140" y="86" width="100" height="28" rx="8" />
        <text className={styles.chipText} x="190" y="104">C → A : N</text>

        <rect className={`${styles.blindChip} ${styles.targetRole}`} x="92" y="138" width="88" height="24" rx="12" />
        <text className={styles.chipText} x="136" y="155">role C</text>
        <text className={styles.note} x="136" y="176">no branch reaches it</text>

        {lines.map((line) =>
          line.map((segment) => (
            <text
              key={`${segment.y}-${segment.x}`}
              className={`${styles.errorText} ${segment.mark ? markText[segment.mark] : ''}`}
              x={segment.x}
              y={segment.y}
              xmlSpace="preserve"
            >
              {segment.text}
            </text>
          )),
        )}

        {marked.map((segment) => (
          <rect
            key={`box-${segment.mark}`}
            className={`${styles.markBox} ${markBox[segment.mark]}`}
            x={segment.x - 2}
            y={segment.y - 9}
            width={segment.width + 4}
            height="13"
            rx="3"
          />
        ))}

        {marked.map((segment) => (
          <path
            key={`pointer-${segment.mark}`}
            className={`${styles.pointer} ${markPointer[segment.mark]}`}
            pathLength="100"
            d={pointerPaths[segment.mark](segment)}
            markerEnd="url(#map-arrow)"
          />
        ))}
      </svg>
      <figcaption className={styles.caption}>{mapDescription}</figcaption>
    </figure>
  );
}
