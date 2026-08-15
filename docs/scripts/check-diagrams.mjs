/**
 * Structural diagram checks + honest registry metrics.
 */
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const docsRoot = new URL('../content/docs/', import.meta.url);
const generated = '(api)';

const FRAME_USE = /<(?:DiagramFrame|Diag[A-Z][A-Za-z]+|Anim[A-Z][A-Za-z]+)\b([^>]*)\/?>/g;

const filesUnder = async (directory) => {
  if (!existsSync(directory)) return [];
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const path = join(directory.pathname ?? directory, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === generated) return [];
        return filesUnder(new URL(`file://${path}/`));
      }
      if (!entry.name.endsWith('.mdx')) return [];
      return [new URL(`file://${path}`)];
    }),
  );
  return nested.flat();
};

const failures = [];
let frames = 0;

for (const file of await filesUnder(docsRoot)) {
  const source = await readFile(file, 'utf8');
  const rel = file.pathname.split('/content/docs/')[1] ?? file.pathname;
  for (const match of source.matchAll(FRAME_USE)) {
    frames += 1;
  }
  for (const m of source.matchAll(/<img\b([^>]*)>/g)) {
    if (!/\balt=/.test(m[1])) failures.push(`${rel}: <img> without alt`);
  }
}

// Delegate count honesty to diagram-metrics.mjs
const metricsScript = fileURLToPath(new URL('./diagram-metrics.mjs', import.meta.url));
const metrics = spawnSync(process.execPath, [metricsScript], {
  encoding: 'utf8',
  env: { ...process.env, DIAGRAM_ENFORCE_THRESHOLDS: '1' },
});
if (metrics.stdout) process.stdout.write(metrics.stdout);
if (metrics.stderr) process.stderr.write(metrics.stderr);
if (metrics.status !== 0) {
  process.exitCode = metrics.status ?? 1;
}

if (failures.length) {
  console.error(failures.join('\n'));
  process.exitCode = 1;
} else if (!process.exitCode) {
  console.log(`diagrams ok: mdx_uses=${frames}`);
}
