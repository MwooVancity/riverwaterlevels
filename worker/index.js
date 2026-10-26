// Edge live layer (plan 2026-10-25: freshness stops depending on builds).
// A */2 cron pulls the newest USGS flow and gage height for every live gauge in a few bulk calls and stores one KV value. Backup: when
// a gauge page or /live.json is requested and the stored readings are over 2 minutes old, the same refresh runs after the response.
// Every gauge page is served through HTMLRewriter: when the stored reading is newer than the one the page was built with, the
// flow, gage height, observed time and age are swapped in and a note says the charts below are as of the build. Any error, a missing
// or older reading, or a non-gauge path serves the static file untouched: never older than the build, never broken.

const LATEST = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items";
const UA = "riverwaterlevels.com (https://riverwaterlevels.com/about/)";
const CHUNK = 300; // gauge ids per call: keeps the URL under ~5 KB
const CALLS_PER_H = 250; // live refresh may use at most a quarter of the USGS key's 1,000/h: the interval stretches as gauges are added (2 min at 53, ~7.5 min at 9,099)

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(refresh(env));
  },

  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    try {
      if (url.pathname === "/live.json") {
        const v = await env.LIVE.get("live", { cacheTtl: 60 });
        const j = v ? JSON.parse(v) : {};
        refreshIfOld(j, env, ctx);
        return new Response(JSON.stringify({ t: j.t || null, g: j.g || {} }), {
          headers: { "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=60" },
        });
      }
      if (!url.pathname.startsWith("/river/")) return env.ASSETS.fetch(req);
      const h = new Headers(req.headers);
      h.delete("if-none-match"); // a 304 would let the browser keep a stale copy of a page we are about to update
      h.delete("if-modified-since");
      const res = await env.ASSETS.fetch(new Request(req, { headers: h }));
      if (!res.ok || !(res.headers.get("content-type") || "").includes("text/html")) return res;
      const L = await env.LIVE.get("live", { type: "json", cacheTtl: 60 });
      refreshIfOld(L, env, ctx);
      const site = L && L.u && L.u[url.pathname];
      const g = site && L.g[site], m = site && L.m[site];
      // never swap a flagged (Ice, Equipment, ...) or sentinel reading: the built page prints the flag in words, the edge does not
      if (!g || !g.f || !m || !(Date.parse(g.f[1]) > Date.parse(m[0])) || g.f[2] || !(g.f[0] > -999)) return tag(res, site ? "static" : "static-unknown", L);
      return tag(rewrite(res, g, m), "swapped", L);
    } catch (e) {
      return env.ASSETS.fetch(req);
    }
  },
};

const MAX_AGE = 120000; // refresh when the stored readings are older than 2 minutes

function refreshIfOld(L, env, ctx) {
  if (L && L.t && Date.now() - Date.parse(L.t) < MAX_AGE) return;
  ctx.waitUntil((async () => {
    // one refresh per Cloudflare location per ~2 min: a cache entry is the lock (free, no KV write)
    const lock = new Request("https://riverwaterlevels.com/__live_refresh_lock");
    if (await caches.default.match(lock)) return;
    await caches.default.put(lock, new Response("1", { headers: { "cache-control": "max-age=110" } }));
    await refresh(env);
  })().catch(() => {}));
}

// x-rwl-edge says what the edge did with this page (swapped / static / static-unknown) and how old its stored readings are, so the live gate can see it
function tag(res, what, L) {
  const o = new Response(res.body, res);
  o.headers.set("x-rwl-edge", what + (L && L.t ? "; live-age-s=" + Math.round((Date.now() - Date.parse(L.t)) / 1000) : "; live-age-s=none"));
  return o;
}

function local(iso, tz) {
  return new Date(iso).toLocaleString("en-US", { timeZone: tz, month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }).replace(/[  ]/g, " "); // Intl uses narrow no-break spaces; the build uses plain ones
}

function age(iso) {
  const m = Math.round((Date.now() - Date.parse(iso)) / 60000);
  return m < 180 ? m + " min" : m < 2880 ? Math.round(m / 60) + " h" : Math.round(m / 1440) + " d";
}

