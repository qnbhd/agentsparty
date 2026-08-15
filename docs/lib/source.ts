import type { Node, Root } from 'fumadocs-core/page-tree';
import { loader } from 'fumadocs-core/source';
import { lucideIconsPlugin } from 'fumadocs-core/source/plugins/lucide-icons';
import { toFumadocsSource } from 'fumadocs-mdx/runtime/server';
import { docs, meta } from '@/.source/server';

export const source = loader({
  baseUrl: '/docs',
  source: toFumadocsSource(docs, meta),
  plugins: [lucideIconsPlugin()],
});

// The glass sidebar opens every folder by default. Only the top-level sections
// stay expanded; folders nested inside them (tutorials, the generated API tree)
// start collapsed, and the sidebar still opens the folder holding the current
// page.
const collapsed = (node: Node): Node =>
  node.type === 'folder'
    ? { ...node, defaultOpen: false, children: node.children.map(collapsed) }
    : node;

export const pageTree: Root = {
  ...source.pageTree,
  children: source.pageTree.children.map((node) =>
    node.type === 'folder' ? { ...node, children: node.children.map(collapsed) } : node,
  ),
};
