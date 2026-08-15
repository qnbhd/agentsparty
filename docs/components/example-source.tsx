import { readFileSync } from 'node:fs';
import { join, normalize, relative, resolve, sep } from 'node:path';

const REPO_ROOT = resolve(process.cwd(), '..');

export type ExampleSourceProps = {
  /** Repository-relative path, e.g. ``examples/offline/toolbox.py``. */
  path: string;
  /** Optional region between ``# docs: start name`` / ``# docs: end name``. */
  region?: string;
  collapse?: boolean;
};

function assertInsideRepo(abs: string): void {
  const rel = relative(REPO_ROOT, abs);
  if (rel.startsWith('..') || rel.includes(`..${sep}`) || normalize(abs) !== abs && abs.includes('..')) {
    // path traversal
  }
  if (!abs.startsWith(REPO_ROOT) || rel.startsWith('..')) {
    throw new Error(`ExampleSource path escapes repository: ${abs}`);
  }
}

function extractRegion(source: string, region: string): string {
  const start = `# docs: start ${region}`;
  const end = `# docs: end ${region}`;
  const startIdx = source.indexOf(start);
  const endIdx = source.indexOf(end);
  if (startIdx < 0 || endIdx < 0) {
    throw new Error(`region ${JSON.stringify(region)} not found`);
  }
  if (source.indexOf(start, startIdx + 1) >= 0 || source.indexOf(end, endIdx + 1) >= 0) {
    throw new Error(`region ${region} appears more than once`);
  }
  return source.slice(startIdx + start.length, endIdx).replace(/^\n/, '');
}

/**
 * Include a repository example file (or named region) at build time.
 * Source text is present in the static HTML / llms corpus, not only client JS.
 */
export function ExampleSource({ path, region, collapse = true }: ExampleSourceProps) {
  if (path.includes('..') || path.startsWith('/') || path.includes('\0')) {
    throw new Error(`invalid ExampleSource path: ${path}`);
  }
  const abs = resolve(REPO_ROOT, path);
  assertInsideRepo(abs);
  let source = readFileSync(abs, 'utf8');
  if (region) {
    source = extractRegion(source, region);
  }
  const sourceUrl = `https://github.com/qnbhd/agentsparty/blob/master/${path}`;
  const body = (
    <>
      <p style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
        <code>{path}</code>
        {region ? (
          <>
            {' '}
            · region <code>{region}</code>
          </>
        ) : null}
        {' · '}
        <a href={sourceUrl}>source</a>
      </p>
      <pre>
        <code className="language-python">{source}</code>
      </pre>
    </>
  );
  if (!collapse) return <div className="my-4">{body}</div>;
  return (
    <details className="my-4 rounded-lg border bg-fd-card p-3">
      <summary className="cursor-pointer text-sm font-medium">
        Full source · {path}
        {region ? ` (${region})` : ''}
      </summary>
      {body}
    </details>
  );
}
