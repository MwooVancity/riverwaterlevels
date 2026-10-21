// A newer live USGS reading must not leave build-time trend and comparison pills standing next to it: node tools/review/live_flow_test.mjs [dist_dir]
// Mocks the USGS latest-continuous call with a flow of 5,000 cfs timestamped now: the flow tile must show it and the two build-time pills (trend, comparison) must be hidden; a failed call leaves both pills visible.
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
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css' };
const srv = http.createServer((q, r) => { let p = join(DIST, decodeURIComponent(q.url.split('?')[0])); if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html'); if (!existsSync(p)) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' }); r.end(readFileSync(p)); }).listen(0);
const BASE = 'http://localhost:' + srv.address().port;
const urls = [];
for (const st of readdirSync(join(DIST, 'river'))) for (const g of readdirSync(join(DIST, 'river', st))) if (existsSync(join(DIST, 'river', st, g, 'index.html'))) urls.push(`/river/${st}/${g}/`);
const b = await chromium.launch();
const bad = [];
for (const u of urls) {
  for (const mode of ['newer', 'fail']) {
    const ctx = await b.newContext({ viewport: { width: 390, height: 800 } });
    const page = await ctx.newPage();
    await page.route('https://api.waterdata.usgs.gov/**', r => mode === 'fail' ? r.abort() : r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ features: [{ properties: { parameter_code: '00060', value: '5000', time: new Date().toISOString() } }] }) }));
    await page.route('https://api.weather.gov/**', r => r.abort());
    await page.goto(BASE + u);
    await page.waitForTimeout(900);
    const s = await page.evaluate(() => ({ a1: (document.querySelector('.answer .a1') || {}).textContent || '', a2: (document.querySelector('.answer .a2') || {}).textContent || '', flow: (document.querySelector('[data-live="flow"]') || {}).textContent || '' }));
    if (mode === 'newer' && s.flow && !/5,000/.test(s.flow)) bad.push(`${u}: live flow not applied (${s.flow})`);
    if (mode === 'newer' && s.flow && (!/ \(as of /.test(s.a1) || !/ \(as of /.test(s.a2))) bad.push(`${u}: trend/comparison pills not dated next to a newer live flow (${s.a1} | ${s.a2})`);
    if (mode === 'fail' && (!s.a1 || !s.a2 || / \(as of /.test(s.a1 + s.a2))) bad.push(`${u}: a failed live call changed the pills (${s.a1} | ${s.a2})`);
    await ctx.close();
  }
}
await b.close(); srv.close();
if (bad.length) { console.log('LIVE FLOW TEST FAILED:\n' + bad.slice(0, 20).join('\n')); process.exit(1); }
console.log('live flow test passes: pills hidden when a newer live reading arrives, kept when the call fails (' + urls.length + ' pages)');
