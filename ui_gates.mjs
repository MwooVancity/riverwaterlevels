// Reader-first browser gates. Usage: node ui_gates.mjs [dist_dir] [path ...]   (default dist_next and a sample of page types)
// Gates: first screen at 390 px (flow and gage height tiles fully visible, comparison tile started), tap targets at 390 px, text contrast in light and dark,
// minimum text size, no sideways scroll, no console errors. Saves a contact sheet to shots/gate/ that a person must LOOK at before a deploy (CLAUDE.md Line 0).
import http from 'http';
import { readFileSync, existsSync, statSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
const here = createRequire(import.meta.url);
let pw;
try { pw = here('playwright'); } catch { pw = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json')('playwright'); }  // this folder first (CI: npm install), else the owner's other project
const require = () => pw;
const { chromium } = require('playwright');
const ROOT = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const dir = args[0] && !args[0].startsWith('/') ? args.shift() : 'dist_next';
const DIST = join(ROOT, dir), OUT = join(ROOT, 'shots', 'gate');
mkdirSync(OUT, { recursive: true });
const PATHS = args.length ? args : ['/', '/rivers/mt/', '/river/yellowstone-river-mt/livingston/', '/river/kinzua-creek/guffey/', '/river/hudson-river/green-island/', '/river/salmon-river-id/white-bird/', '/about/'];
const types = { '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.css': 'text/css', '.png': 'image/png' };
const srv = http.createServer((q, r) => {
  let p = join(DIST, decodeURIComponent(q.url.split('?')[0]));
  if (existsSync(p) && statSync(p).isDirectory()) p = join(p, 'index.html');
  if (!existsSync(p)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': types[p.slice(p.lastIndexOf('.'))] || 'application/octet-stream' });
  r.end(readFileSync(p));
}).listen(0);
const BASE = 'http://localhost:' + srv.address().port;

// ---- page-side helpers (run inside the browser)
const contrastJS = () => {
  const parse = s => {
    let m = s.match(/rgba?\(([^)]+)\)/);
    if (m) { const v = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; }
    m = s.match(/color\(srgb ([^)]+)\)/);
    if (m) { const v = m[1].split(/[ \/]+/).filter(Boolean).map(Number); return [v[0] * 255, v[1] * 255, v[2] * 255, v.length > 3 ? v[3] : 1]; }
    return [255, 255, 255, 1];
  };
  const over = (f, b) => { const a = f[3]; return [f[0] * a + b[0] * (1 - a), f[1] * a + b[1] * (1 - a), f[2] * a + b[2] * (1 - a), 1]; };
  const bgOf = el => { const layers = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] >= 0.99) break; } let b = [255, 255, 255, 1]; for (let i = layers.length - 1; i >= 0; i--) b = over(layers[i], b); return b; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const bad = [], small = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n.textContent.trim(); const el = n.parentElement;
    if (!t || !el || el.closest('svg,script,style,[hidden],[aria-hidden=true]') || seen.has(el)) continue;
    const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || cs.display === 'none') continue;
    seen.add(el);
    const px = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
    if (px < 11) small.push(el.tagName.toLowerCase() + ' ' + px + 'px "' + t.slice(0, 24) + '"');
    const fg = over(parse(cs.color), bgOf(el)), bg = bgOf(el);
    const L1 = lum(fg), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const need = (px >= 24 || (px >= 18.66 && bold)) ? 3 : 4.5;
    if (ratio < need) bad.push(ratio.toFixed(2) + ' < ' + need + ' ' + el.tagName.toLowerCase() + '.' + (typeof el.className === 'string' ? el.className.split(' ')[0] : '') + ' "' + t.slice(0, 24) + '"');
  }
  return { bad: bad.slice(0, 8), nbad: bad.length, small: small.slice(0, 6), nsmall: small.length };
};
const tapJS = () => {
  const bad = [];
  document.querySelectorAll('a,button,input,select,summary').forEach(el => {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    if (r.width === 0 || r.height === 0 || cs.visibility === 'hidden' || el.closest('[hidden]')) return;
    if (cs.display === 'inline' && !el.closest('.pills,.jump,.acts,.tabs,.nav,footer')) return; // links inside a sentence are exempt
    if (el.classList.contains('skip') || el.classList.contains('dot')) return; // map pins: the same gauges are listed as links on the page
    if ((r.height < 36 || r.width < 24) && !bad.some(x => x.startsWith(el.tagName.toLowerCase() + '.' + (el.className || '') + ' '))) bad.push(el.tagName.toLowerCase() + '.' + (el.className || '') + ' ' + Math.round(r.width) + 'x' + Math.round(r.height) + ' "' + (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 20) + '"');
  });
  return { bad: bad.slice(0, 8), n: bad.length };
};
const firstScreenJS = () => {
  const vh = window.innerHeight, q = s => document.querySelector(s), out = [];
  if (!q('.hero2')) return out;
  for (const s of ['.tile.flow', '.tile.stage']) { const e = q(s); if (!e) out.push('missing ' + s); else if (e.getBoundingClientRect().bottom > vh) out.push(s + ' not fully visible without scrolling (bottom ' + Math.round(e.getBoundingClientRect().bottom) + ' > ' + vh + ')'); }
  const n = q('.tile.norm'); if (!n || n.getBoundingClientRect().top > vh) out.push('comparison tile starts below the first screen');
  return out;
};

