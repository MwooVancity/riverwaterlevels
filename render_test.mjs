// Real-browser render test with true device emulation. Usage: node render_test.mjs [--all] [--shots]
// Serves dist/ locally; for each page and viewport checks: page-level horizontal overflow, elements poking past the viewport (outside scroll boxes),
// console errors, failed requests, h1 present, readings visible with scripts off. Exit 1 on any failure.
import http from 'http';
import { readFileSync, existsSync, statSync, mkdirSync, readdirSync } from 'fs';
import { join, dirname, extname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const ROOT = dirname(fileURLToPath(import.meta.url)), DIST = join(ROOT, 'dist'), SHOTS = join(ROOT, 'shots');
mkdirSync(SHOTS, { recursive: true });
const T = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.json': 'application/json', '.xml': 'application/xml', '.txt': 'text/plain', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
  let f = join(DIST, decodeURIComponent(req.url.split('?')[0]));
  if (existsSync(f) && statSync(f).isDirectory()) f = join(f, 'index.html');
  if (!existsSync(f)) { const nf = join(DIST, '404.html'); res.writeHead(404, { 'content-type': 'text/html' }); res.end(existsSync(nf) ? readFileSync(nf) : 'not found'); return; }
  res.writeHead(200, { 'content-type': T[extname(f)] || 'application/octet-stream' }); res.end(readFileSync(f));
});
await new Promise(r => server.listen(0, r));
const BASE = `http://localhost:${server.address().port}`;

function allPages() {
  const out = [];
  const walk = d => { for (const e of readdirSync(d, { withFileTypes: true })) { const p = join(d, e.name); if (e.isDirectory()) walk(p); else if (e.name === 'index.html') out.push('/' + p.slice(DIST.length + 1).replace(/\\/g, '/').replace(/index\.html$/, '')); } };
  walk(DIST); return out.sort();
}
const pages = allPages();
const sample = process.argv.includes('--all') ? pages : [
  '/', '/rivers/pa/', ...pages.filter(p => /^\/river\/[^/]+\/$/.test(p)).slice(0, 2), '/about/', '/data-sources/',
  ...['colorado-river-az/lees-ferry', 'missouri-river-mo/kansas-city', 'potomac-river-md/little-falls', 'kinzua-creek/guffey', 'sacramento-river/freeport'].flatMap(g => [`/river/${g}/`, `/river/${g}/water/`, `/river/${g}/forecast/`]),
].filter(p => pages.includes(p));
const VIEWS = [[360, 800, true], [390, 844, true], [430, 932, true], [768, 1024, false], [1280, 900, false]];

const browser = await chromium.launch();
let fails = 0, checked = 0;
for (const [w, h, mobile] of VIEWS) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: mobile, hasTouch: mobile, deviceScaleFactor: 1 });
  for (const p of sample) {
    const page = await ctx.newPage();
    const errs = [], bad = [];
    page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    page.on('pageerror', e => errs.push(String(e)));
    page.on('requestfailed', r => { if (r.url().startsWith(BASE)) bad.push('request failed ' + r.url()); });
    await page.goto(BASE + p, { waitUntil: 'load' });
    const r = await page.evaluate(() => {
      const vw = document.documentElement.clientWidth, o = [];
      const inScroll = el => { for (let e = el.parentElement; e; e = e.parentElement) { const s = getComputedStyle(e); if (/(auto|scroll)/.test(s.overflowX) && e.scrollWidth > e.clientWidth) return true; } return false; };
      document.querySelectorAll('body *').forEach(el => { const b = el.getBoundingClientRect(); if (b.width > 0 && b.right > vw + 1 && !inScroll(el)) o.push(el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '') + ' right=' + Math.round(b.right)); });
      return { vw, sw: document.documentElement.scrollWidth, over: o.slice(0, 5), h1: document.querySelectorAll('h1').length, text: document.body.innerText.length };
    });
    checked++;
    const issues = [];
    if (r.sw > r.vw + 1) issues.push(`page scrolls sideways (scrollWidth ${r.sw} > ${r.vw})`);
    if (r.over.length) issues.push('elements past viewport: ' + r.over.join('; '));
    if (r.h1 !== 1) issues.push('h1 count ' + r.h1);
    if (errs.length) issues.push('console: ' + errs[0].slice(0, 80));
    issues.push(...bad);
    if (issues.length) { fails++; console.log(`FAIL ${w}px ${p}\n   ` + issues.join('\n   ')); if (process.argv.includes('--shots')) await page.screenshot({ path: join(SHOTS, `fail-${w}-${p.replace(/\W+/g, '_')}.png`), fullPage: true }); }
    await page.close();
  }
  await ctx.close();
}
// scripts off: readings must be in the static HTML
const nojs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
const np = await nojs.newPage();
await np.goto(BASE + '/river/missouri-river-mo/kansas-city/', { waitUntil: 'load' });
const hasFlow = await np.evaluate(() => /latest flow[\s\S]*\d/i.test(document.body.innerText));
console.log('scripts off: latest flow present in static HTML:', hasFlow); if (!hasFlow) fails++;
// phone screenshots for the record
const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
for (const [name, p] of [['water', '/river/colorado-river-az/lees-ferry/'], ['home', '/'], ['forecast', '/river/missouri-river-mo/kansas-city/forecast/']]) {
  const pg = await phone.newPage(); await pg.goto(BASE + p, { waitUntil: 'load' }); await pg.screenshot({ path: join(SHOTS, `phone390-${name}.png`), fullPage: true }); await pg.close();
}
await browser.close(); server.close();
console.log(`checked ${checked} page-viewport combinations, failing ${fails}`);
process.exit(fails ? 1 : 0);
