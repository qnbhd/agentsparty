/**
 * MDX wrappers over the diagram registry.
 */
import {
  ProtocolPlayer,
  ProtocolSequence,
  ProjectionView,
  Timeline,
  BoardView,
  DeclareProjectRefuse,
  KnowledgeOfChoice,
  GuaranteeBoundary,
  STATIC_DIAGRAMS,
  ANIMATION_DIAGRAMS,
  type StaticDiagramDataset,
} from './index';

function renderStatic(
  dataset: StaticDiagramDataset,
  title: string,
  caption: string,
  description: string,
) {
  switch (dataset.kind) {
    case 'sequence':
      return (
        <ProtocolSequence
          dataset={dataset}
          title={title}
          caption={caption}
          description={description}
        />
      );
    case 'projection':
      return (
        <ProjectionView
          dataset={dataset}
          title={title}
          caption={caption}
          description={description}
        />
      );
    case 'timeline':
      return (
        <Timeline dataset={dataset} title={title} caption={caption} description={description} />
      );
    case 'board':
      return (
        <BoardView dataset={dataset} title={title} caption={caption} description={description} />
      );
    case 'knowledge':
      return (
        <KnowledgeOfChoice
          dataset={dataset}
          title={title}
          caption={caption}
          description={description}
        />
      );
    case 'boundary':
      return (
        <GuaranteeBoundary
          dataset={dataset}
          title={title}
          caption={caption}
          description={description}
        />
      );
  }
}

