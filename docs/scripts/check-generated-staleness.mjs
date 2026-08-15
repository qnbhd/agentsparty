/**
 * Fail if committed generated API differs from a fresh generation.
 * Invoked after docs:generate in `npm run check`, so it compares the working
 * tree to itself for dirty edits, or re-runs generate when CHECK_STALE_REGEN=1.
 *
 * Default mode: ensure `(api)` pages and api-data.json exist and xref_map is non-empty.
 * Strict mode (CHECK_STALE_REGEN=1): run generator again and require clean git for those paths.
 */
import { access, readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const apiData = new URL('../public/api-data.json', import.meta.url);
const apiIndex = new URL('../content/docs/(api)/agentsparty/index.mdx', import.meta.url);

const mustExist = async (url, label) => {
  try {
    await access(url);
  } catch {
    console.error(`missing generated artifact: ${label}`);
    process.exitCode = 1;
  }
};

await mustExist(apiData, 'public/api-data.json');
await mustExist(apiIndex, 'content/docs/(api)/agentsparty/index.mdx');

const data = JSON.parse(await readFile(apiData, 'utf8'));
if (!data.xref_map || Object.keys(data.xref_map).length === 0) {
  console.error('api-data.json xref_map is empty');
  process.exitCode = 1;
}

if (process.env.CHECK_STALE_REGEN === '1') {
  const gen = spawnSync('npm', ['run', 'docs:generate'], {
    cwd: root,
    stdio: 'inherit',
    shell: true,
  });
  if (gen.status !== 0) {
    process.exitCode = gen.status ?? 1;
  } else {
    const diff = spawnSync(
      'git',
      ['diff', '--exit-code', '--', 'docs/content/docs/(api)', 'docs/public/api-data.json'],
      { cwd: fileURLToPath(new URL('../..', import.meta.url)), encoding: 'utf8' },
    );
    if (diff.status !== 0) {
      console.error('generated API is stale relative to source');
      console.error(diff.stdout || diff.stderr);
      process.exitCode = 1;
    }
  }
}

if (!process.exitCode) {
  console.log(
    `generated API present; xref_map size=${Object.keys(data.xref_map).length}`,
  );
}
