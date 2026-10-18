// Reader-first browser gates. Usage: node ui_gates.mjs [dist_dir] [path ...]   (default dist_next and a sample of page types)
// Gates: first screen at 390 px (flow and gage height tiles fully visible, comparison tile started), tap targets at 390 px, text contrast in light and dark,
// minimum text size, no sideways scroll, no console errors. Saves a contact sheet to shots/gate/ that a person must LOOK at before a deploy (CLAUDE.md Line 0).
import http from 'http';
import { readFileSync, existsSync, statSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
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

let fails = 0;
const b = await chromium.launch();
const sheet = [];
for (const [label, w, h, scheme] of [['d-light', 1280, 900, 'light'], ['d-dark', 1280, 900, 'dark'], ['m-light', 390, 844, 'light'], ['m-dark', 390, 844, 'dark']]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, deviceScaleFactor: w < 600 ? 2 : 1, isMobile: w < 600, hasTouch: w < 600 });
  for (const p of PATHS) {
    const page = await ctx.newPage(); const errs = [];
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errs.push(m.text().slice(0, 80)); });
    page.on('pageerror', e => errs.push(String(e).slice(0, 80)));
    await page.goto(BASE + p, { waitUntil: 'load' }).catch(() => {});
    const issues = [];
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
    const f = join(OUT, label + p.replace(/[^a-z0-9]+/gi, '_') + '.png');
    await page.screenshot({ path: f });
    sheet.push(f);
    if (issues.length) { fails++; console.log('FAIL ' + label + ' ' + p + '\n   ' + issues.join('\n   ')); }
    await page.close();
  }
  await ctx.close();
}
await b.close(); srv.close();
console.log((fails ? 'UI GATES FAILED: ' + fails + ' page-view combinations' : 'UI gates pass') + '; ' + sheet.length + ' screenshots saved in shots/gate/ (LOOK at them: top of each page, 1280 and 390, light and dark)');
process.exit(fails ? 1 : 0);