const staticMeta: Record<string, { title: string; caption: string; description: string }> = {
  'linear-sequence': { title: 'Linear note', caption: 'Single message A to B.', description: 'Minimal sequence for the offline quickstart.' },
  'three-role-global-sequence': { title: 'Three-role global sequence', caption: 'Draft, alt, and a loop back to Writer.', description: 'Writer submits a draft; Reviewer approves to Tools or revises back.' },
  'approval-workflow-sequence': { title: 'Approval workflow topology', caption: 'The result is explicit on both branches.', description: 'Approve sends Final; Reject sends Rejected, so Reader has a mergeable endpoint.' },
  'toolbox-as-role-sequence': { title: 'Toolbox as a role', caption: 'User, Planner, Tools exchange.', description: 'search is a protocol label, not a hidden callback.' },
  'five-role-review-sequence': { title: 'Five-role review', caption: 'Client through Publisher.', description: 'Longer showcase topology.' },
  'cast-binding-map': { title: 'Cast binding map', caption: 'Protocol to Cast to Runtime.', description: 'Projection section grows with each play.' },
  'payload-decode-boundary': { title: 'Payload decode boundary', caption: 'Wire bytes become domain values.', description: 'Codec.decode sits at the perimeter.' },
  'three-endpoint-projections': { title: 'Three endpoint projections', caption: 'Sending becomes !, receiving becomes ?, and an uninvolved role sees nothing.', description: 'Select a global message to light the local lines it becomes across all three endpoints.' },
  'home-knowledge-of-alt': { title: 'Why blind alt refuses', caption: 'Two worlds, one local view, a toggle that fixes it.', description: 'C must act differently on unobserved branches; the fix is a declared message.' },
  'home-guarantee-boundary': { title: 'The guarantee boundary', caption: 'Checked inside, unclaimed outside.', description: 'What agentsparty guarantees versus what stays outside the domain of definition.' },
  'subtype-association-direction': { title: 'Subtype and association', caption: 'Implementation is smaller than specification.', description: 'Subtype direction for protocol conformance.' },
  'compose-contract-boundary': { title: 'Compose contract boundary', caption: 'Left and right meet at compatibility.', description: 'compose closes open ends into one SessionType.' },
  'runtime-step-sequence': { title: 'Runtime step sequence', caption: 'Session events from start to finish.', description: 'Selected, model, delivered, finished.' },
  'cancellation-broadcast': { title: 'Cancellation broadcast', caption: 'Failure fans out to every participant.', description: 'Session-wide cancel after a step limit.' },
  'deadline-window': { title: 'Deadline window', caption: 'Choice open until deadline.', description: 'DeadlineExceededError ends the branch window.' },
  'codec-family-tree': { title: 'Codec family', caption: 'Primitive and compound codecs.', description: 'Text, containers, record, refine.' },
  'sync-vs-async-boundary': { title: 'Sync versus async', caption: 'run_sync versus await run.', description: 'Event-loop boundary for callers.' },
  'facet-filtering': { title: 'Facet filtering', caption: 'runtime, protocol, model, tool.', description: 'Trace facets for selective observation.' },
  'trace-event-anatomy': { title: 'Trace event anatomy', caption: 'facet, name, span, payload.', description: 'Fields of a single observation record.' },
  'step-unfold-token-limits': { title: 'Allowance limits', caption: 'steps, unfolds, tokens.', description: 'Three distinct limit error families.' },
  'seq-composition': { title: 'Sequential composition', caption: 'seq and >> order messages.', description: 'Ordered steps on one conversation.' },
  'retry-decision-tree': { title: 'Retry decision tree', caption: 'Retry transient or raise.', description: 'Retrying wrapper outcomes.' },
  'fallback-decision-tree': { title: 'Fallback decision tree', caption: 'Primary, secondary, raise.', description: 'Fallback wrapper outcomes.' },
  'metering-boundary': { title: 'Metering boundary', caption: 'Metered wraps an inner model.', description: 'Token accounting without changing the protocol.' },
  'offline-test-architecture': { title: 'Model test architecture', caption: 'OpenAI model, human, journal.', description: 'Model-backed examples with journaled decisions.' },
  'example-ladder': { title: 'Example ladder', caption: 'offline to multi-role.', description: 'Progressive example complexity.' },
  'error-taxonomy': { title: 'Error taxonomy', caption: 'Projection through journal families.', description: 'Typed failure families at the product boundary.' },
  'public-api-tiers': { title: 'Public API tiers', caption: 'core, type-home, extension.', description: 'ADR 0029 stability tiers.' },
  'package-module-map': { title: 'Package module map', caption: 'protocol, runtime, llm, journal, tracing.', description: 'Primary product modules.' },
  'protocol-notation-legend': { title: 'Protocol notation legend', caption: 'Symbols used by render().', description: 'Compact multiparty session-protocol notation.' },
  'supported-unsupported-deployment': { title: 'Deployment boundary', caption: 'In-process only.', description: 'Distributed runtime is not shipped.' },
  'docs-generation-pipeline': { title: 'Docs generation pipeline', caption: 'dump, generate, llms, check.', description: 'How the documentation site is produced.' },
  'documentation-quality-gates': { title: 'Documentation quality gates', caption: 'fences, xref, staleness, diagrams.', description: 'Automated checks in npm run check.' },
  'examples-by-outcome': { title: 'Examples by outcome', caption: 'Task-shaped entry points.', description: 'Editorial deep-dives from the catalogue.' },
};

const animMeta: Record<string, { caption: string; description: string }> = {
  'anim-declare-project-refuse': { caption: 'One conversation, then a gate that refuses blind roles before the model.', description: 'declare, project, gate, run: the gate stops a ProjectionError short of the model.' },
  'anim-global-to-endpoints': { caption: 'One SessionType yields every endpoint view.', description: 'Steps walk from global messages through role highlight to Cast.run.' },
  'anim-message-exchange': { caption: 'Runtime steps are not a black box.', description: 'Select, model answer, decode, deliver, offer.' },
  'anim-projection': { caption: 'Projection builds three columns from one tree.', description: 'Silent edges are dropped per role.' },
  'anim-knowledge-of-alt': { caption: 'Blind alt fails before tokens.', description: 'Role C cannot act differently on unobserved branches.' },
  'anim-recursion': { caption: 'Recursion binders versus finite repeat.', description: 'Allowance bounds unfolds.' },
  'anim-parallel': { caption: 'Parallel tracks finish without a join value.', description: 'Independent tracks interleave in the trace.' },
  'anim-cancellation': { caption: 'Cancellation is session-wide.', description: 'One failure broadcasts to every participant.' },
  'anim-replay': { caption: 'Replay reads decisions; paid work stays zero.', description: 'Journal semantics on a second run.' },
};

