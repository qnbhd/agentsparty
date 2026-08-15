/**
 * Semantic diagram registry.
 *
 * Only top-level exports listed in STATIC_DIAGRAMS and ANIMATION_DIAGRAMS
 * count toward plan §5 metrics. Nested message/step/event ids do not.
 */

import type {
  BoardDataset,
  BoundaryDataset,
  KnowledgeDataset,
  PlayerDataset,
  ProjectionDataset,
  SequenceDataset,
  StaticDiagramDataset,
  TimelineDataset,
} from '../types';

// ---- sequences ----
export const linearSequence: SequenceDataset = {
  id: 'linear-sequence',
  kind: 'sequence',
  roles: ['A', 'B'],
  messages: [{ id: 'msg-note', from: 'A', to: 'B', label: 'Note(str)' }],
};

export const threeRoleSequence: SequenceDataset = {
  id: 'three-role-global-sequence',
  kind: 'sequence',
  variant: 'lifeline',
  roles: ['Writer', 'Reviewer', 'Tools'],
  messages: [
    { id: 'msg-draft', from: 'Writer', to: 'Reviewer', label: 'Draft', payload: '(str)' },
    { id: 'msg-approve', from: 'Reviewer', to: 'Tools', label: 'Publish', payload: '(str)', kind: 'alt' },
    { id: 'msg-revise', from: 'Reviewer', to: 'Writer', label: 'Revise', kind: 'alt' },
  ],
  // Verbatim render() output; asserted by docs/test-fixtures/diagrams.py.
  renderText: [
    'rec review',
    '  Writer -> Reviewer : Draft(str)',
    '  Reviewer -> Writer {',
    '    Approve():',
    '      Reviewer -> Tools : Publish(str)',
    '      end',
    '    Revise():',
    '      review',
    '  }',
  ].join('\n'),
};

export const approvalWorkflowSequence: SequenceDataset = {
  id: 'approval-workflow-sequence',
  kind: 'sequence',
  roles: ['Writer', 'Reviewer', 'Reader'],
  messages: [
    { id: 'approval-draft', from: 'Writer', to: 'Reviewer', label: 'Draft(str)' },
    { id: 'approval-alt', from: 'Reviewer', to: 'Writer', label: 'Approve | Reject', kind: 'alt' },
    { id: 'approval-result', from: 'Writer', to: 'Reader', label: 'Approve: Final | Reject: Rejected' },
  ],
};

export const toolboxSequence: SequenceDataset = {
  id: 'toolbox-as-role-sequence',
  kind: 'sequence',
  roles: ['User', 'Planner', 'Tools'],
  messages: [
    { id: 'msg-ask', from: 'User', to: 'Planner', label: 'ask(str)' },
    { id: 'msg-search', from: 'Planner', to: 'Tools', label: 'search(str)', kind: 'tool' },
    { id: 'msg-hits', from: 'Tools', to: 'Planner', label: 'hits(list)' },
    { id: 'msg-answer', from: 'Planner', to: 'User', label: 'answer(str)' },
  ],
};

export const fiveRoleSequence: SequenceDataset = {
  id: 'five-role-review-sequence',
  kind: 'sequence',
  roles: ['Client', 'Writer', 'Reviewer', 'Editor', 'Publisher'],
  messages: [
    { id: 'msg-brief', from: 'Client', to: 'Writer', label: 'Brief' },
    { id: 'msg-draft2', from: 'Writer', to: 'Reviewer', label: 'Draft' },
    { id: 'msg-notes', from: 'Reviewer', to: 'Editor', label: 'Notes' },
    { id: 'msg-ready', from: 'Editor', to: 'Publisher', label: 'Ready' },
    { id: 'msg-shipped', from: 'Publisher', to: 'Client', label: 'Shipped' },
  ],
};

export const castBindingSequence: SequenceDataset = {
  id: 'cast-binding-map',
  kind: 'sequence',
  roles: ['Protocol', 'Cast', 'Runtime'],
  messages: [
    { id: 'msg-project', from: 'Protocol', to: 'Cast', label: 'project roles' },
    { id: 'msg-play', from: 'Cast', to: 'Cast', label: 'play factories' },
    { id: 'msg-run', from: 'Cast', to: 'Runtime', label: 'run_sync' },
  ],
};

export const codecPipelineSequence: SequenceDataset = {
  id: 'payload-decode-boundary',
  kind: 'sequence',
  roles: ['Wire', 'Codec', 'Domain'],
  messages: [
    { id: 'msg-json', from: 'Wire', to: 'Codec', label: 'JSON bytes' },
    { id: 'msg-decode', from: 'Codec', to: 'Domain', label: 'decode()' },
  ],
};

