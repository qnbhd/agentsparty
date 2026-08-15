import styles from './composition-miniatures.module.css';

type MiniatureProps = {
  readonly id: string;
  readonly description: string;
  readonly viewBox: string;
  readonly children: React.ReactNode;
};

function Miniature({ id, description, viewBox, children }: MiniatureProps) {
  return (
    <figure className={styles.figure}>
      <svg className={styles.svg} viewBox={viewBox} role="img" aria-labelledby={`${id}-title`}>
        <title id={`${id}-title`}>{description}</title>
        <defs>
          <marker
            id={`${id}-arrow`}
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M 0 1 L 9 5 L 0 9 z" fill="context-stroke" />
          </marker>
        </defs>
        {children}
      </svg>
      <figcaption className={styles.caption}>{description}</figcaption>
    </figure>
  );
}

const composeDescription =
  'The contract sequence sits above two disjoint ownership zones: owning(Analyst) and owning(Photo). Brand is owned by no component, so the contract serves it.';

/** Disjoint ownership as space: no role chip may sit inside two zones. */
export function ComposeOwnershipMiniature() {
  return (
    <Miniature id="compose-ownership" description={composeDescription} viewBox="0 0 576 152">
      <text className={styles.sectionLabel} x="18" y="16">contract</text>

      <g>
        <rect className={styles.contractStep} x="32" y="26" width="152" height="24" rx="12" />
        <rect className={styles.contractStep} x="196" y="26" width="152" height="24" rx="12" />
        <rect className={styles.contractStep} x="360" y="26" width="152" height="24" rx="12" />
      </g>
      <text className={styles.stepText} x="108" y="42">Brand → Analyst : Product</text>
      <text className={styles.stepText} x="272" y="42">Analyst → Photo : Copy</text>
      <text className={styles.stepText} x="436" y="42">Photo → Brand : Post</text>
      <path className={styles.edge} d="M 184 38 H 190" markerEnd="url(#compose-ownership-arrow)" />
      <path className={styles.edge} d="M 348 38 H 354" markerEnd="url(#compose-ownership-arrow)" />
      <path className={styles.rail} d="M 32 58 H 512" />
      <circle className={styles.signal} cx="34" cy="58" r="2.5" />

      <text className={styles.sectionLabel} x="18" y="76">ownership</text>

      <rect className={styles.frame} x="24" y="84" width="528" height="60" rx="10" />
      <rect className={`${styles.zone} ${styles.zoneA}`} x="200" y="92" width="132" height="44" rx="9" />
      <rect className={`${styles.zone} ${styles.zoneB}`} x="376" y="92" width="132" height="44" rx="9" />

      <rect className={`${styles.role} ${styles.roleUnowned}`} x="52" y="98" width="80" height="22" rx="11" />
      <text className={styles.roleText} x="92" y="113">Brand</text>
      <text className={styles.note} x="92" y="132" textAnchor="middle">unowned</text>

      <rect className={styles.role} x="224" y="98" width="84" height="22" rx="11" />
      <text className={styles.roleText} x="266" y="113">Analyst</text>
      <text className={`${styles.zoneLabel} ${styles.zoneLabelA}`} x="266" y="131">owning(Analyst)</text>

      <rect className={styles.role} x="404" y="98" width="76" height="22" rx="11" />
      <text className={styles.roleText} x="442" y="113">Photo</text>
      <text className={`${styles.zoneLabel} ${styles.zoneLabelB}`} x="442" y="131">owning(Photo)</text>
    </Miniature>
  );
}

type PanelProps = {
  readonly id: string;
  readonly dx: number;
  readonly title: string;
  readonly may: boolean;
  readonly children?: React.ReactNode;
};