// accessibility rules a person using a screen reader or a keyboard would hit (run in the page)
const a11yJS = () => {
  const out = [], q = s => [...document.querySelectorAll(s)];
  if (document.documentElement.lang !== 'en') out.push('html lang is not en');
  if (!document.title.trim()) out.push('empty title');
  if (q('main').length !== 1) out.push('main landmarks: ' + q('main').length);
  if (!q('nav').length) out.push('no nav landmark');
  const name = e => (e.getAttribute('aria-label') || e.getAttribute('title') || e.textContent || '').trim() || (e.id && document.querySelector('label[for="' + e.id + '"]') ? 'label' : '');
  q('a[href]').forEach(e => { if (!name(e) && !e.querySelector('img[alt]:not([alt=""])')) out.push('link without a name: ' + e.getAttribute('href')); });
  q('button').forEach(e => { if (!name(e)) out.push('button without a name'); });
  q('input,select,textarea').forEach(e => { if (!name(e) && e.type !== 'hidden') out.push('form field without a label: ' + (e.id || e.type)); });
  q('svg[role="img"]').forEach(e => { if (!e.getAttribute('aria-label')) out.push('chart svg without aria-label'); });
  q('svg:not([role]):not([aria-hidden])').forEach(e => { if (!e.closest('[aria-hidden="true"],button,a') && !e.querySelector('title')) out.push('svg that is neither labelled nor hidden'); });
  q('img').forEach(e => { if (!e.hasAttribute('alt')) out.push('img without alt'); });
  const ids = {}; q('[id]').forEach(e => { ids[e.id] = (ids[e.id] || 0) + 1; }); Object.keys(ids).forEach(k => { if (ids[k] > 1) out.push('duplicate id ' + k); });
  const sk = document.querySelector('a.skip'); if (!sk || sk.getAttribute('href') !== '#main') out.push('no skip link to #main');
  q('details > summary').forEach(e => { if (!e.textContent.trim()) out.push('empty summary'); });
  return [...new Set(out)].slice(0, 8);
};
const focusJS = async () => {  // tab through the first 12 stops: each must show a visible focus style
  return null;
};

