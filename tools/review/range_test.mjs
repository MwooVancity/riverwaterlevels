// the range tile on the BUILT pages: typing "5,000" and "12,000" with commas must save, and a live flow refresh while the form is open must NOT close it
import { createRequire } from 'module';
import http from 'http';
import { readFileSync, existsSync, statSync } from 'fs';
import { join } from 'path';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const DIST = 'C:/Users/mwoo7/Desktop/riverwaterlevels/dist_next';
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css' };
const srv = http.createServer((q, r) => { let p = join(DIST, decodeURIComponent(q.url.split('?')[0])); if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html'); if (!existsSync(p)) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' }); r.end(readFileSync(p)); }).listen(0);
const base = process.env.BASE || ('http://localhost:' + srv.address().port);
const b = await chromium.launch();
let bad = [];
for (const [name, vp, mobile] of [['desktop', { width: 1280, height: 900 }, false], ['phone', { width: 390, height: 844 }, true]]) {
  const c = await b.newContext({ viewport: vp, hasTouch: mobile, isMobile: mobile });
  const p = await c.newPage();
  await p.goto(base + '/river/hudson-river/green-island/');
  await p.click('#mybtn');
  await p.fill('#mylo', '5,000');
  // simulate the live refresh changing the flow number while the form is open
  await p.evaluate(() => { const n = document.querySelector('[data-live="flow"]'); n.textContent = n.textContent === '1' ? '2' : '1,234'; });
  await p.waitForTimeout(300);
  const open = await p.evaluate(() => !document.getElementById('myform').hidden);
  const kept = await p.inputValue('#mylo');
  if (!open) bad.push(name + ': form closed by a live refresh');
  if (kept !== '5,000') bad.push(name + ': typed value lost (' + kept + ')');
  await p.fill('#myhi', '12,000');
  await p.click('#myform button[type=submit]');
  const sub = await p.evaluate(() => document.getElementById('mysub').textContent);
  if (!/5,000 to 12,000/.test(sub)) bad.push(name + ': comma numbers did not save: ' + sub);
  for (const [lo, hi] of [['1e3', '5000'], ['5.5.5', '9'], ['-4', '9'], ['9', '3'], ['', '']]) {  // junk is refused with a message, never saved
    await p.click('#myform .clr').catch(() => {});
    await p.click('#mybtn');
    await p.fill('#mylo', lo); await p.fill('#myhi', hi);
    await p.click('#myform button[type=submit]');
    const m = await p.evaluate(() => document.getElementById('mysub').textContent);
    if (!/Enter the lowest flow/.test(m)) bad.push(name + ': junk range ' + lo + ' / ' + hi + ' was not refused: ' + m);
  }
  await c.close();
}
await b.close(); srv.close();
if (bad.length) { console.log('RANGE TEST FAILED\n' + bad.join('\n')); process.exit(1); }
console.log('range test passes: commas accepted, a live refresh does not close the form');
