/**
 * Honest diagram metrics: only top-level STATIC_DIAGRAMS / ANIMATION_DIAGRAMS ids.
 * Nested message/step/event/node ids are ignored.
 */
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const source = await readFile(
  new URL('../components/diagrams/datasets/index.ts', import.meta.url),
  'utf8',
);

function listFromArrayExport(name) {
  const re = new RegExp(`export const ${name}[^=]*=\\s*\\[([\\s\\S]*?)\\];`);
  const m = source.match(re);
  if (!m) return [];
  return m[1]
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s && !s.startsWith('//'));
}

function idOfExport(exportName) {
  const board = source.match(
    new RegExp(`export const ${exportName}\\s*=\\s*board\\(\\s*'([^']+)'`),
  );
  if (board) return board[1];
  const start = source.indexOf(`export const ${exportName}`);
  if (start < 0) return null;
  const chunk = source.slice(start, start + 400);
  const obj = chunk.match(
    /id:\s*'([^']+)',\s*\n\s*kind:\s*'(?:sequence|projection|timeline|board|animation|knowledge|boundary)'/,
  );
  if (obj) return obj[1];
  const anim = chunk.match(/id:\s*'(anim-[^']+)'/);
  return anim?.[1] ?? null;
}

const staticExports = listFromArrayExport('STATIC_DIAGRAMS');
const animExports = listFromArrayExport('ANIMATION_DIAGRAMS');
const staticIds = staticExports.map(idOfExport).filter(Boolean);
const animIds = animExports.map(idOfExport).filter(Boolean);

const docsRoot = new URL('../content/docs/', import.meta.url);

async function filesUnder(dirUrl) {
  const entries = await readdir(dirUrl, { withFileTypes: true });
  const out = [];
  for (const e of entries) {
    const path = join(dirUrl.pathname, e.name);
    if (e.isDirectory()) {
      if (e.name === '(api)') continue;
      out.push(...(await filesUnder(new URL(`file://${path}/`))));
    } else if (e.name.endsWith('.mdx')) {
      out.push(new URL(`file://${path}`));
    }
  }
  return out;
}

let wrapperUses = 0;
for (const file of await filesUnder(docsRoot)) {
  const text = await readFile(file, 'utf8');
  wrapperUses += (text.match(/<(?:Diag|Anim)[A-Z][A-Za-z]+/g) || []).length;
}

const report = {
  static_diagrams: staticIds.length,
  static_ids: staticIds,
  animations: animIds.length,
  animation_ids: animIds,
  mdx_wrapper_uses: wrapperUses,
};

const failures = [];
if (report.static_diagrams < 34) {
  failures.push(`static diagrams ${report.static_diagrams} < 34`);
}
if (report.animations < 9) {
  failures.push(`animations ${report.animations} < 9`);
}
// Nested id inflation guard (single-letter + digit message/event ids, node ids)
if (staticIds.some((id) => /^(n-|msg-|ev-|m\d+$|e\d+$|c\d+$)/.test(id))) {
  failures.push('static registry contains nested-looking ids');
}

console.log(JSON.stringify(report, null, 2));
if (failures.length) {
  console.error(failures.join('\n'));
  process.exitCode = 1;
}
