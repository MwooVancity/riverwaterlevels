// usage: node culprit.mjs <dist_dir> <width> <path> : hides each block in turn and reports which one makes the page scroll sideways
import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
import { join } from 'path';
import { createRequire } from 'module';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const [dir, width, path] = process.argv.slice(2);
const ROOT = 'C:/Users/mwoo7/Desktop/riverwaterlevels/' + dir;
const srv = http.createServer((q, r) => {
  let p = join(ROOT, decodeURIComponent(q.url.split('?')[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': p.endsWith('.html') ? 'text/html' : 'application/octet-stream' });
  r.end(readFileSync(p));
}).listen(0);
const b = await chromium.launch();
const pg = await (await b.newContext({ viewport: { width: Number(width), height: 900 }, isMobile: Number(width) < 600 })).newPage();
await pg.goto('http://localhost:' + srv.address().port + path, { waitUntil: 'load' });
console.log(JSON.stringify(await pg.evaluate(() => {
  const base = document.documentElement.scrollWidth, W = document.documentElement.clientWidth, hit = [];
  document.querySelectorAll('main *, body > *').forEach((e, i) => {
    if (hit.length > 6 || e.children.length > 40) return;
    const d = e.style.display; e.style.display = 'none';
    if (document.documentElement.scrollWidth <= W) hit.push(e.tagName + '.' + (typeof e.className === 'string' ? e.className : '') + '#' + e.id + ' ' + (e.textContent || '').slice(0, 40));
    e.style.display = d;
  });
  return { base, W, hit };
}), null, 1));
await b.close(); srv.close();
