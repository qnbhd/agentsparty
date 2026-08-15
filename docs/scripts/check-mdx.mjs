import { readdir, readFile } from 'node:fs/promises';

const root = new URL('../content/docs/', import.meta.url);
// The generated API pages are real MDX: they carry `<PyFunction>` components
// and JSX attributes, so the prose rules below do not apply to them.
const generated = '(api)';
// Self-closing PascalCase component tags (diagrams, ExampleSource, …).
const jsxComponent = /^\s*<\/?[A-Z][A-Za-z0-9.]*(\s[^>]*)?\s*\/?>\s*$/;
const statuses = new Set(['draft', 'review', 'stable', 'generated']);
const failures = [];

const filesUnder = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(entries.map(async (entry) => {
    const path = new URL(`${entry.name}${entry.isDirectory() ? '/' : ''}`, directory);
    if (entry.isDirectory()) return entry.name === generated ? [] : filesUnder(path);
    return entry.name.endsWith('.mdx') ? [path] : [];
  }));
  return files.flat();
};

for (const file of await filesUnder(root)) {
  const source = await readFile(file, 'utf8');
  const lines = source.split('\n');
  const status = source.match(/^status:\s*([^\s]+)\s*$/m)?.[1];
  if (!status || !statuses.has(status)) {
    failures.push(`${file.pathname}: missing or invalid status (expected draft/review/stable/generated)`);
  }
  const isStyleGuide = file.pathname.endsWith('/contribute/documentation-style.mdx');
  if (status === 'stable' && !isStyleGuide && /```python\s+pseudocode|when available|Probe Routine API|names per public API/.test(source)) {
    failures.push(`${file.pathname}: stable page contains a draft-only API example or claim`);
  }
  if (status === 'stable' && /```python[^`]*_answers/s.test(source)) {
    failures.push(`${file.pathname}: stable page teaches private model state`);
  }
  let fenced = false;
  let openLine = 0;
  for (const [index, line] of lines.entries()) {
    if (line.startsWith('```') || line.startsWith('~~~')) {
      if (!fenced) {
        fenced = true;
        openLine = index + 1;
      } else {
        fenced = false;
      }
      continue;
    }
    if (fenced) continue;
    if (jsxComponent.test(line)) continue;
    if (/(?<!\\)[{}]|(?<![\\\w])</.test(line)) {
      failures.push(`${file.pathname}:${index + 1}: unescaped MDX metacharacter`);
    }
  }
  if (fenced) {
    failures.push(`${file.pathname}:${openLine}: unclosed code fence`);
  }
}

if (failures.length > 0) {
  console.error(failures.join('\n'));
  process.exitCode = 1;
} else {
  console.log('mdx metacharacter and fence check ok');
}
