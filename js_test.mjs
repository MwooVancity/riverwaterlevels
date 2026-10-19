// Tests the page JavaScript against stubbed USGS responses: CSV download (ok, sorted, complete), CSV with a 429 (must not download a partial file), live refresh note.
import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
import { join } from 'path';
import { createRequire } from 'module';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const ROOT = 'C:/Users/mwoo7/Desktop/riverwaterlevels/dist';
const srv = http.createServer((q, r) => {
  let p = join(ROOT, decodeURIComponent(q.url.split('?')[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': p.endsWith('.html') ? 'text/html' : 'application/octet-stream' });
  r.end(readFileSync(p));
}).listen(0);
const url = 'http://localhost:' + srv.address().port + '/river/missouri-river-mo/kansas-city/';
const b = await chromium.launch();
const feat = (code, t, v) => ({ type: 'Feature', properties: { time: t, parameter_code: code, value: String(v), unit_of_measure: code === '00060' ? 'ft3/s' : 'ft' } });
let fails = 0;
const ok = (n, c) => { console.log(c ? 'PASS' : 'FAIL', n); if (!c) fails++; };

// 1. CSV ok: stubbed responses out of order; file must be sorted by time with both parameters
{
  const ctx = await b.newContext({ acceptDownloads: true });
  const pg = await ctx.newPage();
  await pg.route('**/collections/continuous/items**', (route) => {
    const u = route.request().url();
    const code = u.includes('parameter_code=00060') ? '00060' : '00065';
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ features: [feat(code, '2026-10-16T02:00:00Z', 2), feat(code, '2026-10-16T01:00:00Z', 1)] }) });
  });
  await pg.route('**/latest-continuous/**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ features: [] }) }));
  await pg.goto(url, { waitUntil: 'networkidle' });
  const [dl] = await Promise.all([pg.waitForEvent('download'), pg.click('#csvbtn')]);
  const txt = readFileSync(await dl.path(), 'utf8').trim().split('\n');
  ok('csv header', txt[0] === 'time_utc,parameter_code,value,unit');
  ok('csv has 4 data rows (both parameters)', txt.length === 5);
  ok('csv sorted by time', txt.slice(1).map(x => x.split(',')[0]).join() === [...txt.slice(1).map(x => x.split(',')[0])].sort().join());
  await ctx.close();
}
// 2. CSV with 429 for stage: no partial download, clear message
{
  const ctx = await b.newContext({ acceptDownloads: true });
  const pg = await ctx.newPage();
  await pg.route('**/collections/continuous/items**', (route) => {
    const u = route.request().url();
    if (u.includes('parameter_code=00065')) return route.fulfill({ status: 429, body: 'slow down' });
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ features: [feat('00060', '2026-10-16T01:00:00Z', 1)] }) });
  });
  await pg.route('**/latest-continuous/**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ features: [] }) }));
  await pg.goto(url, { waitUntil: 'networkidle' });
  let downloaded = false;
  pg.on('download', () => { downloaded = true; });
  await pg.click('#csvbtn');
  await pg.waitForFunction(() => /failed/i.test(document.querySelector('#csvbtn').textContent), null, { timeout: 15000 }).catch(() => {});
  ok('429 shows failure text', /failed/i.test(await pg.textContent('#csvbtn')));
  ok('429 gives no partial file', !downloaded);
  await ctx.close();
}
// 3. live refresh with a newer flow: the percentile and change captions say they are as of the build
{
  const ctx = await b.newContext();
  const pg = await ctx.newPage();
  const now = new Date().toISOString();
  await pg.route('**/latest-continuous/**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ features: [feat('00060', now, 150000), feat('00065', now, 27.5)] }) }));
  await pg.goto(url, { waitUntil: 'networkidle' });
  await pg.waitForTimeout(800);
  ok('live flow updated', (await pg.textContent('[data-live="flow"]')).includes('150,000'));
  ok('percentile caption notes build time', /as of/.test(await pg.textContent('#pcap')));
  await ctx.close();
}
// 4. a folded group opens when its anchor is used (jump link, permalink, shared URL) and when printing
{
  const ctx = await b.newContext();
  const pg = await ctx.newPage();
  await pg.goto(url, { waitUntil: 'networkidle' });
  const closed = await pg.evaluate(() => { const d = document.querySelector('details.fold'); return !!d && !d.open; });
  ok('flood record starts folded', closed);
  await pg.goto(url + '#annual_peaks', { waitUntil: 'networkidle' });
  ok('anchor to a folded block opens it', await pg.evaluate(() => { const e = document.getElementById('annual_peaks'); return !!e && e.closest('details').open && e.getBoundingClientRect().height > 50; }));
  await ctx.close();
}
// 5. "Your range": the reader's own low and high flow, saved in the browser, compared with the latest flow; bad input is refused; clear removes it
{
  const ctx = await b.newContext();
  const pg = await ctx.newPage();
  await pg.goto(url, { waitUntil: 'networkidle' });
  ok('range tile appears when storage works', await pg.evaluate(() => !document.querySelector('.tile.mine').hidden));
  await pg.click('#mybtn');
  await pg.fill('#mylo', '2000'); await pg.fill('#myhi', '1000'); await pg.click('#myform button[type=submit]');
  ok('low above high is refused', /Enter the lowest flow/.test(await pg.textContent('#mysub')));
  await pg.fill('#mylo', '1000'); await pg.fill('#myhi', '2000'); await pg.click('#myform button[type=submit]');
  ok('flow far above the range says so', (await pg.textContent('#mylv')) === 'Above your range');
  await pg.reload({ waitUntil: 'networkidle' });
  ok('range survives a reload', (await pg.textContent('#mylv')) === 'Above your range');
  await pg.click('#mybtn'); await pg.fill('#mylo', '50000'); await pg.fill('#myhi', '90000'); await pg.click('#myform button[type=submit]');
  ok('flow inside the range says so', (await pg.textContent('#mylv')) === 'In your range');
  await pg.click('#mybtn'); await pg.click('#myform .clr');
  ok('clear removes the range', (await pg.textContent('#mylv')) === 'Set your range');
  await ctx.close();
}
await b.close();
srv.close();
console.log(fails ? fails + ' FAILED' : 'ALL JS TESTS PASS');
process.exit(fails ? 1 : 0);
