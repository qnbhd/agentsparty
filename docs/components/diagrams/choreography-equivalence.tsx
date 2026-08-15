import styles from './choreography-equivalence.module.css';

const description = '@choreography and combinators produce the same session tree; equal_session returns True.';

export function ChoreographyEquivalence() {
  return (
    <figure className={styles.figure}>
      <svg className={styles.svg} viewBox="0 0 576 132" role="img" aria-labelledby="choreography-equivalence-title">
        <title id="choreography-equivalence-title">{description}</title>
        <defs>
          <marker id="equivalence-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 1 L 9 5 L 0 9 z" fill="context-stroke" />
          </marker>
        </defs>

        <rect className={styles.facade} x="18" y="42" width="144" height="30" rx="15" />
        <text className={styles.facadeText} x="90" y="61">@choreography</text>
        <rect className={`${styles.facade} ${styles.facadeRight}`} x="414" y="42" width="144" height="30" rx="15" />
        <text className={styles.facadeText} x="486" y="61">combinators</text>

        <path className={styles.arrow} d="M 162 57 H 238" markerEnd="url(#equivalence-arrow)" />
        <path className={styles.arrow} d="M 414 57 H 338" markerEnd="url(#equivalence-arrow)" />

        <g className={styles.tree}>
          <path className={styles.treeEdge} d="M 288 75 L 264 91 M 288 75 L 312 91" />
          <path className={styles.treeNode} d="M 288 38 L 338 57 L 288 76 L 238 57 Z" />
          <text className={styles.treeText} x="288" y="60">session</text>
          <rect className={styles.treeLeaf} x="239" y="89" width="50" height="18" rx="9" />
          <text className={styles.leafText} x="264" y="101">msg</text>
          <rect className={styles.treeLeaf} x="292" y="89" width="40" height="18" rx="9" />
          <text className={styles.leafText} x="312" y="101">end</text>
        </g>

        <text className={styles.equalText} x="288" y="123">equal_session == True</text>
      </svg>
      <figcaption className={styles.caption}>{description}</figcaption>
    </figure>
  );
}
