// node imgload.mjs <url> : scrolls through the page and reports whether every <img> loaded (naturalWidth > 0)
import { createRequire } from 'module';
const require = createRequire('C:/Users/mwoo7/Desktop/calcscrape/package.json');
const { chromium } = require('playwright');
const b = await chromium.launch();
const pg = await (await b.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
await pg.goto(process.argv[2], { waitUntil: 'load' });
await pg.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 250)); } });
await pg.waitForTimeout(4000);
console.log(JSON.stringify(await pg.evaluate(() => [...document.images].map(i => ({ src: i.src.slice(0, 70), ok: i.naturalWidth > 0, w: i.naturalWidth, shown: Math.round(i.getBoundingClientRect().width) }))), null, 1));
await b.close();
