// Hater review, step 1 (owner 2026-10-27: "no page goes live unless it is scrutinized like the worst hater in the world").
// Serves the built site (dist_next) locally and saves what a visitor SEES for each gauge: phone (390 px) full page cut into
// readable slices, desktop first screen, and the visible text. The reviewer reads these files, then signs with tools/review_sign.py.
// Usage: node tools/hater_shots.mjs [site ...]   (no sites: every gauge page in dist_next)   Output: .cache/review/<site>/
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1')), '..');
const DIST = path.join(ROOT, 'dist_next');
const OUT = path.join(ROOT, '.cache', 'review');
const LIVE = process.argv.includes('--live'); // review the deployed site itself (no local build needed)
const BASE_ARG = (process.argv.find((a) => a.startsWith('--base=')) || '').slice(7).replace(/\/$/, ''); // a preview version URL from preview.yml: no local collect or build
const REMOTE = LIVE || !!BASE_ARG;
const BASE = BASE_ARG || (LIVE ? 'https://riverwaterlevels.com' : 'http://localhost:8123');
const live = REMOTE ? await (await fetch(BASE + '/live-sites.json')).json() : JSON.parse(fs.readFileSync(path.join(DIST, 'live-sites.json'), 'utf8')); // [[site, url, built, tz]]
const want = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const pages = live.filter(([s]) => !want.length || want.includes(s));
for (const w of want) if (!live.some(([s]) => s === w)) console.log('NOT SHOT', w, ': not in live-sites.json of this build (mark it live and build first)');
const CODE = (await import('node:child_process')).execFileSync(process.platform === 'win32' ? 'python' : 'python3', ['-I', '-c', 'import sys; sys.path.insert(0, sys.argv[1]); from lib.common import template_hash; print(template_hash())', ROOT]).toString().trim();
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.ico': 'image/x-icon' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(DIST, p);
  if (!f.startsWith(DIST) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(8123);

const browser = await chromium.launch();
for (const [site, url] of pages) {
  const dir = path.join(OUT, site);
  fs.mkdirSync(dir, { recursive: true });
  for (const f of fs.readdirSync(dir)) fs.unlinkSync(path.join(dir, f));
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p = await phone.newPage();
  if (!REMOTE) await p.route(/^https?:\/\/(?!localhost)/, (r) => r.abort()); // a local build: no outside calls while shooting
  await p.goto(BASE + url + '?tabs=off', { waitUntil: 'load' });
  await p.waitForTimeout(REMOTE ? 2500 : 300); // live: let the page's own refresh land, as a visitor sees it
  // scroll like a visitor so lazy images (radar loop, map) load; a shot of an unloaded image is a false "blank box" (hater 2026-10-27)
  await p.evaluate(async () => { for (let y = 0; y < document.documentElement.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 120)); } window.scrollTo(0, 0); });
  await p.waitForLoadState('networkidle').catch(() => {});
  const H = await p.evaluate(() => document.documentElement.scrollHeight);
  const SLICE = 1400;
  for (let y = 0, i = 1; y < H && i <= 30; y += SLICE, i++) {
    await p.screenshot({ path: path.join(dir, `phone-${String(i).padStart(2, '0')}.png`), clip: { x: 0, y, width: 390, height: Math.min(SLICE, H - y) }, fullPage: true });
  }
  fs.writeFileSync(path.join(dir, 'text.txt'), await p.evaluate(() => document.querySelector('main') ? document.querySelector('main').innerText : document.body.innerText));
  await phone.close();
  const desk = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const d = await desk.newPage();
  if (!REMOTE) await d.route(/^https?:\/\/(?!localhost)/, (r) => r.abort());
  await d.goto(BASE + url, { waitUntil: 'load' });
  await d.screenshot({ path: path.join(dir, 'desktop-01.png') });
  await desk.close();
  fs.writeFileSync(path.join(dir, '_code.txt'), REMOTE ? 'remote ' + BASE : CODE); // review_sign.py refuses a PASS on code changed after these shots
  if (H > 30 * SLICE) console.log('WARNING', site, 'page is', H, 'px: only the first', 30 * SLICE, 'px were shot');
  console.log(site, url, fs.readdirSync(dir).length, 'files');
}
await browser.close();
server.close();
