// Surfaces the `status` frontmatter that `scripts/check-mdx.mjs` already
// enforces. Without this the field is an authoring-only contract the reader
// never sees, so a draft page looks exactly as settled as a stable one.
const LABELS = {
  draft: { text: 'Draft', hint: 'Incomplete; API may still move.' },
  review: { text: 'In review', hint: 'Written, not yet verified end to end.' },
  stable: { text: 'Stable', hint: 'Verified against the shipped API.' },
  generated: { text: 'Generated', hint: 'Produced from the Python source.' },
} as const;

const DOT = {
  draft: 'var(--diagram-amber)',
  review: 'var(--diagram-blue)',
  stable: 'var(--color-fd-primary)',
  generated: 'var(--color-fd-muted-foreground)',
} as const;

export type PageStatus = keyof typeof LABELS;

export function PageStatusBadge({ status }: { status: PageStatus }) {
  const { text, hint } = LABELS[status];
  return (
    <span
      className="text-fd-muted-foreground inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5 font-mono text-[0.6875rem] tracking-wider uppercase"
      title={hint}
    >
      <span
        aria-hidden
        className="size-1.5 rounded-full"
        style={{ backgroundColor: DOT[status] }}
      />
      {text}
    </span>
  );
}
