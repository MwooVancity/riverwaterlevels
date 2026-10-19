// Every gauge page at narrow phone widths: no table wrapper may scroll sideways (fonts differ between machines, so 360 and 340 px stand in for a wider font at 390 px).
// Usage: node tools/review/clip_all.mjs [dist_dir]   (default dist_next). Exit 1 and list the pages when any `.scroll` (except the hourly heatmap) is wider than its box.
import http from 'http';
import { readFileSync, existsSync, statSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
const here = createRequire(import.meta.url);
let pw;
try { pw = here('playwright'); } catch { pw = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json')('playwright'); }
const { chromium } = pw;
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DIST = join(ROOT, process.argv[2] || 'dist_next');
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css', '.png': 'image/png' };
const srv = http.createServer((q, r) => {
  let p = join(DIST, decodeURIComponent(q.url.split('?')[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' });
  r.end(readFileSync(p));
}).listen(0);
const BASE = 'http://localhost:' + srv.address().port;
const pages = [];
for (const a of readdirSync(join(DIST, 'river'))) for (const b of readdirSync(join(DIST, 'river', a))) if (existsSync(join(DIST, 'river', a, b, 'index.html'))) pages.push(`/river/${a}/${b}/`);
const browser = await chromium.launch();
const bad = [];
for (const w of [390, 360, 340]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 1 });
  const pg = await ctx.newPage();
  for (const u of pages) {
    await pg.goto(BASE + u);
    const clip = await pg.evaluate(() => [...document.querySelectorAll('.scroll')].filter(s => s.scrollWidth > s.clientWidth + 2 && !s.querySelector('table.hm')).map(s => (s.closest('section') || { id: 'page' }).id));
    if (clip.length) bad.push(`${w}px ${u}: ${clip.join(', ')}`);
  }
  await ctx.close();
}
await browser.close(); srv.close();
if (bad.length) { console.log('TABLES CUT OFF\n' + bad.join('\n')); process.exit(1); }
console.log('no table scrolls sideways on ' + pages.length + ' gauge pages at 390, 360 and 340 px');