// ---- projections ----
export const threeEndpointProjection: ProjectionDataset = {
  id: 'three-endpoint-projections',
  kind: 'projection',
  variant: 'linked',
  global: [
    'Writer -> Reviewer : Draft(str)',
    'Reviewer -> Writer : Note(str)',
    'Writer -> Archivist : Final(str)',
  ],
  endpoints: [
    {
      role: 'Writer',
      lines: ['!Reviewer : Draft(str)', '?Reviewer : Note(str)', '!Archivist : Final(str)'],
      slots: ['!Reviewer : Draft(str)', '?Reviewer : Note(str)', '!Archivist : Final(str)'],
    },
    {
      role: 'Reviewer',
      lines: ['?Writer : Draft(str)', '!Writer : Note(str)'],
      slots: ['?Writer : Draft(str)', '!Writer : Note(str)', null],
    },
    {
      role: 'Archivist',
      lines: ['?Writer : Final(str)'],
      slots: [null, null, '?Writer : Final(str)'],
    },
  ],
  // Verbatim render() output; asserted by docs/test-fixtures/diagrams.py.
  renderText: [
    'Writer -> Reviewer : Draft(str)',
    'Reviewer -> Writer : Note(str)',
    'Writer -> Archivist : Final(str)',
    'end',
    '',
    'Writer:',
    '  !Reviewer : Draft(str)',
    '  ?Reviewer : Note(str)',
    '  !Archivist : Final(str)',
    '  end',
    '',
    'Reviewer:',
    '  ?Writer : Draft(str)',
    '  !Writer : Note(str)',
    '  end',
    '',
    'Archivist:',
    '  ?Writer : Final(str)',
    '  end',
  ].join('\n'),
};

export const subtypeDirection: ProjectionDataset = {
  id: 'subtype-association-direction',
  kind: 'projection',
  global: ['implementation ≤ specification'],
  endpoints: [
    { role: 'Spec', lines: ['offers more branches', 'accepts fewer payloads'] },
    { role: 'Impl', lines: ['selects subset', 'sends subtype payloads'] },
  ],
};

export const composeBoundary: ProjectionDataset = {
  id: 'compose-contract-boundary',
  kind: 'projection',
  global: ['compose(left, right) at compatibility type'],
  endpoints: [
    { role: 'Left', lines: ['exports open ends'] },
    { role: 'Right', lines: ['imports matching ends'] },
    { role: 'Whole', lines: ['closed SessionType'] },
  ],
};

// ---- knowledge of alt (home page) ----
export const knowledgeOfChoice: KnowledgeDataset = {
  id: 'home-knowledge-of-alt',
  kind: 'knowledge',
  chooser: 'A',
  peer: 'B',
  blind: 'C',
  altLine: 'A -> B { Yes, No }',
  worlds: [
    {
      id: 'yes',
      label: 'Yes',
      action: 'C receives Y from A',
      message: 'A -> C : Y(str)',
      inform: 'A -> C : Yes(str)',
    },
    {
      id: 'no',
      label: 'No',
      action: 'C sends N to A',
      message: 'C -> A : N(str)',
      inform: 'A -> C : No(str)',
    },
  ],
  localViewBroken: ['?A : Y(str)', '!A : N(str)'],
  localViewFixed: ['?A {', '  Yes(str):', '    ?A : Y(str)', '  No(str):', '    !A : N(str)', '}'],
  note: 'C must behave differently on each branch, but never learned which one ran.',
  fixedNote: 'Now every local path starts with ?A — C learns the branch first.',
  newNote: 'new: A tells C which branch ran',
  errorLine: 'project(broken, C) → ProjectionError',
  okLine: 'project(fixed, C) → ok',
  // Verbatim render() output; asserted by docs/test-fixtures/diagrams.py.
  brokenGlobal: [
    'A -> B {',
    '  No():',
    '    C -> A : N(str)',
    '    end',
    '  Yes():',
    '    A -> C : Y(str)',
    '    end',
    '}',
  ].join('\n'),
  fixedGlobal: [
    'A -> B {',
    '  No():',
    '    A -> C : No(str)',
    '    C -> A : N(str)',
    '    end',
    '  Yes():',
    '    A -> C : Yes(str)',
    '    A -> C : Y(str)',
    '    end',
    '}',
  ].join('\n'),
  fixedLocal: [
    '?A {',
    '  No(str):',
    '    !A : N(str)',
    '    end',
    '  Yes(str):',
    '    ?A : Y(str)',
    '    end',
    '}',
  ].join('\n'),
  errorMessage: [
    "role 'C' cannot tell the branches of the alt A -> B apart:",
    "  on 'No' it must send N to A (as C), on 'Yes' it must receive Y from A (as C).",
    'A role that behaves differently per branch must be told which branch was taken — add a message from A (or B) to C inside each branch.',
  ].join('\n'),
};

