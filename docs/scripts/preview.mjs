/**
 * Serve the exported site from `out/`.
 *
 * The export is a plain directory tree, but Next writes root-absolute asset
 * URLs (`/_next/...`), so opening `out/index.html` over `file://` resolves
 * them against the filesystem root and loads nothing. Any static host fixes
 * that; this is the same thing without installing one.
 */
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, join, normalize } from 'node:path';

const root = new URL('../out/', import.meta.url).pathname;
const port = Number(process.env.PORT ?? 4173);

const TYPES = {
  '.css': 'text/css',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.woff2': 'font/woff2',
};

// `trailingSlash` puts every route in its own directory; a bare route name is
// still worth answering, the way a static host would.
const candidates = (pathname) => {
  const path = join(root, normalize(pathname).replace(/^(\.\.[/\\])+/, ''));
  return [path, join(path, 'index.html'), `${path}.html`];
};

const firstFile = async (paths) => {
  for (const path of paths) {
    const found = await stat(path).catch(() => null);
    if (found?.isFile()) return path;
  }
  return null;
};

createServer(async (request, response) => {
  const { pathname } = new URL(request.url, 'http://localhost');
  const found = await firstFile(candidates(decodeURIComponent(pathname)));
  const file = found ?? (await firstFile([join(root, '404.html')]));
  if (!file) {
    response.writeHead(404, { 'content-type': TYPES['.html'] });
    return response.end('Not found');
  }
  response.writeHead(found ? 200 : 404, {
    'content-type': TYPES[extname(file)] ?? 'application/octet-stream',
  });
  createReadStream(file).pipe(response);
}).listen(port, () => {
  console.log(`agentsparty docs → http://127.0.0.1:${port}`);
});
