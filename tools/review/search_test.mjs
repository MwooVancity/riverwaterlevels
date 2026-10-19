// Header search behaviour: node tools/review/search_test.mjs [dist_dir]   (default dist_next). Typing then Enter must open the first suggestion; no-match must show the water.noaa.gov link.
import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
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
const b = await chromium.launch();
const bad = [];
const cases = [['Pennsylvania', true], ['Atlanta GA', true], ['07010000', true], ['hudson', true], ['Denver', false]];
for (const [q, opens] of cases) {
  for (const start of ['/', '/river/penns-creek/penns-creek/']) {
    const pg = await (await b.newContext({ viewport: { width: 390, height: 800 } })).newPage();
    await pg.goto(BASE + start);
    await pg.fill('#gq', q);
    await pg.waitForTimeout(400);
    const shown = await pg.$$eval('#gr a[href^="/river/"]', as => as.length);
    const before = pg.url();
    await pg.press('#gq', 'Enter');
    await pg.waitForTimeout(600);
    const moved = pg.url() !== before || start !== '/river/penns-creek/penns-creek/' ? pg.url() !== before : true;  // on a gauge page the first suggestion may be the page itself
    const nomatch = await pg.$eval('#gr', e => e.textContent).catch(() => '');
    if (opens && (!shown || !moved)) bad.push(`${q} on ${start}: ${shown} suggestions, Enter moved=${moved}`);
    if (!opens && (shown || !/water\.noaa\.gov/.test(await pg.$eval('#gr', e => e.innerHTML)))) bad.push(`${q} on ${start}: expected the no-match message with the water.noaa.gov link`);
  }
}
await b.close(); srv.close();
if (bad.length) { console.log('SEARCH FAILED\n' + bad.join('\n')); process.exit(1); }
console.log('search test passes: ' + cases.length + ' queries on 2 pages');
