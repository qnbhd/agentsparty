import { DiagramFrame } from './diagram-frame';
import frameStyles from './diagram.module.css';
import styles from './home.module.css';
import type { SequenceDataset } from './types';

export type LifelineSequenceProps = {
  dataset: SequenceDataset;
  title: string;
  caption: string;
  description: string;
};

const MARKER = 'lifeline-arrow-three-role-global-sequence';
const HEADER_H = 34;
const LIFELINE_TOP = 70;
const LIFELINE_BOTTOM = 350;

/** x position of each role's lifeline, in declaration order. */
function roleX(dataset: SequenceDataset, index: number): number {
  // Writer, Reviewer, Tools -> 160 / 420 / 680
  return 160 + index * 260;
}

function Label({ label, payload }: { label: string; payload?: string }) {
  return (
    <>
      <tspan className={styles.msgLabel}>{label}</tspan>
      {payload ? <tspan className={styles.msgPayload}>{payload}</tspan> : null}
    </>
  );
}

export function LifelineSequence({ dataset, title, caption, description }: LifelineSequenceProps) {
  const xs = dataset.roles.map((_, i) => roleX(dataset, i));
  const writerX = xs[0];
  const reviewerX = xs[1];
  const toolsX = xs[2];
  const draftY = 110;
  const frameY = 140;
  const frameH = 190;
  const approveY = 190;
  const diamondY = 235;
  const reviseY = 290;

  return (
    <DiagramFrame
      id={dataset.id}
      title={title}
      caption={caption}
      description={description}
      fallback={
        <pre className={frameStyles.renderText}>{dataset.renderText}</pre>
      }
    >
      <svg
        viewBox="0 0 780 390"
        className={styles.lifelineSvg}
        role="img"
        aria-label="Writer sends Draft to Reviewer; Reviewer chooses Approve to Tools or Revise back to Writer"
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

        {/* alt frame fill sits behind the lifelines so they stay visible */}
        <rect
          x={writerX - 20}
          y={frameY}
          width={toolsX - writerX + 40}
          height={frameH}
          rx={12}
          className={styles.altFrameFill}
        />

        {/* lifelines */}
        {xs.map((x) => (
          <line key={x} x1={x} y1={LIFELINE_TOP} x2={x} y2={LIFELINE_BOTTOM} className={styles.lifeline} />
        ))}

        {/* role headers */}
        {xs.map((x, i) => (
          <g key={x}>
            <rect x={x - 55} y={LIFELINE_TOP - HEADER_H - 10} width={110} height={HEADER_H} rx={8} className={styles.roleHeader} />
            <text x={x} y={LIFELINE_TOP - HEADER_H / 2 - 2} className={styles.roleHeaderText}>
              {dataset.roles[i]}
            </text>
          </g>
        ))}

        {/* Draft(text): control label in protocol colour, payload in grey */}
        <line
          x1={writerX}
          y1={draftY}
          x2={reviewerX}
          y2={draftY}
          className={styles.msgArrow}
          markerEnd={`url(#${MARKER})`}
        />
        <text x={(writerX + reviewerX) / 2} y={draftY - 9} textAnchor="middle">
          <Label label="Draft" payload="(str)" />
        </text>

        {/* decision diamond on the Reviewer lifeline */}
        <polygon
          points={`${reviewerX},${diamondY - 12} ${reviewerX + 12},${diamondY} ${reviewerX},${diamondY + 12} ${reviewerX - 12},${diamondY}`}
          className={styles.altDiamond}
        />

        {/* Approve branch: Reviewer -> Tools : Publish(text) */}
        <line
          x1={reviewerX}
          y1={approveY}
          x2={toolsX}
          y2={approveY}
          className={styles.msgArrow}
          markerEnd={`url(#${MARKER})`}
        />
        <text x={(reviewerX + toolsX) / 2} y={approveY - 9} textAnchor="middle">
          <Label label="Publish" payload="(str)" />
        </text>

        {/* Revise branch: back arrow on the left of the lifelines, no loop */}
        <path
          d={`M ${reviewerX} ${reviseY} H 70 V ${draftY + 15} H ${writerX}`}
          className={styles.msgBack}
          markerEnd={`url(#${MARKER})`}
        />
        <text x={reviewerX - 25} y={reviseY - 8} textAnchor="end" className={styles.msgBackLabel}>
          Revise
        </text>

        {/* alt frame border on top, so the dashed edge stays crisp */}
        <rect
          x={writerX - 20}
          y={frameY}
          width={toolsX - writerX + 40}
          height={frameH}
          rx={12}
          className={styles.altFrame}
        />

        {/* alt label as a chip on the top border, so no line shows through */}
        <g>
          <rect
            x={writerX - 20}
            y={frameY - 12}
            width={68}
            height={24}
            rx={12}
            className={styles.altFrameLabelBg}
          />
          <text
            x={writerX - 20 + 34}
            y={frameY + 5}
            className={styles.altFrameLabel}
          >
            alt
          </text>
        </g>
      </svg>
      <p className={styles.lifelineLegend}>
        <span>
          <span className={styles.lifelineLegendProtocol}>Draft</span>{' '}
          <span className={styles.lifelineLegendPayload}>(str)</span>
        </span>
        <span>color selects the protocol · grey fills the model</span>
      </p>
    </DiagramFrame>
  );
}
