// usage: node overflow.mjs <dist_dir> <width> <path>  : lists elements that stick out past the viewport
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
const pg = await (await b.newContext({ viewport: { width: Number(width), height: 900 } })).newPage();
await pg.goto('http://localhost:' + srv.address().port + path, { waitUntil: 'networkidle' });
const res = await pg.evaluate(() => {
  const W = document.documentElement.clientWidth, out = [];
  document.querySelectorAll('body *').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.right > W + 1 && r.width > 0) {
      let p = e.parentElement, inScroll = false;
      while (p) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') { inScroll = true; break; } p = p.parentElement; }
      if (!inScroll) out.push(e.tagName + '.' + (e.className && e.className.baseVal === undefined ? e.className : '') + '#' + e.id + ' ' + (e.src || '').slice(0, 60) + ' parent=' + e.parentElement.className + ' right=' + Math.round(r.right));
    }
  });
  return { W, sw: document.documentElement.scrollWidth, out: out.slice(0, 12) };
});
console.log(JSON.stringify(res, null, 1));
await b.close(); srv.close();
