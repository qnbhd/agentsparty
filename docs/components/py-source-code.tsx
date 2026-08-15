import type { ReactNode } from 'react';

/**
 * Replacement for `PySourceCode` from fumadocs-python.
 *
 * The upstream component hands a `className` callback to a client-side
 * collapsible; functions cannot cross the server/client boundary, so every
 * generated API page fails to prerender under `output: 'export'`. A native
 * `<details>` needs no client component at all.
 */
export function PySourceCode({ children }: { children: ReactNode }) {
  return (
    <details className="group my-6 rounded-lg border bg-fd-card p-3 prose-no-margin">
      <summary className="cursor-pointer list-none text-sm font-medium text-fd-muted-foreground select-none hover:text-fd-foreground">
        <span className="inline-block transition-transform group-open:rotate-90">›</span> Source code
      </summary>
      {children}
    </details>
  );
}
