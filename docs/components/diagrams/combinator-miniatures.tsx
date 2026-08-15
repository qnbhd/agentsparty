import styles from './combinator-miniatures.module.css';

type MiniatureProps = {
  readonly label: string;
  readonly description: string;
  readonly children: React.ReactNode;
};

function Miniature({ label, description, children }: MiniatureProps) {
  return (
    <figure className={styles.figure}>
      <svg className={styles.svg} viewBox="0 0 576 104" role="img" aria-labelledby={`${label}-mini-title`}>
        <title id={`${label}-mini-title`}>{description}</title>
        <text className={styles.renderLabel} x="18" y="18">render()</text>
        <text className={styles.treeLabel} x="294" y="18">tree</text>
        <path className={styles.divider} d="M 268 13 V 91" />
        <path className={styles.edge} d="M 193 55 H 255" />
        <circle className={styles.signal} cx="193" cy="55" r="2.5" />
        {children}
      </svg>
      <figcaption className={styles.caption}>{description}</figcaption>
    </figure>
  );
}

export function MsgMiniature() {
  return (
    <Miniature label="msg" description="The rendered message becomes a msg tree node with sender, receiver, and payload leaves.">
      <text className={styles.renderText} x="18" y="59">A → B : Note(str)</text>
      <g className={styles.tree}>
        <path className={styles.edge} d="M 346 52 L 386 34 M 346 52 H 386 M 346 52 L 386 70" />
        <rect className={styles.node} x="294" y="41" width="52" height="22" rx="11" />
        <text className={styles.nodeText} x="320" y="56" textAnchor="middle">msg</text>
        <rect className={styles.leaf} x="386" y="24" width="38" height="18" rx="9" />
        <text className={styles.leafText} x="405" y="36" textAnchor="middle">A</text>
        <rect className={styles.leaf} x="386" y="43" width="38" height="18" rx="9" />
        <text className={styles.leafText} x="405" y="55" textAnchor="middle">B</text>
        <rect className={styles.leaf} x="386" y="62" width="66" height="18" rx="9" />
        <text className={styles.leafText} x="419" y="74" textAnchor="middle">Note(str)</text>
      </g>
    </Miniature>
  );
}

export function SequenceMiniature() {
  return (
    <Miniature label="sequence" description="Two rendered lines become the ordered children of a sequence node.">
      <text className={styles.renderText} x="18" y="48">A → B : First(str)</text>
      <text className={styles.renderText} x="18" y="67">B → A : Second(str)</text>
      <g className={styles.tree}>
        <path className={styles.edge} d="M 344 52 L 390 36 M 344 52 L 390 68" />
        <rect className={styles.node} x="294" y="41" width="50" height="22" rx="6" />
        <text className={styles.nodeText} x="319" y="56" textAnchor="middle">seq</text>
        <rect className={styles.leaf} x="390" y="25" width="82" height="22" rx="11" />
        <text className={styles.leafText} x="431" y="39" textAnchor="middle">msg First</text>
        <rect className={styles.leaf} x="390" y="57" width="82" height="22" rx="11" />
        <text className={styles.leafText} x="431" y="71" textAnchor="middle">msg Second</text>
      </g>
    </Miniature>
  );
}

export function AltMiniature() {
  return (
    <Miniature label="alt" description="The rendered choice becomes an alt node with one child for each labelled case.">
      <text className={styles.renderText} x="18" y="48">A → B {'{'}</text>
      <text className={styles.renderText} x="34" y="67">Yes() | No()</text>
      <g className={styles.tree}>
        <path className={styles.edge} d="M 344 52 L 390 36 M 344 52 L 390 68" />
        <path className={styles.node} d="M 319 38 L 344 52 L 319 66 L 294 52 Z" />
        <text className={styles.nodeText} x="319" y="56" textAnchor="middle">alt</text>
        <rect className={styles.leaf} x="390" y="25" width="62" height="22" rx="11" />
        <text className={styles.leafText} x="421" y="39" textAnchor="middle">Yes()</text>
        <rect className={styles.leaf} x="390" y="57" width="62" height="22" rx="11" />
        <text className={styles.leafText} x="421" y="71" textAnchor="middle">No()</text>
      </g>
    </Miniature>
  );
}

export function RecMiniature() {
  return (
    <Miniature label="rec-var" description="The recursion binder contains a guarded message and a var leaf that refers back to the binder.">
      <text className={styles.renderText} x="18" y="40">rec X</text>
      <text className={styles.renderText} x="34" y="58">A → B : Tick(str)</text>
      <text className={styles.renderText} x="34" y="76">X</text>
      <g className={styles.tree}>
        <path className={styles.edge} d="M 350 52 H 382 L 408 36 M 382 52 L 408 68" />
        <rect className={styles.node} x="294" y="41" width="56" height="22" rx="6" />
        <text className={styles.nodeText} x="322" y="56" textAnchor="middle">rec X</text>
        <rect className={styles.leaf} x="408" y="25" width="72" height="22" rx="11" />
        <text className={styles.leafText} x="444" y="39" textAnchor="middle">msg Tick</text>
        <rect className={styles.leaf} x="408" y="57" width="52" height="22" rx="11" />
        <text className={styles.leafText} x="434" y="71" textAnchor="middle">var X</text>
        <path className={styles.feedback} d="M 460 68 C 510 68 510 24 350 43" />
      </g>
    </Miniature>
  );
}

export function ParMiniature() {
  return (
    <Miniature label="par" description="The rendered parallel block becomes a par node with two independent track children.">
      <text className={styles.renderText} x="18" y="39">par {'{'}</text>
      <text className={styles.renderText} x="34" y="57">| A → B : L(str)</text>
      <text className={styles.renderText} x="34" y="75">| C → D : R(str)</text>
      <g className={styles.tree}>
        <path className={styles.edge} d="M 344 52 L 390 36 M 344 52 L 390 68" />
        <rect className={styles.node} x="294" y="41" width="50" height="22" rx="6" />
        <text className={styles.nodeText} x="319" y="56" textAnchor="middle">par</text>
        <rect className={styles.leaf} x="390" y="25" width="82" height="22" rx="11" />
        <text className={styles.leafText} x="431" y="39" textAnchor="middle">msg L</text>
        <rect className={styles.leaf} x="390" y="57" width="82" height="22" rx="11" />
        <text className={styles.leafText} x="431" y="71" textAnchor="middle">msg R</text>
      </g>
    </Miniature>
  );
}
