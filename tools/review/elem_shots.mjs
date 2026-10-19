// usage: node elem_shots.mjs <dist_dir> <prefix> <width> <light|dark> <path> [path...]   (env IDS=a,b,c element ids to capture)
import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
import { join } from 'path';
import { createRequire } from 'module';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const [dir, prefix, width, scheme, ...paths] = process.argv.slice(2);
const ids = (process.env.IDS || '').split(',').filter(Boolean);
const ROOT = 'C:/Users/mwoo7/Desktop/riverwaterlevels/' + dir;
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml' };
const srv = http.createServer((q, r) => {
  let p = join(ROOT, decodeURIComponent(q.url.split('?')[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' });
  r.end(readFileSync(p));
}).listen(0);
const port = srv.address().port;
const b = await chromium.launch();
const w = Number(width);
const out = 'C:/Users/mwoo7/Desktop/riverwaterlevels/shots/';
for (const path of paths) {
  const ctx = await b.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: w < 600 ? 2 : 1, colorScheme: scheme, isMobile: w < 600, hasTouch: w < 600 });
  const pg = await ctx.newPage();
  const errs = [];
  pg.on('console', m => m.type() === 'error' && errs.push(m.text()));
  await pg.goto('http://localhost:' + port + path, { waitUntil: 'networkidle' }).catch(() => {});
  const name = prefix + '_' + path.replace(/[^a-z0-9]+/gi, '_');
  await pg.screenshot({ path: out + name + '_top.png' });
  const over = await pg.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const got = [];
  for (const id of ids) {
    const el = await pg.$('#' + id);
    if (el) { await el.screenshot({ path: out + name + '_' + id + '.png' }); got.push(id); }
  }
  console.log(name, 'errors', errs.length, 'hscroll', over, 'elements', got.join(','));
  await ctx.close();
}
await b.close(); srv.close();
