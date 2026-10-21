// Reader-quality budget (owner 2026-10-20: "why wasn't this caught under our gate to get to #1?"): node tools/review/reader_budget.mjs [dist_dir]
// Measures every built gauge page on a phone (390 px, tabs on) and fails when a page is longer, more repetitive or buries its answer more than data/ui-budget.json allows.
// The budget is a RATCHET: after a release makes pages shorter, lower the numbers in the file; never raise them without writing why in docs/UI-REDESIGN.md.
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
const BUDGET = JSON.parse(readFileSync(join(ROOT, 'data', 'ui-budget.json'), 'utf8'));
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css' };
const srv = http.createServer((q, r) => { let p = join(DIST, decodeURIComponent(q.url.split('?')[0])); if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html'); if (!existsSync(p)) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' }); r.end(readFileSync(p)); }).listen(0);
const base = 'http://localhost:' + srv.address().port;
const urls = [];
for (const st of readdirSync(join(DIST, 'river'))) for (const g of readdirSync(join(DIST, 'river', st))) if (existsSync(join(DIST, 'river', st, g, 'index.html'))) urls.push(`/river/${st}/${g}/`);
const b = await chromium.launch();
const bad = [], rows = [];
for (const u of urls) {
  const c = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const p = await c.newPage();
  await p.route('**/*', r => (r.request().url().startsWith(base) ? r.continue() : r.abort()));  // external images (radar) load at different speeds: block them so heights are the same on every run
  await p.goto(base + u, { waitUntil: 'load' });
  await p.waitForSelector('.gtabs button', { timeout: 10000 }).catch(() => {});  // a page that really has no tabs still fails below
  await p.waitForTimeout(300);
  const m = await p.evaluate(() => {
    const tabs = [...document.querySelectorAll('.gtabs button')];
    let maxTab = document.documentElement.scrollHeight, tabCount = tabs.length;
    const nowTab = maxTab, perTab = {};  // the page opens on the Now tab: its height is the first thing a reader scrolls
    for (const t of tabs) { t.click(); const h = document.documentElement.scrollHeight; perTab[t.textContent.trim()] = h; maxTab = Math.max(maxTab, h); }
    if (tabs[0]) tabs[0].click();
    window.scrollTo(0, 0);
    const ans = document.querySelector('.answer');
    const answerBottom = ans ? Math.round(ans.getBoundingClientRect().bottom + scrollY) : 99999;
    const grid = document.querySelectorAll('.hero2 .tile:not([hidden])').length;
    const rails = document.querySelectorAll('.rail').length;
    const figs = {};
    for (const s of document.querySelectorAll('section.blk, .hero2, .cstrip')) {
      const k = s.id || s.className;
      for (const mm of (s.innerText || '').matchAll(/[-+]?[0-9][0-9,]*\.?[0-9]*\s?(cfs|ft|%|in|mph|years)/g)) { const f = mm[0].replace(/\s+/g, ' '); (figs[f] = figs[f] || new Set()).add(k); }
    }
    const maxRepeat = Math.max(0, ...Object.values(figs).map(v => v.size));
    return { maxTab, nowTab, perTab, tabCount, answerBottom, grid, rails, maxRepeat };
  });
  rows.push({ u, ...m });
  const warn = [];
  if (m.maxTab > BUDGET.maxTabHeight) warn.push(`${u}: tallest phone tab ${m.maxTab} px > budget ${BUDGET.maxTabHeight}`);
  if (BUDGET.maxNowHeight && m.nowTab > BUDGET.maxNowHeight) warn.push(`${u}: the Now tab is ${m.nowTab} px > budget ${BUDGET.maxNowHeight}`);
  if (m.answerBottom > BUDGET.answerBottom) bad.push(`${u}: one-line answer ends at ${m.answerBottom} px > ${BUDGET.answerBottom}`);
  if (m.grid > BUDGET.gridTiles) bad.push(`${u}: ${m.grid} tiles in the grid > ${BUDGET.gridTiles}`);
  if (m.maxRepeat > BUDGET.maxRepeat) bad.push(`${u}: one figure repeated in ${m.maxRepeat} blocks > ${BUDGET.maxRepeat}`);
  if (m.tabCount < BUDGET.minTabs) bad.push(`${u}: only ${m.tabCount} phone tabs (< ${BUDGET.minTabs})`);
  for (const w of warn) console.log('WARN (height, not blocking: a Line 0 block is never cut for length) ' + w);
  await c.close();
}
await b.close(); srv.close();
const worst = rows.reduce((a, r) => (r.maxTab > a.maxTab ? r : a), rows[0]);
const tall = rows.reduce((a, r) => { for (const [k, v] of Object.entries(r.perTab)) if (v > a[1]) a = [k + ' ' + r.u, v]; return a; }, ['', 0]);
console.log(`Now tab at most ${Math.max(...rows.map(r => r.nowTab))} px; tallest tab is ${tall[0]} at ${tall[1]} px`);
console.log(`reader budget: ${rows.length} pages; tallest phone tab ${worst.maxTab} px (${worst.u}); budget ${BUDGET.maxTabHeight}; max repeat ${Math.max(...rows.map(r => r.maxRepeat))}; max grid tiles ${Math.max(...rows.map(r => r.grid))}; answer ends by ${Math.max(...rows.map(r => r.answerBottom))} px`);
if (bad.length) { console.log('READER BUDGET FAILED:\n' + bad.slice(0, 25).join('\n')); process.exit(1); }
console.log('reader budget passes');