let fails = 0;
const b = await chromium.launch();
const sheet = [];
for (const [label, w, h, scheme] of [['d-light', 1280, 900, 'light'], ['d-dark', 1280, 900, 'dark'], ['m-light', 390, 844, 'light'], ['m-dark', 390, 844, 'dark']]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, deviceScaleFactor: w < 600 ? 2 : 1, isMobile: w < 600, hasTouch: w < 600 });
  for (const p of PATHS) {
    const page = await ctx.newPage(); const errs = [];
    await page.addInitScript(() => { window.__cls = 0; try { new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true }); } catch (e) {} });
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errs.push(m.text().slice(0, 80)); });
    page.on('pageerror', e => errs.push(String(e).slice(0, 80)));
    let loaded = false;  // a slow machine must not turn into "no nav landmark": retry once, then report the real cause
    for (let k = 0; k < 2 && !loaded; k++) loaded = await page.goto(BASE + p, { waitUntil: 'load', timeout: 60000 }).then(() => true).catch(() => false);
    const issues = [];
    if (!loaded) issues.push('page did not load in 60 s (twice)');
    const sw = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (sw > 1) issues.push('page scrolls sideways by ' + sw + ' px');
    const c = await page.evaluate(contrastJS);
    if (c.nbad) issues.push('contrast: ' + c.nbad + ' text runs below the minimum, e.g. ' + c.bad.slice(0, 3).join(' | '));
    if (c.nsmall) issues.push('text under 11 px: ' + c.nsmall + ', e.g. ' + c.small.slice(0, 2).join(' | '));
    if (w < 600 && scheme === 'light') {
      const t = await page.evaluate(tapJS); if (t.n) issues.push('tap targets under 36 px high or 24 px wide: ' + t.n + ', e.g. ' + t.bad.slice(0, 3).join(' | '));
      issues.push(...(await page.evaluate(firstScreenJS)));
      const clip = await page.evaluate(() => [...document.querySelectorAll('.scroll')].filter(s => s.scrollWidth > s.clientWidth + 2 && !s.querySelector('table.hm')).map(s => (s.closest('section') || { id: 'page' }).id));
      if (clip.length) issues.push('table columns cut off on a phone: ' + clip.join(', '));
    }
    if (errs.length) issues.push('console: ' + errs[0]);
    if (scheme === 'light' && w >= 1000) {
      const a = await page.evaluate(a11yJS); a.forEach(x => issues.push('accessibility: ' + x));
      let bad = [];
      for (let i = 0; i < 12; i++) {
        await page.keyboard.press('Tab');
        const st = await page.evaluate(() => { const e = document.activeElement; if (!e || e === document.body) return null; const c = getComputedStyle(e); return { tag: e.tagName, label: (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 20), ok: (c.outlineStyle !== 'none' && parseFloat(c.outlineWidth) > 0) || c.boxShadow !== 'none' || e.matches(':focus-visible') && c.outlineStyle !== 'none' }; });
        if (st && !st.ok) bad.push(st.tag + ' "' + st.label + '"');
      }
      if (bad.length) issues.push('keyboard focus not visible on: ' + [...new Set(bad)].slice(0, 3).join(', '));
      const cls = await page.evaluate(() => window.__cls || 0);
      if (cls > 0.1) issues.push('layout shift (CLS) ' + cls.toFixed(3) + ' is over 0.1');
    }
    const f = join(OUT, label + p.replace(/[^a-z0-9]+/gi, '_') + '.png');
    await page.screenshot({ path: f });
    sheet.push(f);
    if (issues.length) { fails++; console.log('FAIL ' + label + ' ' + p + '\n   ' + issues.join('\n   ')); }
    await page.close();
  }
  await ctx.close();
}
{
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 400, downloadThroughput: 50 * 1024, uploadThroughput: 25 * 1024 });  // about 400 kbit/s, 400 ms latency
  const t0 = Date.now();
  const gp = PATHS.find(p => p.startsWith('/river/')) || PATHS[0];
  await page.goto(BASE + gp, { waitUntil: 'commit' }).catch(() => {});
  const seen = await page.waitForSelector('.tile.flow b', { timeout: 20000 }).then(() => (Date.now() - t0) / 1000).catch(() => null);
  if (seen === null || seen > 8) { fails++; console.log('FAIL slow connection ' + gp + '\n   flow tile visible after ' + (seen === null ? 'more than 20' : seen.toFixed(1)) + ' s on a 400 kbit/s phone connection (limit 8 s)'); }
  else console.log('slow connection: flow tile visible after ' + seen.toFixed(1) + ' s on 400 kbit/s');
  await ctx.close();
}
await b.close(); srv.close();
console.log((fails ? 'UI GATES FAILED: ' + fails + ' page-view combinations' : 'UI gates pass') + '; ' + sheet.length + ' screenshots saved in shots/gate/ (LOOK at them: top of each page, 1280 and 390, light and dark)');
process.exit(fails ? 1 : 0);
