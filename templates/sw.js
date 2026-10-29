// Offline layer: keeps the last page and reading so a phone with weak or no signal still shows something with its age.
// Plain JS. Same-origin GET only: nothing from another host (radar, cameras, maps, NWS, USGS) is ever cached or touched.
// Pages and /live/*.json: network first, saved copy after 4 s or when the network fails. Stylesheet, icons, manifest: saved copy first.
// Never decides what a page says: the page's own age chip and "as of" times stay as built; this only adds the "Offline" line to a saved copy.
const V = "rwl-1"; // bump to drop every older cache
const PAGES = "pages-" + V, LIVE = "live-" + V, STATIC = "static-" + V;
const KEEP = 20, WAIT = 4000; // saved copies per cache; ms before the saved copy is shown
// AGE_FN in lib/page.py, character for character (check.py): the page, the edge and this file print one age
function age(d){var m=Math.round((Date.now()-d)/60000);return m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => ![PAGES, LIVE, STATIC].includes(k)).map((k) => caches.delete(k)))).then(() => self.clients.claim())
));

self.addEventListener("fetch", (e) => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.origin !== location.origin || u.pathname === "/sw.js" || u.pathname.startsWith("/embed/")) return;
  if (/^\/(site|dir)\.[0-9a-f]+\.css$|^\/(icon-\d+\.png|favicon\.svg|manifest\.webmanifest)$/.test(u.pathname)) e.respondWith(saved(r));
  else if (u.pathname.startsWith("/live/")) e.respondWith(fresh(e, r, LIVE));
  else if (r.mode === "navigate") e.respondWith(fresh(e, r, PAGES));
});

async function saved(r) {
  const c = await caches.open(STATIC), hit = await c.match(r);
  if (hit) return hit;
  const res = await fetch(r);
  if (res.ok) c.put(r, res.clone());
  return res;
}

async function fresh(e, r, name) {
  const u = new URL(r.url), key = u.origin + u.pathname; // one saved copy per page, whatever the query string
  const net = fetch(r).then((res) => {
    if (res.ok && /html|json/.test(res.headers.get("content-type") || "")) e.waitUntil(keep(name, key, res.clone()));
    return res;
  });
  net.catch(() => {}); // a late failure after the saved copy was shown is not an error
  try {
    const first = await Promise.race([net, new Promise((ok) => setTimeout(() => ok(null), WAIT))]);
    if (first) return first;
  } catch (_) { /* network failed: fall through to the saved copy */ }
  const hit = await (await caches.open(name)).match(key);
  if (hit) return name === PAGES ? offline(hit) : hit;
  return net; // nothing saved: wait for the network, or fail as it would have
}

async function keep(name, key, res) {
  const c = await caches.open(name), h = new Headers(res.headers);
  h.set("x-rwl-saved", String(Date.now()));
  h.delete("content-encoding");
  h.delete("content-length");
  await c.put(key, new Response(await res.blob(), { status: res.status, statusText: res.statusText, headers: h }));
  const ks = await c.keys(); // oldest first; a re-saved page moves to the end
  for (const k of ks.slice(0, Math.max(0, ks.length - KEEP))) await c.delete(k);
}

async function offline(res) {
  const t = Number(res.headers.get("x-rwl-saved")), html = await res.text();
  const line = '<p class="offl" role="status">Offline: showing this page as saved ' + (t ? age(t) + " ago" : "earlier") + "</p>";
  return new Response(html.replace(/<main\b[^>]*>/, (m) => m + line), { status: 200, headers: { "content-type": "text/html; charset=utf-8" } });
}
