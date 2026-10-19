// node comp_shots.mjs lakebrief|ours  -> sliced screenshots (2000 css px tall each) in riverwaterlevels/shots/cmp/
import { createRequire } from 'module';
import { mkdirSync, rmSync } from 'fs';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const which = process.argv[2];
const OUT = 'C:/Users/mwoo7/Desktop/riverwaterlevels/shots/cmp/';
mkdirSync(OUT, { recursive: true });
const SITES = {
  lakebrief: { base: 'https://lakebrief.com', pages: { 'candlewood-lake-dashboard': '/lake/candlewood-lake', 'candlewood-lake-water': '/lake/candlewood-lake/water', 'candlewood-lake-forecast': '/lake/candlewood-lake/forecast', 'bantam-lake-water': '/lake/bantam-lake/water', 'shasta-lake-water': '/lake/shasta-lake/water' }, schemes: ['light'] },
  ours: { base: 'https://riverwaterlevels.com', pages: { 'home': '/', 'missouri-kansas-city': '/river/missouri-river-mo/kansas-city/', 'missouri-kansas-city-forecast': '/river/missouri-river-mo/kansas-city/forecast/', 'kinzua-creek': '/river/kinzua-creek/guffey/', 'yellowstone': '/river/yellowstone-river-mt/livingston/', 'gauley-alert': '/river/gauley-river/above-belva/', 'shenandoah-strip': '/river/shenandoah-river/millville/', 'hudson-forecast-gauge': '/river/hudson-river/green-island/', 'state-pa': '/rivers/pa/', 'status': '/status/' }, schemes: ['light', 'dark'] },
};
const S = SITES[which];
const b = await chromium.launch();
for (const [n, p] of Object.entries(S.pages)) {
  for (const [vn, vp] of [['desktop', { width: 1280, height: 900 }], ['phone', { width: 390, height: 844 }]]) {
    for (const sc of S.schemes) {
      const ctx = await b.newContext({ viewport: vp, colorScheme: sc, deviceScaleFactor: vn === 'phone' ? 2 : 1, isMobile: vn === 'phone', hasTouch: vn === 'phone' });
      const pg = await ctx.newPage();
      const ok = await pg.goto(S.base + p, { waitUntil: 'networkidle', timeout: 60000 }).then(r => r && r.status() === 200).catch(() => false);
      if (!ok) { console.log('SKIP', n, vn, sc); await ctx.close(); continue; }
      await pg.waitForTimeout(1500);
      const H = await pg.evaluate(() => document.documentElement.scrollHeight);
      const seg = 2000;
      for (let i = 0, y = 0; y < H; i++, y += seg) {
        await pg.screenshot({ path: OUT + which + '-' + n + '-' + vn + '-' + sc + '-' + String(i + 1).padStart(2, '0') + '.jpg', type: 'jpeg', quality: 72, fullPage: true, clip: { x: 0, y, width: vp.width, height: Math.min(seg, H - y) } });
      }
      console.log(which, n, vn, sc, 'height', H);
      await ctx.close();
    }
  }
}
await b.close();