// ---- guarantee boundary (home page) ----
export const guaranteeBoundary: BoundaryDataset = {
  id: 'home-guarantee-boundary',
  kind: 'boundary',
  insideLabel: 'Checked by agentsparty',
  inside: [
    'Declared labels only',
    'Knowledge of alt',
    'Guarded recursion',
    'Decode at the boundary',
    'Replay of decisions',
  ],
  outsideLabel: 'Outside the domain of definition',
  outside: ['Deadlock freedom', 'Liveness', 'Exactly-once effects', 'Distributed delivery'],
};

// ---- timelines ----
export const runtimeTimeline: TimelineDataset = {
  id: 'runtime-step-sequence',
  kind: 'timeline',
  events: [
    { id: 'ev-start', at: 0, label: 'SessionStarted', facet: 'runtime', kind: 'event' },
    { id: 'ev-select', at: 1, label: 'Selected Draft', facet: 'protocol', kind: 'decision' },
    { id: 'ev-model', at: 2, label: 'ModelCalled', facet: 'model', kind: 'event' },
    { id: 'ev-deliver', at: 3, label: 'Delivered', facet: 'protocol', kind: 'event' },
    { id: 'ev-end', at: 4, label: 'SessionFinished', facet: 'runtime', kind: 'event' },
  ],
};

export const cancelTimeline: TimelineDataset = {
  id: 'cancellation-broadcast',
  kind: 'timeline',
  events: [
    { id: 'ev-fail', at: 0, label: 'StepLimit at Tools', kind: 'cancel' },
    { id: 'ev-bcast', at: 1, label: 'broadcast cancel', kind: 'cancel' },
    { id: 'ev-all', at: 2, label: 'every participant cancels', kind: 'cancel' },
  ],
};

export const deadlineTimeline: TimelineDataset = {
  id: 'deadline-window',
  kind: 'timeline',
  events: [
    { id: 'ev-open', at: 0, label: 'alt opens', kind: 'span' },
    { id: 'ev-dl', at: 2, label: 'deadline', kind: 'deadline' },
    { id: 'ev-dex', at: 3, label: 'DeadlineExceededError', kind: 'cancel' },
  ],
};

// ---- boards (structural maps) ----
const board = (
  id: string,
  nodes: BoardDataset['nodes'],
  opts?: { edges?: BoardDataset['edges']; columns?: BoardDataset['columns'] },
): BoardDataset => ({
  id,
  kind: 'board',
  nodes,
  edges: opts?.edges,
  columns: opts?.columns,
});

export const codecFamilyTree = board('codec-family-tree', [
  { id: 'n-text', label: 'Text' },
  { id: 'n-int', label: 'Integer' },
  { id: 'n-list', label: 'list_of' },
  { id: 'n-opt', label: 'optional' },
  { id: 'n-rec', label: 'record' },
  { id: 'n-model', label: 'json_model' },
  { id: 'n-ref', label: 'refine' },
], { columns: [['n-text', 'n-int'], ['n-list', 'n-opt'], ['n-rec', 'n-model', 'n-ref']] });

export const syncVsAsync = board('sync-vs-async-boundary', [
  { id: 'n-sync', label: 'run_sync', detail: 'fresh event loop' },
  { id: 'n-async', label: 'await run()', detail: 'existing loop' },
], { columns: [['n-sync'], ['n-async']] });

export const facetFiltering = board('facet-filtering', [
  { id: 'n-rt', label: 'runtime' },
  { id: 'n-pr', label: 'protocol' },
  { id: 'n-md', label: 'model' },
  { id: 'n-tl', label: 'tool' },
], { columns: [['n-rt', 'n-pr'], ['n-md', 'n-tl']] });

export const traceEventAnatomy = board('trace-event-anatomy', [
  { id: 'n-facet', label: 'facet' },
  { id: 'n-name', label: 'name' },
  { id: 'n-span', label: 'span' },
  { id: 'n-payload', label: 'payload' },
], { columns: [['n-facet', 'n-name'], ['n-span', 'n-payload']] });