function rewrite(res, g, m) {
  const [fv, ft] = g.f, tz = m[1], mins = (Date.now() - Date.parse(ft)) / 60000;
  const text = (s) => ({ element(e) { e.setInnerContent(s); } });
  const asof = " (as of the " + local(m[0], tz) + " reading)";
  const out = new HTMLRewriter()
    .on('span[data-live="flow"]', text(Math.round(fv).toLocaleString("en-US"))) // same rounding as fmtc() in lib/common.py
    .on('span[data-live="lead"]', text(Math.round(fv).toLocaleString("en-US") + " cfs"))
    // dv = text the build derived from its own reading (class word, trend, flood distance, forecast vs now): not recomputed here, so it carries its own time
    .on(".dv", { element(e) { e.append('<small class="asof">' + asof + "</small>", { html: true }); } })
    .on('span[data-live="obs"]', text(local(ft, tz)))
    .on('span[data-live="age"]', { element(e) { e.setAttribute("data-t", ft); e.setInnerContent(age(ft)); } })
    .on("span.ab", { element(e) { e.setAttribute("class", "ab " + (mins <= 90 ? "fresh" : mins <= 360 ? "ageing" : "stale")); } })
    .on(".hero", { element(e) {
      const built = e.getAttribute("data-t");
      e.after('<p id="lbn" class="src lf2">Flow and gage height at the top updated ' + local(ft, tz) + ". Charts, tables and comparisons below are as of the page build" + (built ? ", " + local(built, tz) : "") + ".</p>", { html: true });
    } });
  if (g.h && !g.h[2] && g.h[0] > -999 && Date.parse(g.h[1]) > Date.parse(m[0])) out.on('span[data-live="stage"]', text(Number(g.h[0]).toFixed(2)));
  const r = out.transform(res);
  const o = new Response(r.body, r);
  o.headers.delete("etag");
  o.headers.set("cache-control", "public, max-age=0, must-revalidate");
  return o;
}

async function refresh(env) {
  const sites = await (await env.ASSETS.fetch("https://riverwaterlevels.com/live-sites.json")).json(); // [[site, url, built iso, tz]]
  const prev = (await env.LIVE.get("live", { type: "json" })) || {};
  const every = Math.max(MAX_AGE, Math.ceil(Math.ceil(sites.length / CHUNK) * 3600000 / CALLS_PER_H));
  if (prev.t && Date.now() - Date.parse(prev.t) < every - 20000) return; // refreshed recently enough (another location, or the quota-capped interval): also keeps KV writes under the free 1,000/day
  const g = {}, cutoff = Date.now() - 8 * 86400000; // the service returns decades-old values for dead sensors
  for (const [s] of sites) if (prev.g && prev.g[s]) g[s] = prev.g[s]; // a failed chunk keeps the previous reading
  let got = 0;
  for (let i = 0; i < sites.length; i += CHUNK) {
    let next = LATEST + "?monitoring_location_id=" + sites.slice(i, i + CHUNK).map((x) => "USGS-" + x[0]).join(",") + "&parameter_code=00060,00065&limit=10000&skipGeometry=true&properties=monitoring_location_id,parameter_code,value,time,qualifier&f=json"; // ~30% smaller replies
    for (let page = 0; next && page < 5; page++) {
      const r = await fetch(next, { headers: env.USGS_API_KEY ? { "X-Api-Key": env.USGS_API_KEY, "User-Agent": UA } : { "User-Agent": UA } }); // no key set yet: anonymous (lower limit); on failure the page serves as built
      if (!r.ok) break;
      const j = await r.json();
      for (const f of j.features || []) {
        const p = f.properties || {}, v = parseFloat(p.value), t = Date.parse(p.time);
        if (isNaN(v) || isNaN(t) || t < cutoff) continue;
        const s = String(p.monitoring_location_id || "").slice(5), k = p.parameter_code === "00060" ? "f" : p.parameter_code === "00065" ? "h" : null;
        if (!k) continue;
        g[s] = g[s] || {};
        const q = Array.isArray(p.qualifier) ? p.qualifier.join(",") : (p.qualifier || "");
        if (!g[s][k] || Date.parse(g[s][k][1]) < t) { g[s][k] = q ? [v, p.time, q] : [v, p.time]; got++; }
      }
      next = ((j.links || []).find((l) => l.rel === "next") || {}).href;
    }
  }
  const m = Object.fromEntries(sites.map((x) => [x[0], [x[2], x[3]]]));
  if (!got && prev.t && JSON.stringify(m) === JSON.stringify(prev.m)) return; // nothing new and no new build: no KV write (free plan: 1,000 writes/day)
  await env.LIVE.put("live", JSON.stringify({ t: new Date().toISOString(), u: Object.fromEntries(sites.map((x) => [x[1], x[0]])), m, g }));
}
