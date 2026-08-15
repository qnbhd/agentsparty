import type { ReactNode } from 'react';
import { codeToHtml } from 'shiki';

/* Shiki emits `--shiki-light` / `--shiki-dark` custom properties under
 * `defaultColor: false`; the `.shiki` rules shipped by the Fumadocs preset pick
 * the right one per theme, so these panels match the code blocks inside /docs. */
export async function PythonCode({ code }: { code: string }) {
  const html = await codeToHtml(code, {
    lang: 'python',
    themes: { light: 'vitesse-light', dark: 'vitesse-dark' },
    defaultColor: false,
  });
  return (
    <div
      className="agentsparty-code overflow-x-auto py-4 text-[13px] leading-relaxed"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/* Rendered protocols are not a Shiki language: highlight only the message
 * operators (`->` global, `!` send, `?` receive) and leave the rest as text. */
const OPERATOR = /(->|[!?])/g;

export function Protocol({ text }: { text: string }) {
  return (
    <pre className="overflow-x-auto px-4 py-4 font-mono text-[13px] leading-relaxed">
      {text.split(OPERATOR).map((part, index) =>
        index % 2 === 1 ? (
          <span key={index} className="text-fd-primary">
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </pre>
  );
}

export function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <figure className="agentsparty-panel overflow-hidden rounded-xl border bg-fd-card/70 backdrop-blur-sm">
      <figcaption className="flex items-center gap-2 border-b bg-fd-muted/40 px-4 py-2.5">
        <span className="size-2 rounded-full bg-fd-primary/70" aria-hidden />
        <span className="font-mono text-xs text-fd-muted-foreground">
          {title}
        </span>
      </figcaption>
      {children}
    </figure>
  );
}