export const limitsBoard = board('step-unfold-token-limits', [
  { id: 'n-steps', label: 'steps', detail: 'StepLimitError' },
  { id: 'n-unfold', label: 'unfoldings', detail: 'RecursionLimitError' },
  { id: 'n-tok', label: 'tokens', detail: 'TokenLimitError' },
], { columns: [['n-steps'], ['n-unfold'], ['n-tok']] });

export const seqComposition = board('seq-composition', [
  { id: 'n-a', label: 'msg A→B' },
  { id: 'n-b', label: 'msg B→C' },
  { id: 'n-seq', label: 'seq / >>' },
], { edges: [{ from: 'n-a', to: 'n-seq' }, { from: 'n-b', to: 'n-seq' }], columns: [['n-a', 'n-b'], ['n-seq']] });

export const retryTree = board('retry-decision-tree', [
  { id: 'n-call', label: 'complete()' },
  { id: 'n-retry', label: 'retry transient' },
  { id: 'n-raise', label: 'raise ModelError' },
], { edges: [{ from: 'n-call', to: 'n-retry' }, { from: 'n-call', to: 'n-raise' }], columns: [['n-call'], ['n-retry', 'n-raise']] });

export const fallbackTree = board('fallback-decision-tree', [
  { id: 'n-pri', label: 'primary' },
  { id: 'n-sec', label: 'secondary' },
  { id: 'n-fail', label: 'raise unavailable' },
], { edges: [{ from: 'n-pri', to: 'n-sec' }, { from: 'n-sec', to: 'n-fail' }], columns: [['n-pri'], ['n-sec'], ['n-fail']] });

export const meteringBoundary = board('metering-boundary', [
  { id: 'n-meter', label: 'Metered' },
  { id: 'n-inner', label: 'inner model' },
], { edges: [{ from: 'n-meter', to: 'n-inner' }], columns: [['n-meter'], ['n-inner']] });

export const providerBaseUrlBoundary = board('provider-base-url-boundary', [
  { id: 'n-config', label: 'base_url' },
  { id: 'n-client', label: 'provider client' },
], { edges: [{ from: 'n-config', to: 'n-client' }], columns: [['n-config'], ['n-client']] });

export const offlineArch = board('offline-test-architecture', [
  { id: 'n-model', label: 'OpenAIModel' },
  { id: 'n-sh', label: 'ScriptedHumanIo' },
  { id: 'n-mj', label: 'MemoryJournal' },
], { columns: [['n-model'], ['n-sh'], ['n-mj']] });

export const exampleLadder = board('example-ladder', [
  { id: 'n-off', label: 'offline' },
  { id: 'n-hello', label: 'online hello' },
  { id: 'n-multi', label: 'multi-role' },
], { edges: [{ from: 'n-off', to: 'n-hello' }, { from: 'n-hello', to: 'n-multi' }], columns: [['n-off'], ['n-hello'], ['n-multi']] });

export const errorTaxonomy = board('error-taxonomy', [
  { id: 'n-proj', label: 'Projection' },
  { id: 'n-pay', label: 'Payload' },
  { id: 'n-mod', label: 'Model' },
  { id: 'n-lim', label: 'Limits' },
  { id: 'n-jou', label: 'Journal' },
], { columns: [['n-proj', 'n-pay'], ['n-mod'], ['n-lim', 'n-jou']] });

export const publicApiTiers = board('public-api-tiers', [
  { id: 'n-core', label: 'core' },
  { id: 'n-th', label: 'type-home' },
  { id: 'n-ext', label: 'extension' },
], { columns: [['n-core'], ['n-th'], ['n-ext']] });

export const packageMap = board('package-module-map', [
  { id: 'n-proto', label: 'protocol' },
  { id: 'n-run', label: 'runtime' },
  { id: 'n-llm', label: 'llm' },
  { id: 'n-journal', label: 'journal' },
  { id: 'n-tracing', label: 'tracing' },
], { columns: [['n-proto', 'n-run'], ['n-llm'], ['n-journal', 'n-tracing']] });

export const notationLegend = board('protocol-notation-legend', [
  { id: 'n-arrow', label: '->', detail: 'message' },
  { id: 'n-bang', label: '!', detail: 'send' },
  { id: 'n-q', label: '?', detail: 'recv' },
  { id: 'n-br', label: '{}', detail: 'alt' },
  { id: 'n-rec2', label: 'rec', detail: 'recursion' },
  { id: 'n-par3', label: 'par', detail: 'parallel' },
], { columns: [['n-arrow', 'n-bang', 'n-q'], ['n-br', 'n-rec2', 'n-par3']] });

