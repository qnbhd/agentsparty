import { defineConfig, defineDocs } from 'fumadocs-mdx/config';
import remarkXref from './scripts/remark-xref';
import remarkMermaid from './scripts/remark-mermaid';

export const { docs, meta } = defineDocs({
  dir: 'content/docs',
});

export default defineConfig({
  mdxOptions: {
    remarkPlugins: [remarkXref, remarkMermaid],
    rehypeCodeOptions: {
      langs: ['bash', 'json', 'mermaid', 'python', 'typescript'],
      themes: { light: 'vitesse-light', dark: 'vitesse-black' },
    },
  },
});
