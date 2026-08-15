import { readFileSync } from 'node:fs';
import { visit } from 'unist-util-visit';
import type { Root, Text } from 'mdast';

type XrefMap = Record<string, string>;

const XREF = /\[\[([A-Za-z_][\w.]*)\]\]/g;

const readXrefMap = (): XrefMap => {
  try {
    const source = readFileSync(new URL('../public/api-data.json', import.meta.url), 'utf8');
    return JSON.parse(source).xref_map as XrefMap;
  } catch {
    return {};
  }
};

export default function remarkXref() {
  const xrefMap = readXrefMap();
  return (tree: Root) => {
    visit(tree, 'text', (node, index, parent) => {
      if (index === undefined || parent === undefined) return;
      const text = node as Text;
      const parts: Array<Text | { type: 'link'; url: string; children: Text[] }> = [];
      let cursor = 0;
      for (const match of text.value.matchAll(XREF)) {
        const target = xrefMap[match[1]];
        if (!target || match.index === undefined) continue;
        if (match.index > cursor) parts.push({ type: 'text', value: text.value.slice(cursor, match.index) });
        parts.push({ type: 'link', url: target, children: [{ type: 'text', value: match[1] }] });
        cursor = match.index + match[0].length;
      }
      if (parts.length === 0) return;
      if (cursor < text.value.length) parts.push({ type: 'text', value: text.value.slice(cursor) });
      parent.children.splice(index, 1, ...parts);
    });
  };
}