export const deployBoundary = board('supported-unsupported-deployment', [
  { id: 'n-inproc', label: 'in-process', detail: 'supported' },
  { id: 'n-dist', label: 'distributed runtime', detail: 'unsupported' },
], { columns: [['n-inproc'], ['n-dist']] });

export const docsPipeline = board('docs-generation-pipeline', [
  { id: 'n-dump', label: 'dump API' },
  { id: 'n-gen', label: 'generate MDX' },
  { id: 'n-llms', label: 'llms' },
  { id: 'n-check', label: 'check' },
], { edges: [{ from: 'n-dump', to: 'n-gen' }, { from: 'n-gen', to: 'n-llms' }, { from: 'n-llms', to: 'n-check' }], columns: [['n-dump', 'n-gen'], ['n-llms', 'n-check']] });

export const qualityGates = board('documentation-quality-gates', [
  { id: 'n-fences', label: 'fences' },
  { id: 'n-xref', label: 'xref' },
  { id: 'n-stale', label: 'staleness' },
  { id: 'n-diag', label: 'diagrams' },
], { columns: [['n-fences', 'n-xref'], ['n-stale', 'n-diag']] });

export const exampleIndexBoard = board('examples-by-outcome', [
  { id: 'n-hello2', label: 'hello' },
  { id: 'n-appr', label: 'approval' },
  { id: 'n-ref', label: 'projection refusal' },
  { id: 'n-tb', label: 'toolbox replay' },
], { columns: [['n-hello2', 'n-appr'], ['n-ref', 'n-tb']] });

// ---- animations ----
export const animDeclareProjectRefuse: PlayerDataset = {
  id: 'anim-declare-project-refuse',
  kind: 'animation',
  title: 'Declare, project, gate, run',
  steps: [
    { id: 'step-declare', title: 'Declare', body: 'One conversation, written down before anything runs.' },
    { id: 'step-project', title: 'Project', body: 'Each role gets the local view it can observe.' },
    { id: 'step-gate', title: 'Gate', body: 'A blind role is refused before any model call.' },
    { id: 'step-run', title: 'Run', body: 'Cast binds participants and executes the session.' },
  ],
};

export const animGlobalToEndpoints: PlayerDataset = {
  id: 'anim-global-to-endpoints',
  kind: 'animation',
  title: 'Global type to endpoint views',
  steps: [
    { id: 'step-1', title: 'Global messages', body: 'One SessionType lists every send and alt.' },
    { id: 'step-2', title: 'Highlight a role', body: 'Projection keeps only what that role can observe.' },
    { id: 'step-3', title: 'Derive send/recv', body: 'Internal alt becomes select; external becomes offer.' },
    { id: 'step-4', title: 'Run', body: 'Cast binds participants and executes.' },
  ],
};

export const animMessageExchange: PlayerDataset = {
  id: 'anim-message-exchange',
  kind: 'animation',
  title: 'Message exchange at runtime',
  steps: [
    { id: 'step-1', title: 'Select', body: 'Sender chooses a declared Case.' },
    { id: 'step-2', title: 'Model answer', body: 'Model fills only the declared payload schema.' },
    { id: 'step-3', title: 'Decode', body: 'Codec parses JSON into a domain value.' },
    { id: 'step-4', title: 'Deliver', body: 'Envelope crosses to the receiver.' },
    { id: 'step-5', title: 'Offer', body: 'Receiver reacts on the informed branch.' },
  ],
};

export const animProjection: PlayerDataset = {
  id: 'anim-projection',
  kind: 'animation',
  title: 'Walking the AST into three columns',
  steps: [
    { id: 'step-1', title: 'Enter message', body: 'Sender gains send; receiver gains recv.' },
    { id: 'step-2', title: 'Enter alt', body: 'Chooser gains select; informed gain offer.' },
    { id: 'step-3', title: 'Drop silent work', body: 'Untouched roles keep no local action.' },
    { id: 'step-4', title: 'Three endpoints', body: 'Each column is a complete local protocol.' },
  ],
};

