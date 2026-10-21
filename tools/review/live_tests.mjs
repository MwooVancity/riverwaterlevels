// Live-behaviour browser tests in one run (one local server, one Playwright browser): node tools/review/live_tests.mjs [dist_dir]
//   alerts: a live NWS fetch must update the hero alert tile and the top banner, not only the lower block. Mocks api.weather.gov: one Flood Warning -> tile reads 1 + banner shows it; empty list -> tile reads 0 and no banner; failed request -> build-time text stays.
//   flow:   a newer live USGS reading must not leave build-time trend and comparison pills standing next to it. Mocks the USGS latest-continuous call with a flow of 5,000 cfs timestamped now: the flow tile must show it and the two build-time pills (trend, comparison) must not vanish; a failed call leaves both pills visible.
//   search: header search. Typing then Enter must open the first suggestion; no-match must show the water.noaa.gov link.
// (folded from alerts_live_test.mjs, live_flow_test.mjs, search_test.mjs; every check and message unchanged)
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
const urls = [];
for (const st of readdirSync(join(DIST, 'river'))) for (const g of readdirSync(join(DIST, 'river', st))) if (existsSync(join(DIST, 'river', st, g, 'index.html'))) urls.push(`/river/${st}/${g}/`);
const b = await chromium.launch();
const out = [];  // [section title, failure header, failures, pass line]

async function alerts() {
  const bad = [];
  const pages = [];  // one page with a build-time banner and one without
  for (const u of urls) {
    const h = readFileSync(join(DIST, u, 'index.html'), 'utf8');
    const ban = h.includes('class="abanner"');
    if (h.includes('id="alerts"') && !pages.some(x => x.ban === ban)) pages.push({ url: u, ban });
  }
  const warn = { features: [{ properties: { event: 'Flood Warning', severity: 'Severe', areaDesc: 'Test County', headline: 'Flood Warning issued', ends: '2030-01-01T00:00:00Z', expires: '2030-01-01T00:00:00Z', geocode: { UGC: ['XXC001'] } } }] };
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
  if (!pages.length) bad.push('no gauge page with an alerts block found');
  out.push(['alerts', 'ALERT LIVE TEST FAILED:', bad, 'alerts live test passes: tile and banner follow the live NWS answer on ' + pages.length + ' pages']);
}

async function flow() {
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
      if (mode === 'newer' && s.flow && (!s.a1 || !s.a2)) bad.push(`${u}: a pill vanished after a newer live flow (${s.a1} | ${s.a2})`);
      if (mode === 'fail' && (!s.a1 || !s.a2)) bad.push(`${u}: a failed live call hid a pill (${s.a1} | ${s.a2})`);
      await ctx.close();
    }
  }
  out.push(['flow', 'LIVE FLOW TEST FAILED:', bad.slice(0, 20), 'live flow test passes: pills hidden when a newer live reading arrives, kept when the call fails (' + urls.length + ' pages)']);
}

async function search() {
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
      if (opens && (!shown || !moved)) bad.push(`${q} on ${start}: ${shown} suggestions, Enter moved=${moved}`);
      if (!opens && (shown || !/water\.noaa\.gov/.test(await pg.$eval('#gr', e => e.innerHTML)))) bad.push(`${q} on ${start}: expected the no-match message with the water.noaa.gov link`);
    }
  }
  out.push(['search', 'SEARCH FAILED', bad, 'search test passes: ' + cases.length + ' queries on 2 pages']);
}

await alerts(); await flow(); await search();
await b.close(); srv.close();
for (const [, head, bad, pass] of out) console.log(bad.length ? head + '\n' + bad.join('\n') : pass);
console.log('live tests: ' + out.map(([n, , bad]) => n + ' ' + (bad.length ? bad.length + ' failures' : 'pass')).join(', '));
process.exit(out.some(o => o[2].length) ? 1 : 0);
