/** Serializable diagram data shapes shared by all diagram components. */

export type RoleId = string;

export type MessageStep = {
  readonly id: string;
  readonly from: RoleId;
  readonly to: RoleId;
  readonly label: string;
  /** Gray payload suffix (e.g. `(str)`) for the two-color lifeline variant. */
  readonly payload?: string;
  readonly kind?: 'message' | 'alt' | 'model' | 'tool' | 'cancel' | 'replay';
};

export type SequenceDataset = {
  readonly id: string;
  readonly kind: 'sequence';
  readonly roles: readonly RoleId[];
  readonly messages: readonly MessageStep[];
  /** `lifeline`: bespoke lifeline sequence with two-color labels. */
  readonly variant?: 'lifeline';
  /** Canonical render() output for the accessible text version. */
  readonly renderText?: string;
};

export type ProjectionColumn = {
  readonly role: RoleId;
  readonly lines: readonly string[];
  /** `linked` variant only: one entry per global line; `null` = erased. */
  readonly slots?: readonly (string | null)[];
};

export type ProjectionDataset = {
  readonly id: string;
  readonly kind: 'projection';
  readonly global: readonly string[];
  readonly endpoints: readonly ProjectionColumn[];
  /** `linked`: hover a global line to light the matching local lines. */
  readonly variant?: 'linked';
  /** Canonical render() output for the accessible text version. */
  readonly renderText?: string;
};

export type KnowledgeWorld = {
  readonly id: string;
  readonly label: string;
  readonly action: string;
  readonly message: string;
  /** Informing message added to this world in the fixed state. */
  readonly inform: string;
};

export type KnowledgeDataset = {
  readonly id: string;
  readonly kind: 'knowledge';
  readonly chooser: RoleId;
  readonly peer: RoleId;
  readonly blind: RoleId;
  readonly altLine: string;
  readonly worlds: readonly KnowledgeWorld[];
  readonly localViewBroken: readonly string[];
  readonly localViewFixed: readonly string[];
  readonly note: string;
  readonly fixedNote: string;
  readonly newNote: string;
  readonly errorLine: string;
  readonly okLine: string;
  /** Canonical render() strings for the accessible text version. */
  readonly brokenGlobal: string;
  readonly fixedGlobal: string;
  readonly fixedLocal: string;
  readonly errorMessage: string;
};

export type BoundaryDataset = {
  readonly id: string;
  readonly kind: 'boundary';
  readonly insideLabel: string;
  readonly inside: readonly string[];
  readonly outsideLabel: string;
  readonly outside: readonly string[];
};

export type TimelineEvent = {
  readonly id: string;
  readonly at: number;
  readonly label: string;
  readonly facet?: string;
  readonly kind?: 'decision' | 'event' | 'span' | 'deadline' | 'cancel';
};

export type TimelineDataset = {
  readonly id: string;
  readonly kind: 'timeline';
  readonly events: readonly TimelineEvent[];
};

export type PlayerStep = {
  readonly id: string;
  readonly title: string;
  readonly body: string;
  readonly highlight?: readonly string[];
};

export type PlayerDataset = {
  readonly id: string;
  readonly kind: 'animation';
  readonly title: string;
  readonly steps: readonly PlayerStep[];
};

/** Multi-box / layer / tree board — for structural maps that are not sequences. */
export type BoardNode = {
  readonly id: string;
  readonly label: string;
  readonly detail?: string;
};

export type BoardEdge = {
  readonly from: string;
  readonly to: string;
  readonly label?: string;
};

export type BoardDataset = {
  readonly id: string;
  readonly kind: 'board';
  readonly nodes: readonly BoardNode[];
  readonly edges?: readonly BoardEdge[];
  /** Optional column layout: each column is a list of node ids. */
  readonly columns?: readonly (readonly string[])[];
};

export type StaticDiagramDataset =
  | SequenceDataset
  | ProjectionDataset
  | TimelineDataset
  | BoardDataset
  | KnowledgeDataset
  | BoundaryDataset;

export type DiagramKind = StaticDiagramDataset['kind'] | 'animation';
