// Serves a built folder locally so a reviewer can look at pages BEFORE they go live. Usage: node tools/serve.mjs [dist_next] [port]   then open http://localhost:<port>/river/<river>/<place>/
import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', process.argv[2] || 'dist_next');
const port = Number(process.argv[3] || 8123);
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css', '.png': 'image/png', '.xml': 'application/xml', '.txt': 'text/plain' };
http.createServer((q, r) => {
  let p = join(ROOT, decodeURIComponent(q.url.split('?')[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { r.writeHead(404); return r.end('not found'); }
  r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' });
  r.end(readFileSync(p));
}).listen(port, () => console.log('serving ' + ROOT + ' at http://localhost:' + port));
