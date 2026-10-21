// Forbes-editor gate (owner 2026-10-20: "add the Forbes editor gate"): node tools/review/editor_gate.mjs [dist_dir]
// Also runs (folded from clip_all.mjs and reader_budget.mjs): tables never scroll sideways at 390/360/340 px, and the reader budget (tab heights, answer position, grid tiles, repeated figures, tab count) from data/ui-budget.json.
// Measures what a demanding editor flags on the first phone screen of every gauge page and fails when a page is worse than data/ui-budget.json "editor".
//   repeat      most times one timestamp or one line of text is repeated across the top block (answer pills, tiles, swipe strip)
//   trendRepeat most times the trend word (Rising/Falling/Steady) is written in the top block
//   tileChars   longest swipe-strip tile (characters): a tile that runs to six lines reads as small print
//   firstWords  words visible in the first 844 px of the phone screen
//   unitShown   the unit "cfs" is spelled out in visible text on the page (a hover title does not work on a phone)
// The budget is a RATCHET: lower the numbers after a release improves them; never raise one without writing why in docs/UI-REDESIGN.md.
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
const B = JSON.parse(readFileSync(join(ROOT, 'data', 'ui-budget.json'), 'utf8')).editor || {};
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css' };
const srv = http.createServer((q, r) => { let p = join(DIST, decodeURIComponent(q.url.split('?')[0])); if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html'); if (!existsSync(p)) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' }); r.end(readFileSync(p)); }).listen(0);
const base = 'http://localhost:' + srv.address().port;
const urls = [];
for (const st of readdirSync(join(DIST, 'river'))) for (const g of readdirSync(join(DIST, 'river', st))) if (existsSync(join(DIST, 'river', st, g, 'index.html'))) urls.push(`/river/${st}/${g}/`);
const b = await chromium.launch();
const rows = [], bad = [];
for (const u of urls) {
  const c = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const p = await c.newPage();
  await p.route('**/*', r => (r.request().url().startsWith(base) ? r.continue() : r.abort()));  // the gate judges the page as built: a live USGS answer would date the pills and change the repeat count with the clock
  await p.goto(base + u, { waitUntil: 'load' });
  await p.waitForSelector('.gtabs button', { timeout: 10000 }).catch(() => {});
  await p.waitForTimeout(300);
  const m = await p.evaluate(() => {
    const top = [...document.querySelectorAll('.hero, .answer, .cstrip')];
    const text = top.map(e => e.innerText || '').join('\n');
    const count = {};
    for (const t of text.match(/[A-Z][a-z]{2} \d{1,2}, \d{1,2}:\d{2} [AP]M [A-Z]{2,4}/g) || []) count[t] = (count[t] || 0) + 1;
    for (const l of text.split('\n').map(s => s.trim()).filter(s => s.length >= 12)) count[l] = (count[l] || 0) + 1;
    const repeat = Math.max(0, ...Object.values(count));
    const trendRepeat = (text.match(/\b(Rising|Falling|Steady)\b/g) || []).length;
    const tileChars = Math.max(0, ...[...document.querySelectorAll('.cstrip .tile')].map(t => (t.innerText || '').length));
    let firstWords = 0;
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n; (n = w.nextNode());) {
      const e = n.parentElement; if (!e || ['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(e.tagName)) continue;
      const r = e.getBoundingClientRect(); if (r.width === 0 || r.height === 0 || r.top >= 844 || getComputedStyle(e).visibility === 'hidden') continue;
      firstWords += (n.textContent.trim().split(/\s+/).filter(Boolean)).length;
    }
    // detail checks (2026-10-20, "be autistic and adhd about everything on the page"): the things one notices only when staring at it
    const all = document.body.innerText, ex = [];
    const bare = (all.match(/(?<!gauge )(?<![\d.,A-Za-z-])\d{5,}(?![\d,.A-Za-z])/g) || []).filter(n => !/^(19|20)\d\d$/.test(n)); if (bare.length) ex.push('number without thousands comma: ' + bare[0]);
    const odd = all.match(/ ,| \.(?!\d)|\.\.(?!\.)|,,|\( | \)|\bundefined\b|\bNaN\b|\[object/); if (odd) ex.push('stray punctuation or code text: "' + odd[0] + '"');
    const cf = new Set((all.match(/\bcfs\b/gi) || []).map(x => (/[a-z]/.test(x) && /[A-Z]/.test(x)) ? x : x.toLowerCase())); if (cf.size > 1) ex.push('cfs written two ways: ' + [...cf].join(' and '));  // CSS sets the unit in capitals beside the number (design 2026-10-21): CFS and cfs are one spelling, Cfs is not
    const dup = all.match(/\b(\w{3,})[ \t]+\1\b/i);  // same line only: a unit ending one tile and starting the next is not a typo if (dup && !/^(that|had)$/i.test(dup[1])) ex.push('repeated word: "' + dup[0] + '"');
    const empty = [...document.querySelectorAll('.tile,.card.blk')].filter(e => e.getBoundingClientRect().height > 0 && (e.innerText || '').trim().length < 3).length; if (empty) ex.push(empty + ' empty tile or block');
    const rowH = {}; for (const t of document.querySelectorAll('.cstrip .tile')) { const r = t.getBoundingClientRect(); if (r.height) (rowH[Math.round(r.top)] = rowH[Math.round(r.top)] || []).push(Math.round(r.height)); }
    const uneven = Object.values(rowH).filter(h => h.length > 1 && Math.max(...h) - Math.min(...h) > 2).length; if (uneven) ex.push(uneven + ' tile row(s) with tiles of different height');
    const tiny = [...document.querySelectorAll('.tile b small')].filter(s => parseFloat(getComputedStyle(s).fontSize) < 0.33 * parseFloat(getComputedStyle(s.parentElement).fontSize)).length; if (tiny) ex.push(tiny + ' unit(s) printed at under 40% of the number height');
    const detail = ex;
    const hasFlow = !!document.querySelector('.tile.flow');
    const unitShown = !hasFlow || /cubic feet per second/i.test(document.body.innerText) || !!document.querySelector('.tile.flow abbr[title*="cubic feet"]');
    return { repeat, trendRepeat, tileChars, firstWords, unitShown, detail };
  });
  rows.push({ u, ...m });
  if (m.repeat > (B.repeat ?? 1e9)) bad.push(`${u}: one timestamp or line repeated ${m.repeat} times in the top block > ${B.repeat}`);
  if (m.trendRepeat > (B.trendRepeat ?? 1e9)) bad.push(`${u}: trend word written ${m.trendRepeat} times in the top block > ${B.trendRepeat}`);
  if (m.tileChars > (B.tileChars ?? 1e9)) bad.push(`${u}: a swipe-strip tile runs to ${m.tileChars} characters > ${B.tileChars}`);
  if (m.firstWords > (B.firstWords ?? 1e9)) bad.push(`${u}: ${m.firstWords} words on the first phone screen > ${B.firstWords}`);
  for (const d of m.detail) bad.push(`${u}: ${d}`);
  if (B.unitShown && !m.unitShown) bad.push(`${u}: "cfs" is never spelled out in visible text`);
  await c.close();
}
// --- section: tables never scroll sideways (was clip_all.mjs). Fonts differ between machines, so 360 and 340 px stand in for a wider font at 390 px. Fails when any `.scroll` (except the hourly heatmap) is wider than its box.
const clipBad = [];
for (const w of [390, 360, 340]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 800 }, deviceScaleFactor: 1 });
  const pg = await ctx.newPage();
  for (const u of urls) {
    await pg.goto(base + u + (u.indexOf('?') < 0 ? '?tabs=off' : ''));
    const clip = await pg.evaluate(() => [...document.querySelectorAll('.scroll')].filter(s => s.scrollWidth > s.clientWidth + 2 && !s.querySelector('table.hm')).map(s => (s.closest('section') || { id: 'page' }).id));
    if (clip.length) clipBad.push(`${w}px ${u}: ${clip.join(', ')}`);
  }
  await ctx.close();
}
// --- section: reader budget (was reader_budget.mjs). Measures every page on a phone (390 px, tabs on) and fails when a page is longer, more repetitive or buries its answer more than data/ui-budget.json allows. A RATCHET: never raise a number without writing why in docs/UI-REDESIGN.md.
const BUDGET = JSON.parse(readFileSync(join(ROOT, 'data', 'ui-budget.json'), 'utf8'));
const budBad = [], budRows = [], budWarn = [];
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
  budRows.push({ u, ...m });
  if (m.maxTab > BUDGET.maxTabHeight) budWarn.push(`${u}: tallest phone tab ${m.maxTab} px > budget ${BUDGET.maxTabHeight}`);
  if (BUDGET.maxNowHeight && m.nowTab > BUDGET.maxNowHeight) budWarn.push(`${u}: the Now tab is ${m.nowTab} px > budget ${BUDGET.maxNowHeight}`);
  if (m.answerBottom > BUDGET.answerBottom) budBad.push(`${u}: one-line answer ends at ${m.answerBottom} px > ${BUDGET.answerBottom}`);
  if (m.grid > BUDGET.gridTiles) budBad.push(`${u}: ${m.grid} tiles in the grid > ${BUDGET.gridTiles}`);
  if (m.maxRepeat > BUDGET.maxRepeat) budBad.push(`${u}: one figure repeated in ${m.maxRepeat} blocks > ${BUDGET.maxRepeat}`);
  if (m.tabCount < BUDGET.minTabs) budBad.push(`${u}: only ${m.tabCount} phone tabs (< ${BUDGET.minTabs})`);
  await c.close();
}
await b.close(); srv.close();
const mx = k => Math.max(...rows.map(r => r[k]));
console.log(`editor gate: ${rows.length} pages; worst repeat ${mx('repeat')}, trend word ${mx('trendRepeat')}, longest tile ${mx('tileChars')} chars, first screen ${mx('firstWords')} words, unit spelled out on ${rows.filter(r => r.unitShown).length}/${rows.length}; budget ${JSON.stringify(B)}`);
if (bad.length) console.log('EDITOR GATE FAILED:\n' + bad.slice(0, 25).join('\n'));
else console.log('editor gate passes');
if (clipBad.length) console.log('TABLES CUT OFF\n' + clipBad.join('\n'));
else console.log('no table scrolls sideways on ' + urls.length + ' gauge pages at 390, 360 and 340 px');
for (const w of budWarn) console.log('WARN (height, not blocking: a Line 0 block is never cut for length) ' + w);
const worst = budRows.reduce((a, r) => (r.maxTab > a.maxTab ? r : a), budRows[0]);
const tall = budRows.reduce((a, r) => { for (const [k, v] of Object.entries(r.perTab)) if (v > a[1]) a = [k + ' ' + r.u, v]; return a; }, ['', 0]);
console.log(`Now tab at most ${Math.max(...budRows.map(r => r.nowTab))} px; tallest tab is ${tall[0]} at ${tall[1]} px`);
console.log(`reader budget: ${budRows.length} pages; tallest phone tab ${worst.maxTab} px (${worst.u}); budget ${BUDGET.maxTabHeight}; max repeat ${Math.max(...budRows.map(r => r.maxRepeat))}; max grid tiles ${Math.max(...budRows.map(r => r.grid))}; answer ends by ${Math.max(...budRows.map(r => r.answerBottom))} px`);
if (budBad.length) console.log('READER BUDGET FAILED:\n' + budBad.slice(0, 25).join('\n'));
else console.log('reader budget passes');
console.log(`editor gate sections: detail ${bad.length ? 'FAIL' : 'pass'}, clipping ${clipBad.length ? 'FAIL' : 'pass'}, budgets ${budBad.length ? 'FAIL' : 'pass'}`);
process.exit(bad.length || clipBad.length || budBad.length ? 1 : 0);
