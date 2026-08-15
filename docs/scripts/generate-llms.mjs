/**
 * Structured llms corpora: index by IA section, full authored body,
 * API index and verified example files.
 */
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { execSync } from 'node:child_process';

const docsRoot = new URL('../content/docs/', import.meta.url);
const outputRoot = new URL('../public/', import.meta.url);
const repoRoot = new URL('../../', import.meta.url);
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

const SECTIONS = [
  ['Start', 'start'],
  ['Core Concepts', 'concepts'],
  ['Tutorials', 'tutorials'],
  ['Reference', 'reference'],
];

const filesUnder = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const path = join(directory.pathname, entry.name);
      if (entry.isDirectory()) return filesUnder(new URL(`file://${path}/`));
      return entry.name.endsWith('.mdx') ? [new URL(`file://${path}`)] : [];
    }),
  );
  return nested.flat();
};

const frontmatter = (source) => {
  const m = source.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return {};
  const data = {};
  for (const line of m[1].split('\n')) {
    const kv = line.match(/^(\w+):\s*(.+)$/);
    if (kv) data[kv[1]] = kv[2].trim();
  }
  return data;
};

const routeOf = (file) => {
  const rel = file.pathname.split('/content/docs/')[1].replace(/\.mdx$/, '');
  return `${basePath}/docs/${rel}`.replace('/(api)', '');
};

const markdownText = (page) => {
  // remove frontmatter before exposing the page as Markdown:
  const body = page.source.replace(/^---\n[\s\S]*?\n---\s*/, '');
  return `# ${page.title} (${page.route})\n\n${body}`;
};

const metaOrder = async (dirUrl) => {
  try {
    const meta = JSON.parse(await readFile(new URL('meta.json', dirUrl), 'utf8'));
    return meta.pages ?? [];
  } catch {
    return [];
  }
};

const allFiles = await filesUnder(docsRoot);
const authored = [];
const apiPages = [];

for (const file of allFiles) {
  const rel = file.pathname.split('/content/docs/')[1];
  const source = await readFile(file, 'utf8');
  const fm = frontmatter(source);
  const page = {
    file,
    rel,
    route: routeOf(file),
    title: fm.title ?? rel,
    source,
    isApi: rel.startsWith('(api)/'),
  };
  if (page.isApi) apiPages.push(page);
  else authored.push(page);
}

const markdownPages = [...authored, ...apiPages];
await Promise.all(
  markdownPages.map(async (page) => {
    // resolve the public route, including the base-path boundary:
    const route = basePath && page.route.startsWith(basePath)
      ? page.route.slice(basePath.length)
      : page.route;
    const routes = [route];
    if (route.endsWith('/index')) routes.push(route.slice(0, -'/index'.length));
    // write both source-compatible and canonical index URLs:
    await Promise.all(
      routes.map(async (markdownRoute) => {
        const output = new URL(`${markdownRoute.slice(1)}.md`, outputRoot);
        await mkdir(new URL('.', output), { recursive: true });
        await writeFile(output, `${markdownText(page)}\n`, 'utf8');
      }),
    );
  }),
);

const byDir = (prefix) =>
  authored
    .filter((p) => p.rel === `${prefix}.mdx` || p.rel.startsWith(`${prefix}/`))
    .sort((a, b) => a.rel.localeCompare(b.rel));

let version = '0.1.0';
try {
  version = execSync('uv run --project .. python -c "from importlib.metadata import version; print(version(\'agentsparty\'))"', {
    cwd: new URL('..', import.meta.url).pathname,
    encoding: 'utf8',
  }).trim();
} catch {
  /* keep default */
}

let commit = 'unknown';
try {
  commit = execSync('git rev-parse --short HEAD', {
    cwd: repoRoot.pathname,
    encoding: 'utf8',
  }).trim();
} catch {
  /* keep default */
}

const generatedAt = new Date().toISOString().slice(0, 10);
const header = (name) =>
  `# agentsparty\n> Protocol-first orchestration for AI agents\n\nGenerated: ${generatedAt} · package ${version} · commit ${commit}\n\n`;

// llms.txt structured index
const indexParts = [header('llms'), '## Documentation map\n'];
for (const [title, dir] of SECTIONS) {
  indexParts.push(`## ${title}\n`);
  for (const page of byDir(dir)) {
    if (page.rel.endsWith('/meta.json')) continue;
    indexParts.push(`- [${page.title}](${page.route})`);
  }
  indexParts.push('');
}
// index.mdx
const home = authored.find((p) => p.rel === 'index.mdx');
if (home) {
  indexParts.splice(2, 0, `## Home\n- [${home.title}](${home.route})\n`);
}
indexParts.push(
  '## API reference\n- Generated symbols are documented on the site under /docs/agentsparty.\n',
);
await writeFile(new URL('llms.txt', outputRoot), `${indexParts.join('\n')}\n`, 'utf8');

// llms-full.txt authored only
const full = [
  header('llms-full'),
  ...authored
    .sort((a, b) => a.rel.localeCompare(b.rel))
    .map((p) => `\n\n<!-- ${p.route} -->\n\n# ${p.title}\n\n${p.source}`),
].join('');
await writeFile(new URL('llms-full.txt', outputRoot), `${full}\n`, 'utf8');

// llms-examples.txt: the verified/online split, mirroring the catalogue page
const examplesDir = new URL('../../examples/', import.meta.url);
const walkExamples = async (dir, bucket) => {
  let entries = [];
  try {
    entries = await readdir(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    if (entry.isDirectory() && entry.name !== '__pycache__') {
      await walkExamples(new URL(`${entry.name}/`, dir), bucket);
    } else if (entry.name.endsWith('.py')) {
      const rel = join(dir.pathname, entry.name).split('/examples/')[1];
      bucket.push(`- examples/${rel} · \`uv run python examples/${rel}\``);
    }
  }
};
const offline = [];
const online = [];
await walkExamples(new URL('offline/', examplesDir), offline);
await walkExamples(new URL('online/', examplesDir), online);
try {
  const entries = await readdir(examplesDir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isFile() && entry.name.endsWith('.py')) {
      online.push(
        `- examples/${entry.name} · \`uv run python examples/${entry.name}\``,
      );
    }
  }
} catch {
  /* no root examples */
}
const examplesTxt = [
  header('llms-examples'),
  '## Verified in CI (offline)\n',
  ...offline.sort(),
  '\n## Showcase (online, not verified in CI)\n',
  ...online.sort(),
  '\n## Tutorial files\n',
  '- docs/examples/canonical/offline_quickstart.py',
  '- docs/examples/tutorial/01_approval_workflow.py',
  '- docs/examples/tutorial/02_typed_payloads.py',
  '- docs/examples/tutorial/03_human_review.py',
  '- docs/examples/tutorial/04_durable_session.py',
  '- docs/examples/tutorial/05_observable_session.py',
].join('\n');
await writeFile(new URL('llms-examples.txt', outputRoot), `${examplesTxt}\n`, 'utf8');

console.log(
  `llms: authored=${authored.length} api=${apiPages.length} offline=${offline.length} online=${online.length}`,
);
