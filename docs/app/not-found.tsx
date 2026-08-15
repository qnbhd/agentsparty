import type { Metadata } from 'next';
import Link from 'next/link';
import { GlassLayout } from 'fumadocs-ui/layouts/glass';
import { baseOptions } from '@/app/layout.config';
import { pageTree } from '@/lib/source';

export const metadata: Metadata = {
  title: 'Page not found',
  description: 'That documentation page does not exist.',
};

// Rendered inside the documentation shell so a stale external link still
// arrives at the sidebar and the search dialog, not at a dead end.
export default function NotFound() {
  return (
    <GlassLayout tree={pageTree} {...baseOptions}>
      <main className="mx-auto flex w-full max-w-2xl flex-col items-start gap-6 px-6 py-24">
        <p className="font-mono text-sm tracking-widest text-fd-muted-foreground uppercase">
          404
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-balance">
          That page does not exist
        </h1>
        <p className="text-fd-muted-foreground text-pretty">
          The page may have been renamed or removed. Search the documentation,
          or start from one of the entry points below.
        </p>
        <ul className="flex flex-col gap-2">
          <li>
            <Link className="text-fd-primary hover:underline" href="/docs">
              Documentation home
            </Link>
          </li>
          <li>
            <Link
              className="text-fd-primary hover:underline"
              href="/docs/start/core-idea"
            >
              Core idea — what a fixed protocol buys you
            </Link>
          </li>
          <li>
            <Link
              className="text-fd-primary hover:underline"
              href="/docs/start/quickstart"
            >
              Quickstart — define and run a session
            </Link>
          </li>
          <li>
            <Link
              className="text-fd-primary hover:underline"
              href="/docs/reference/glossary"
            >
              Glossary — the vocabulary in one page
            </Link>
          </li>
        </ul>
      </main>
    </GlassLayout>
  );
}
