'use client';

import { Check, Copy } from 'lucide-react';
import { useCopyButton } from '@fumadocs/base-ui/utils/use-copy-button';

/* The two installers on the landing page, each a button that copies itself.
 *
 * Both are offered because the reader already has one of them and should not
 * have to translate the other. Deliberately NOT syntax-highlighted: a shell
 * line this short carries two tokens, so colouring them adds noise without
 * information, and the hero reserves its brightest lime for the one call to
 * action. The installer name is set apart by weight instead, since that is the
 * only part of the two lines that differs and the only part worth scanning.
 */

const COMMANDS = [
  { tool: 'uv', rest: 'add agentsparty' },
  { tool: 'pip', rest: 'install agentsparty' },
] as const;

export function InstallRail() {
  return (
    <div className="agentsparty-hero-install">
      {COMMANDS.map((command) => (
        <InstallCommand key={command.tool} {...command} />
      ))}
    </div>
  );
}

function InstallCommand({ tool, rest }: { tool: string; rest: string }) {
  const command = `${tool} ${rest}`;
  const [copied, onClick] = useCopyButton(() =>
    navigator.clipboard.writeText(command),
  );

  return (
    <button
      type="button"
      className="agentsparty-hero-install-command"
      onClick={onClick}
      // The visible text is the command; the label says what pressing does.
      aria-label={`Copy ${command}`}
    >
      <code>
        <span className="agentsparty-hero-install-tool">{tool}</span> {rest}
      </code>
      {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
      {/* Announced on copy, because the icon swap is the only other signal. */}
      <span className="sr-only" aria-live="polite">
        {copied ? 'Copied' : ''}
      </span>
    </button>
  );
}
