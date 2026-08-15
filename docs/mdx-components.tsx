import defaultMdxComponents from 'fumadocs-ui/mdx';
import type { MDXComponents } from 'mdx/types';
import { Step, Steps } from 'fumadocs-ui/components/steps';
import * as Python from 'fumadocs-python/components';
import { PySourceCode } from '@/components/py-source-code';
import {
  DiagramFrame,
  ProtocolSequence,
  ProjectionView,
  Timeline,
  ProtocolPlayer,
  FixedReviewProtocol,
  MsgMiniature,
  SequenceMiniature,
  AltMiniature,
  RecMiniature,
  ParMiniature,
  ComposeOwnershipMiniature,
  TerminationMiniature,
  AllowanceMiniature,
  BlindChoiceWidget,
  ProjectionErrorMap,
  ChoreographyEquivalence,
} from '@/components/diagrams';
import * as DiagramWrappers from '@/components/diagrams/wrappers';
import { ExampleSource } from '@/components/example-source';
import { MermaidSvg } from '@/components/mermaid-svg';
import { Terminal } from '@/components/terminal';

export function getMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    ...Python,
    Steps,
    Step,
    PySourceCode,
    DiagramFrame,
    ProtocolSequence,
    ProjectionView,
    Timeline,
    ProtocolPlayer,
    FixedReviewProtocol,
    MsgMiniature,
    SequenceMiniature,
    AltMiniature,
    RecMiniature,
    ParMiniature,
    ComposeOwnershipMiniature,
    TerminationMiniature,
    AllowanceMiniature,
    BlindChoiceWidget,
    ProjectionErrorMap,
    ChoreographyEquivalence,
    ExampleSource,
    MermaidSvg,
    Terminal,
    ...DiagramWrappers,
    ...components,
  };
}
