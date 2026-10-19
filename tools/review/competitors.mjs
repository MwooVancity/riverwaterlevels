import { createRequire } from 'module';
import { mkdirSync } from 'fs';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const OUT = process.env.COMP_OUT || 'shots/competitors';
mkdirSync(OUT, { recursive: true });
const only = process.argv[2];
const pages = [
  ['usgs-waterdata-03192000', 'https://waterdata.usgs.gov/monitoring-location/03192000/'],
  ['aw-lower-gauley', 'https://www.americanwhitewater.org/content/River/view/river-detail/2378/main'],
  ['nws-water-noaa-TRYN6', 'https://water.noaa.gov/gauges/TRYN6'],
  ['ours-gauley-above-belva', 'https://riverwaterlevels.com/river/gauley-river/above-belva/'],
  ['ours-hudson-green-island', 'https://riverwaterlevels.com/river/hudson-river/green-island/'],
];
const b = await chromium.launch();
for (const [name, url] of pages.filter(p => !only || p[0].includes(only))) {
  for (const [tag, vp, mobile] of [['desktop', { width: 1280, height: 900 }, false], ['phone', { width: 390, height: 844 }, true]]) {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 1, isMobile: mobile, userAgent: mobile ? undefined : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36' });
    const pg = await ctx.newPage();
    try {
      await pg.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await pg.waitForTimeout(name.startsWith('nws') ? 22000 : 6000);
      await pg.screenshot({ path: `${OUT}/${name}-${tag}.png`, clip: { x: 0, y: 0, width: vp.width, height: 1800 }, fullPage: true });
      console.log('ok', name, tag);
    } catch (e) { console.log('FAIL', name, tag, String(e).slice(0, 80)); }
    await ctx.close();
  }
}
await b.close();
