/**
 * Fail when authored MDX contains unresolved [[qualified.name]] xrefs.
 * Also warns on manual links into the (api) route group path.
 */
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const docsRoot = new URL('../content/docs/', import.meta.url);
const apiDataUrl = new URL('../public/api-data.json', import.meta.url);
const generated = '(api)';
const XREF = /\[\[([A-Za-z_][\w.]*)\]\]/g;
const API_LINK = /\]\(\/docs\/agentsparty\//g;

const filesUnder = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const path = join(directory.pathname, entry.name);
      if (entry.isDirectory()) {
        return entry.name === generated ? [] : filesUnder(new URL(`file://${path}/`));
      }
      if (!entry.name.endsWith('.mdx')) return [];
      return [new URL(`file://${path}`)];
    }),
  );
  return nested.flat();
};

const api = JSON.parse(await readFile(apiDataUrl, 'utf8'));
const xrefMap = api.xref_map ?? {};
const failures = [];
const warnings = [];

for (const file of await filesUnder(docsRoot)) {
  const source = await readFile(file, 'utf8');
  const rel = file.pathname.split('/content/docs/')[1] ?? file.pathname;
  for (const match of source.matchAll(XREF)) {
    const name = match[1];
    if (!xrefMap[name]) {
      failures.push(`${rel}: unresolved xref [[${name}]]`);
    }
  }
  if (API_LINK.test(source)) {
    warnings.push(`${rel}: prefer [[xref]] over hard-coded /docs/agentsparty/ links`);
  }
}

if (warnings.length) {
  console.warn(warnings.join('\n'));
}
if (failures.length) {
  console.error(failures.join('\n'));
  process.exitCode = 1;
} else {
  console.log(`checked xrefs; ${Object.keys(xrefMap).length} symbols in map`);
}
