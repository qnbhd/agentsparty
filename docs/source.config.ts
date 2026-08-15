import { defineConfig, defineDocs } from 'fumadocs-mdx/config';
import { pageSchema } from 'fumadocs-core/source/schema';
import { z } from 'zod';
import remarkXref from './scripts/remark-xref';
import remarkMermaid from './scripts/remark-mermaid';
import remarkTerminal from './scripts/remark-terminal';

// `pageSchema` strips unknown frontmatter, so the editorial fields authored
// pages carry have to be declared to survive into `page.data`. `status` uses
// the vocabulary `scripts/check-mdx.mjs` enforces; it is absent here only on
// the generated `(api)` pages, which that check skips.
// `nullish`, not `optional`: the dev-server adapter supplies a missing
// frontmatter key as `null`, which `optional()` alone rejects.
const docsSchema = pageSchema.extend({
  status: z.enum(['draft', 'review', 'stable', 'generated']).nullish(),
  journey: z.string().nullish(),
});

export const { docs, meta } = defineDocs({
  dir: 'content/docs',
  docs: { schema: docsSchema },
});

export default defineConfig({
  mdxOptions: {
    remarkPlugins: [remarkXref, remarkMermaid, remarkTerminal],
    rehypeCodeOptions: {
      langs: ['bash', 'json', 'mermaid', 'python', 'typescript'],
      themes: { light: 'vitesse-light', dark: 'vitesse-dark' },
    },
  },
});
