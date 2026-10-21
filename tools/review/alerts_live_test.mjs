// Live NWS alert fetch must update the hero alert tile and the top banner, not only the lower block: node tools/review/alerts_live_test.mjs [dist_dir]
// Mocks api.weather.gov: one Flood Warning -> tile reads 1 + banner shows it; empty list -> tile reads 0 and no banner; failed request -> build-time text stays.
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
const pages = [];  // one page with a build-time banner and one without
for (const st of readdirSync(join(DIST, 'river'))) for (const g of readdirSync(join(DIST, 'river', st))) {
  const f = join(DIST, 'river', st, g, 'index.html');
  if (!existsSync(f)) continue;
  const h = readFileSync(f, 'utf8');
  const ban = h.includes('class="abanner"');
  if (h.includes('id="alerts"') && !pages.some(x => x.ban === ban)) pages.push({ url: `/river/${st}/${g}/`, ban });
}
const warn = { features: [{ properties: { event: 'Flood Warning', severity: 'Severe', areaDesc: 'Test County', headline: 'Flood Warning issued', ends: '2030-01-01T00:00:00Z', expires: '2030-01-01T00:00:00Z', geocode: { UGC: ['XXC001'] } } }] };
const b = await chromium.launch();
const bad = [];
for (const pg of pages) {
  for (const mode of ['warn', 'none', 'fail']) {
    const ctx = await b.newContext({ viewport: { width: 390, height: 800 } });
    const page = await ctx.newPage();
    await page.route('https://api.weather.gov/**', r => mode === 'fail' ? r.abort() : r.fulfill({ status: 200, contentType: 'application/geo+json', body: JSON.stringify(mode === 'warn' ? warn : { features: [] }) }));
    await page.goto(BASE + pg.url);
    const before = await page.evaluate(() => ({ ban: !!document.querySelector('a.abanner'), tile: (document.querySelector('.tile.alrt') || {}).textContent || '' }));
    await page.waitForTimeout(900);
    const after = await page.evaluate(() => ({ ban: !!document.querySelector('a.abanner'), bantxt: (document.querySelector('a.abanner') || {}).textContent || '', tile: (document.querySelector('.tile.alrt') || {}).textContent || '' }));
    const pill = await page.evaluate(() => (document.querySelector('.answer .a3') || {}).textContent || '');
    const tag = `${pg.url} [${mode}]`;
    if (mode === 'warn' && !/1 active NWS alert/.test(pill)) bad.push(tag + ': answer pill says "' + pill + '" next to a live warning');
    if (mode === 'none' && !/No active NWS alerts/.test(pill)) bad.push(tag + ': answer pill says "' + pill + '" after a live answer of no alerts');
    if (mode === 'warn' && !(after.ban && /Flood Warning/.test(after.bantxt))) bad.push(tag + ': banner does not show the live warning');
    if (mode === 'warn' && after.tile && !/Flood Warning/.test(after.tile)) bad.push(tag + ': tile does not show the live warning');
    if (mode === 'none' && after.ban) bad.push(tag + ': banner left standing after the live answer said no alerts');
    if (mode === 'none' && after.tile && !/Checked live/.test(after.tile)) bad.push(tag + ': tile not updated by an empty live answer');
    if (mode === 'fail' && (after.ban !== before.ban || after.tile !== before.tile)) bad.push(tag + ': a failed fetch changed the page');
    await ctx.close();
  }
}
await b.close(); srv.close();
if (!pages.length) bad.push('no gauge page with an alerts block found');
if (bad.length) { console.log('ALERT LIVE TEST FAILED:\n' + bad.join('\n')); process.exit(1); }
console.log('alerts live test passes: tile and banner follow the live NWS answer on ' + pages.length + ' pages');
