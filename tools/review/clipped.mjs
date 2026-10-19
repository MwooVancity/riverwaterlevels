// node clipped.mjs <dist_dir> <width> <path...> : lists tables whose scroll box is wider than the screen (columns cut off on a phone)
import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
import { join } from 'path';
import { createRequire } from 'module';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const [dir, width, ...paths] = process.argv.slice(2);
const ROOT = 'C:/Users/mwoo7/Desktop/riverwaterlevels/' + dir;
const srv = http.createServer((q, r) => {
  let p = join(ROOT, decodeURIComponent(q.url.split('?')[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': p.endsWith('.html') ? 'text/html' : 'application/octet-stream' });
  r.end(readFileSync(p));
}).listen(0);
const b = await chromium.launch();
const agg = {};
for (const path of paths) {
  const pg = await (await b.newContext({ viewport: { width: Number(width), height: 900 }, isMobile: true })).newPage();
  await pg.goto('http://localhost:' + srv.address().port + path, { waitUntil: 'load' });
  const res = await pg.evaluate(() => [...document.querySelectorAll('.scroll')].filter(s => s.scrollWidth > s.clientWidth + 2 && !s.querySelector('table.hm')).map(s => { const sec = s.closest('section'); return (sec ? sec.id : 'page') + ' (' + (s.scrollWidth - s.clientWidth) + 'px hidden): ' + [...s.querySelectorAll('th')].map(t => t.textContent.trim()).join(' | ').slice(0, 90); }));
  for (const r of res) agg[r] = (agg[r] || 0) + 1;
  await pg.close();
}
console.log(Object.entries(agg).map(([k, v]) => v + 'x ' + k).join('\n') || 'no clipped tables');
await b.close(); srv.close();
