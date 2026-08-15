/**
 * Transform ```mermaid fences into <MermaidSvg svg="..." /> with real SVG
 * via pure-Node mermaid subset renderer (no browser required).
 */
import { visit } from 'unist-util-visit';
import type { Root, Code } from 'mdast';
// Pure-Node subset renderer (see mermaid-to-svg.mjs).
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore -- local .mjs without package types
import { mermaidToSvg } from './mermaid-to-svg.mjs';

type MdxJsxAttribute = {
  type: 'mdxJsxAttribute';
  name: string;
  value: string;
};

type MdxJsxFlowElement = {
  type: 'mdxJsxFlowElement';
  name: string;
  attributes: MdxJsxAttribute[];
  children: [];
  data?: { _mdxExplicitJsx: boolean };
};

export default function remarkMermaid() {
  return async (tree: Root) => {
    const nodes: Array<{ node: Code; index: number; parent: { children: unknown[] } }> = [];
    visit(tree, 'code', (node: Code, index, parent) => {
      if (node.lang === 'mermaid' && parent && typeof index === 'number') {
        nodes.push({ node, index, parent: parent as { children: unknown[] } });
      }
    });
    for (const { node, index, parent } of nodes) {
      try {
        const svg = mermaidToSvg(node.value);
        if (!svg.includes('<svg')) {
          throw new Error('renderer returned non-SVG');
        }
        const jsx: MdxJsxFlowElement = {
          type: 'mdxJsxFlowElement',
          name: 'MermaidSvg',
          attributes: [{ type: 'mdxJsxAttribute', name: 'svg', value: svg }],
          children: [],
          data: { _mdxExplicitJsx: true },
        };
        parent.children[index] = jsx;
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        throw new Error(`Mermaid render failed: ${message}\nSource:\n${node.value}`);
      }
    }
  };
}
