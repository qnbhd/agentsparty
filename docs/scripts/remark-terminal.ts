/**
 * Transform ```text fences into <Terminal value="..." /> so plain terminal
 * blocks (program output, interactive prompts) render as their own surface
 * instead of as an un-highlighted copy of a code card.
 *
 * Mirrors remark-mermaid: the whole fence becomes one MDX JSX element whose
 * content travels as a string attribute, which remark-mdx escapes safely
 * regardless of braces, quotes, or newlines in the source.
 */
import { visit } from 'unist-util-visit';
import type { Root, Code } from 'mdast';

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

export default function remarkTerminal() {
  return (tree: Root) => {
    const nodes: Array<{ node: Code; index: number; parent: { children: unknown[] } }> = [];
    visit(tree, 'code', (node: Code, index, parent) => {
      if (node.lang === 'text' && parent && typeof index === 'number') {
        nodes.push({ node, index, parent: parent as { children: unknown[] } });
      }
    });
    for (const { node, index, parent } of nodes) {
      const jsx: MdxJsxFlowElement = {
        type: 'mdxJsxFlowElement',
        name: 'Terminal',
        attributes: [{ type: 'mdxJsxAttribute', name: 'value', value: node.value }],
        children: [],
        data: { _mdxExplicitJsx: true },
      };
      parent.children[index] = jsx;
    }
  };
}