function StaticById({ id }: { id: string }) {
  const dataset = STATIC_DIAGRAMS.find((d) => d.id === id);
  const meta = staticMeta[id];
  if (!dataset || !meta) throw new Error(`unknown static diagram: ${id}`);
  return renderStatic(dataset, meta.title, meta.caption, meta.description);
}

function AnimById({ id }: { id: string }) {
  const dataset = ANIMATION_DIAGRAMS.find((d) => d.id === id);
  const meta = animMeta[id];
  if (!dataset || !meta) throw new Error(`unknown animation: ${id}`);
  return <ProtocolPlayer dataset={dataset} caption={meta.caption} description={meta.description} />;
}

export function AnimGlobalToEndpoints() {
  return <AnimById id="anim-global-to-endpoints" />;
}

export function AnimDeclareProjectRefuse() {
  const dataset = ANIMATION_DIAGRAMS.find((d) => d.id === 'anim-declare-project-refuse');
  const meta = animMeta['anim-declare-project-refuse'];
  if (!dataset || !meta) throw new Error('unknown animation: anim-declare-project-refuse');
  return (
    <DeclareProjectRefuse
      dataset={dataset}
      caption={meta.caption}
      description={meta.description}
      autoplay
    />
  );
}

export function AnimMessageExchange() {
  return <AnimById id="anim-message-exchange" />;
}

export function AnimProjectionWalk() {
  return <AnimById id="anim-projection" />;
}

export function AnimKnowledgeOfChoice() {
  return <AnimById id="anim-knowledge-of-alt" />;
}

export function AnimRecursion() {
  return <AnimById id="anim-recursion" />;
}

export function AnimParallel() {
  return <AnimById id="anim-parallel" />;
}

export function AnimCancellation() {
  return <AnimById id="anim-cancellation" />;
}

export function AnimReplay() {
  return <AnimById id="anim-replay" />;
}

export function DiagThreeRoleSequence() {
  return <StaticById id="three-role-global-sequence" />;
}

export function DiagApprovalWorkflow() {
  return <StaticById id="approval-workflow-sequence" />;
}

export function DiagLinearSequence() {
  return <StaticById id="linear-sequence" />;
}

export function DiagProjection() {
  return <StaticById id="three-endpoint-projections" />;
}

export function DiagKnowledgeOfChoice() {
  return <StaticById id="home-knowledge-of-alt" />;
}

export function DiagGuaranteeBoundary() {
  return <StaticById id="home-guarantee-boundary" />;
}

export function DiagRuntimeTimeline() {
  return <StaticById id="runtime-step-sequence" />;
}

export function DiagToolboxSequence() {
  return <StaticById id="toolbox-as-role-sequence" />;
}

export function DiagCancelTimeline() {
  return <StaticById id="cancellation-broadcast" />;
}

export function DiagFiveRole() {
  return <StaticById id="five-role-review-sequence" />;
}

export function DiagComposeBoundary() {
  return <StaticById id="compose-contract-boundary" />;
}

export function DiagSubtypeDirection() {
  return <StaticById id="subtype-association-direction" />;
}

export function DiagCodecBoundary() {
  return <StaticById id="payload-decode-boundary" />;
}

export function DiagAllowanceLimits() {
  return <StaticById id="step-unfold-token-limits" />;
}

export function DiagDeadlineWindow() {
  return <StaticById id="deadline-window" />;
}

export function DiagSyncAsync() {
  return <StaticById id="sync-vs-async-boundary" />;
}

export function DiagOfflineArchitecture() {
  return <StaticById id="offline-test-architecture" />;
}

export function DiagExampleLadder() {
  return <StaticById id="example-ladder" />;
}

export function DiagPackageMap() {
  return <StaticById id="package-module-map" />;
}

export function DiagDocumentationPipeline() {
  return <StaticById id="docs-generation-pipeline" />;
}
