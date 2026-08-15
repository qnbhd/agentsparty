import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import * as Python from 'fumadocs-python';

const apiDataPath = new URL('../agentsparty.json', import.meta.url);
// `write` drops the leading package segment of each generated path, so the
// package name has to be part of `outDir` for routes to match the hrefs that
// `convert` emits from `baseUrl`.
const apiRoot = new URL('../content/docs/(api)/', import.meta.url);
const packageRoot = new URL('agentsparty/', apiRoot);
const publicRoot = new URL('../public/', import.meta.url);

// Not a basePath-aware URL: these become next/link hrefs, and Next prefixes
// those with `basePath` itself.
const baseUrl = '/docs';

const href = (dottedPath) => `${baseUrl}/${dottedPath.split('.').join('/')}`;

// -- prune: Griffe reports the whole module tree; the site documents the
// -- public surface plus constructors.

const isDocumented = (name) => !name.startsWith('_') || name === '__init__';

const documentedEntries = (members = {}) =>
  Object.fromEntries(Object.entries(members).filter(([name]) => isDocumented(name)));

const mapValues = (members, transform) =>
  Object.fromEntries(Object.entries(members).map(([name, value]) => [name, transform(value)]));

const withoutSelf = (parameters = []) => parameters.filter((parameter) => parameter.name !== 'self');

// `self.x = x` in a constructor reaches Griffe as an attribute with neither a
// type nor a docstring; the constructor parameter already documents it.
const isDescribedAttribute = (attribute) =>
  isDocumented(attribute.name) && (attribute.annotation || attribute.description);

const prunedFunction = (func) => ({ ...func, parameters: withoutSelf(func.parameters) });

const prunedClass = (cls) => ({
  ...cls,
  parameters: withoutSelf(cls.parameters),
  attributes: (cls.attributes ?? []).filter(isDescribedAttribute),
  functions: mapValues(documentedEntries(cls.functions), prunedFunction),
});

const prunedModule = (module) => {
  const modules = mapValues(documentedEntries(module.modules), prunedModule);
  return {
    ...module,
    modules,
    classes: mapValues(documentedEntries(module.classes), prunedClass),
    functions: mapValues(documentedEntries(module.functions), prunedFunction),
    attributes: (module.attributes ?? []).filter(isDescribedAttribute),
  };
};

// -- cross-references

// Resolves `[[agentsparty.protocol.msg]]` in authored MDX (scripts/remark-xref.ts)
// and the reST roles below.
const xrefEntries = (module) => [
  [module.path, href(module.path)],
  ...Object.values(module.classes).flatMap((cls) => [
    [cls.path, href(cls.path)],
    ...Object.values(cls.functions).map((method) => [method.path, href(cls.path)]),
    ...cls.attributes.map((attribute) => [`${cls.path}.${attribute.name}`, href(cls.path)]),
  ]),
  // Module functions and attributes are rendered on the module page itself.
  ...Object.values(module.functions).map((func) => [func.path, href(module.path)]),
  ...module.attributes.map((attribute) => [`${module.path}.${attribute.name}`, href(module.path)]),
  ...Object.values(module.modules).flatMap(xrefEntries),
];

// Docstrings are written in reST; Sphinx roles mean nothing to MDX and would
// render as literal `:class:` noise.
const ROLE = /:(?:class|meth|func|attr|mod|obj|data|exc|ref|term):`~?([^`]+)`/g;

const asMarkdown = (xrefMap) => (_match, target) => {
  const label = target.split('.').at(-1);
  const url = xrefMap[target];
  return url ? `[\`${label}\`](${url})` : `\`${label}\``;
};

// Rewrites every string in the tree except `source`, which is verbatim Python
// shown in a code block and must keep its original docstring.
const withResolvedRoles = (node, replace) => {
  if (typeof node === 'string') return node.replaceAll(ROLE, replace);
  if (Array.isArray(node)) return node.map((item) => withResolvedRoles(item, replace));
  if (node === null || typeof node !== 'object') return node;
  return Object.fromEntries(
    Object.entries(node).map(([key, value]) => [
      key,
      key === 'source' ? value : withResolvedRoles(value, replace),
    ]),
  );
};

// -- generate

const pruned = prunedModule(JSON.parse(await readFile(apiDataPath, 'utf8')));
const xrefMap = Object.fromEntries(xrefEntries(pruned));
const api = withResolvedRoles(pruned, asMarkdown(xrefMap));

await rm(apiRoot, { recursive: true, force: true });
await mkdir(packageRoot, { recursive: true });
await Python.write(Python.convert(api, { baseUrl }), { outDir: packageRoot.pathname });

await writeFile(
  new URL('meta.json', apiRoot),
  `${JSON.stringify({ title: 'API reference', pages: ['agentsparty'] }, null, 2)}\n`,
  'utf8',
);

await mkdir(publicRoot, { recursive: true });
await writeFile(
  new URL('api-data.json', publicRoot),
  `${JSON.stringify({ xref_map: xrefMap }, null, 2)}\n`,
  'utf8',
);