/** One recursion graph: binder, guarded message, back edge. The exit branch, if any, is a child. */
function TerminationPanel({ id, dx, title, may, children }: PanelProps) {
  return (
    <g transform={`translate(${dx} 0)`}>
      <text className={styles.panelTitle} x="0" y="18">{title}</text>

      <rect className={styles.node} x="14" y="52" width="34" height="22" rx="11" />
      <text className={styles.nodeText} x="31" y="67">X</text>
      <path className={styles.edge} d="M 48 63 H 78" markerEnd={`url(#${id}-arrow)`} />
      <rect className={styles.node} x="84" y="52" width="56" height="22" rx="6" />
      <text className={styles.nodeText} x="112" y="67">Tick</text>

      {children}

      <path className={styles.loop} d="M 112 74 V 86 Q 112 94 104 94 H 39 Q 31 94 31 86 V 78" markerEnd={`url(#${id}-arrow)`} />
      <path className={styles.travel} pathLength="100" d="M 112 74 V 86 Q 112 94 104 94 H 39 Q 31 94 31 86 V 78" />

      <text className={styles.verdict} x="12" y="120">
        may_terminate <tspan className={may ? styles.yes : styles.no}>{may ? '✓' : '✗'}</tspan>
        <tspan dx="12">must_terminate </tspan>
        <tspan className={styles.no}>✗</tspan>
      </text>
    </g>
  );
}

const terminationDescription =
  'A recursion with an exit branch reaches end on some path, so may_terminate holds and must_terminate does not. A cycle with no exit satisfies neither predicate.';

export function TerminationMiniature() {
  return (
    <Miniature id="termination" description={terminationDescription} viewBox="0 0 576 132">
      <path className={styles.divider} d="M 288 14 V 122" />

      <TerminationPanel id="termination" dx={18} title="rec X with an exit branch" may>
        <path className={styles.edge} d="M 140 58 L 170 41" markerEnd="url(#termination-arrow)" />
        <path className={`${styles.travel} ${styles.travelExit}`} pathLength="100" d="M 140 58 L 170 41" />
        <rect className={styles.terminal} x="174" y="30" width="44" height="20" rx="10" />
        <text className={styles.nodeText} x="196" y="44">end</text>
      </TerminationPanel>

      <TerminationPanel id="termination" dx={356} title="rec X with no exit" may={false} />
    </Miniature>
  );
}

type GaugeProps = {
  readonly y: number;
  readonly name: string;
  readonly error: string;
  readonly rowClass?: string;
};

function Gauge({ y, name, error, rowClass = '' }: GaugeProps) {
  return (
    <g>
      <text className={styles.gaugeLabel} x="18" y={y + 4}>{name}</text>
      <rect className={styles.track} x="96" y={y - 7} width="228" height="14" rx="7" />
      <rect className={`${styles.fill} ${rowClass}`} x="96" y={y - 7} width="228" height="14" rx="7" />
      <path className={styles.limit} d={`M 328 ${y - 11} V ${y + 11}`} />
      <path className={styles.edge} d={`M 336 ${y} H 366`} markerEnd="url(#allowance-arrow)" />
      <rect className={`${styles.errorChip} ${rowClass}`} x="372" y={y - 11} width="186" height="22" rx="11" />
      <text className={`${styles.errorText} ${rowClass}`} x="465" y={y + 4}>{error}</text>
    </g>
  );
}

const allowanceDescription =
  'Three separate bounds — steps, recursion unfolds, and tokens — raise three distinct errors. Replayed journal decisions do not consume the allowance.';

export function AllowanceMiniature() {
  return (
    <Miniature id="allowance" description={allowanceDescription} viewBox="0 0 576 132">
      <text className={styles.sectionLabel} x="18" y="16">allowance</text>
      <text className={styles.note} x="558" y="16" textAnchor="end">replay reads decisions — it does not consume</text>

      <Gauge y={44} name="steps" error="StepLimitError" />
      <Gauge y={76} name="unfolds" error="RecursionLimitError" rowClass={styles.rowB} />
      <Gauge y={108} name="tokens" error="TokenLimitError" rowClass={styles.rowC} />
    </Miniature>
  );
}