export const animKnowledgeOfChoice: PlayerDataset = {
  id: 'anim-knowledge-of-alt',
  kind: 'animation',
  title: 'Why invisible alt refuses',
  steps: [
    { id: 'step-1', title: 'Chooser informs B', body: 'A selects Yes|No toward B.' },
    { id: 'step-2', title: 'C stays blind', body: 'C is not told which branch ran.' },
    { id: 'step-3', title: 'Incompatible actions', body: 'On Yes C receives; on No C sends.' },
    { id: 'step-4', title: 'Refusal', body: 'ProjectionError before any model call.' },
  ],
};

export const animRecursion: PlayerDataset = {
  id: 'anim-recursion',
  kind: 'animation',
  title: 'Recursion vs finite repeat',
  steps: [
    { id: 'step-1', title: 'Binder', body: 'rec(X) introduces a recursion variable.' },
    { id: 'step-2', title: 'Body', body: 'Messages and alts run inside the binder.' },
    { id: 'step-3', title: 'again / var', body: 'var(X) returns to the binder.' },
    { id: 'step-4', title: 'Unfold counter', body: 'Allowance bounds unfolds.' },
    { id: 'step-5', title: 'End', body: 'must_terminate asks whether every path finishes.' },
  ],
};

export const animParallel: PlayerDataset = {
  id: 'anim-parallel',
  kind: 'animation',
  title: 'Parallel tracks without join value',
  steps: [
    { id: 'step-1', title: 'Fork', body: 'par(left, right) starts two independent tracks.' },
    { id: 'step-2', title: 'Interleave', body: 'Events from both tracks appear without a product type.' },
    { id: 'step-3', title: 'Both finish', body: 'Session ends when every track ends.' },
  ],
};

export const animCancellation: PlayerDataset = {
  id: 'anim-cancellation',
  kind: 'animation',
  title: 'Session-wide cancellation',
  steps: [
    { id: 'step-1', title: 'Failure at one role', body: 'StepLimit or cancel on one participant.' },
    { id: 'step-2', title: 'Broadcast', body: 'Runtime notifies every other participant.' },
    { id: 'step-3', title: 'Clean roll-up', body: 'Awaiting peers stop; original error surfaces.' },
  ],
};

export const animReplay: PlayerDataset = {
  id: 'anim-replay',
  kind: 'animation',
  title: 'Journal replay skips paid work',
  steps: [
    { id: 'step-1', title: 'First run', body: 'Model and tool calls append decisions.' },
    { id: 'step-2', title: 'Second run', body: 'Runtime reads decisions from the journal.' },
    { id: 'step-3', title: 'Counters stay zero', body: 'Tool call count remains 0 on pure replay.' },
  ],
};

/** Top-level static semantic diagrams (must each be drawable). */
export const STATIC_DIAGRAMS: readonly StaticDiagramDataset[] = [
  linearSequence,
  threeRoleSequence,
  approvalWorkflowSequence,
  toolboxSequence,
  fiveRoleSequence,
  castBindingSequence,
  codecPipelineSequence,
  threeEndpointProjection,
  subtypeDirection,
  composeBoundary,
  knowledgeOfChoice,
  guaranteeBoundary,
  runtimeTimeline,
  cancelTimeline,
  deadlineTimeline,
  codecFamilyTree,
  syncVsAsync,
  facetFiltering,
  traceEventAnatomy,
  limitsBoard,
  seqComposition,
  retryTree,
  fallbackTree,
  meteringBoundary,
  providerBaseUrlBoundary,
  offlineArch,
  exampleLadder,
  errorTaxonomy,
  publicApiTiers,
  packageMap,
  notationLegend,
  deployBoundary,
  docsPipeline,
  qualityGates,
  exampleIndexBoard,
];

export const ANIMATION_DIAGRAMS: readonly PlayerDataset[] = [
  animDeclareProjectRefuse,
  animGlobalToEndpoints,
  animMessageExchange,
  animProjection,
  animKnowledgeOfChoice,
  animRecursion,
  animParallel,
  animCancellation,
  animReplay,
];

export const STATIC_DIAGRAM_IDS: readonly string[] = STATIC_DIAGRAMS.map((d) => d.id);
export const ANIMATION_DIAGRAM_IDS: readonly string[] = ANIMATION_DIAGRAMS.map((d) => d.id);

// legacy alias used by quality-report regex fallbacks
export const allDatasetIds = [...STATIC_DIAGRAM_IDS, ...ANIMATION_DIAGRAM_IDS] as const;
export const animationDatasets = ANIMATION_DIAGRAMS;
export const staticDatasets = Object.fromEntries(
  STATIC_DIAGRAMS.filter((d) => d.kind === 'board').map((d) => [d.id, d]),
);
