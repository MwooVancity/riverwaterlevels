// Edge live layer, fetch-on-open (owner 2026-10-26: "ur not downloading shit"): nothing is pulled on a timer and nothing is stored.
// When a gauge page is opened, the worker asks USGS for THAT gauge's newest flow and gage height, keeps the answer in this Cloudflare
// location's cache for 3 minutes (the next reader there reuses it), and swaps it into the page with HTMLRewriter. Text the build derived
// from its own reading is stamped with that reading's time. Any error, a missing, older or flagged reading, or a non-gauge path serves the
// static page untouched: never older than the build, never broken. /live/<site>.json gives the browser the same answer.

const LATEST = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items";
const UA = "riverwaterlevels.com (https://riverwaterlevels.com/about/)";
const TTL_S = 180; // one USGS call per gauge per Cloudflare location per 3 min, only for pages someone opens
let SITES = null; // url -> [site, built reading time, time zone], from the built live-sites.json; kept for the life of this isolate

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    try {
      const lj = url.pathname.match(/^\/live\/(\d{8,15})\.json$/);
      if (lj) {
        const g = await latest(lj[1], env, ctx);
        return secure(new Response(JSON.stringify({ t: g ? g.at : null, g: g ? { [lj[1]]: g } : {} }), {
          headers: { "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=60" },
        }), url);
      }
      if (!url.pathname.startsWith("/river/")) return env.ASSETS.fetch(req);
      let res = await env.ASSETS.fetch(req);
      if (res.status !== 304 && (!res.ok || !(res.headers.get("content-type") || "").includes("text/html"))) return secure(res, url);
      const m = (await sites(env))[url.pathname];
      const g = m && await latest(m[0], env, ctx);
      // never swap a flagged (Ice, Equipment, ...) or sentinel reading: the built page prints the flag in words, the edge does not
      if (!g || !g.f || !(Date.parse(g.f[1]) > Date.parse(m[1])) || g.f[2] || !(g.f[0] > -999)) return secure(tag(res, m ? "static" : "static-unknown", g), url);
      if (res.status === 304) { // the browser holds the built copy but a newer reading exists: send the full page so it can be updated
        const h = new Headers(req.headers);
        h.delete("if-none-match");
        h.delete("if-modified-since");
        res = await env.ASSETS.fetch(new Request(req, { headers: h }));
      }
      return secure(tag(rewrite(res, g, m), "swapped", g), url);
    } catch (e) {
      return env.ASSETS.fetch(req);
    }
  },
};

async function sites(env) {
  if (!SITES) {
    const list = await (await env.ASSETS.fetch("https://riverwaterlevels.com/live-sites.json")).json(); // [[site, url, built iso, tz]]
    SITES = Object.fromEntries(list.map((x) => [x[1], [x[0], x[2], x[3]]]));
  }
  return SITES;
}

// newest flow (f) and gage height (h) for one gauge: [value, time, qualifier?]; from this location's cache when under TTL_S old
async function latest(site, env, ctx) {
  const key = new Request("https://riverwaterlevels.com/__usgs/" + site);
  const hit = await caches.default.match(key);
  if (hit) return hit.json();
  const r = await fetch(LATEST + "?monitoring_location_id=USGS-" + site + "&parameter_code=00060,00065&skipGeometry=true&properties=parameter_code,value,time,qualifier&f=json",
    { headers: env.USGS_API_KEY ? { "X-Api-Key": env.USGS_API_KEY, "User-Agent": UA } : { "User-Agent": UA } });
  if (!r.ok) return null;
  const j = await r.json(), g = { at: new Date().toISOString() }, cutoff = Date.now() - 8 * 86400000; // dead sensors return decades-old values
  for (const f of j.features || []) {
    const p = f.properties || {}, v = parseFloat(p.value), t = Date.parse(p.time);
    const k = p.parameter_code === "00060" ? "f" : p.parameter_code === "00065" ? "h" : null;
    if (!k || isNaN(v) || isNaN(t) || t < cutoff) continue;
    const q = Array.isArray(p.qualifier) ? p.qualifier.join(",") : (p.qualifier || "");
    if (!g[k] || Date.parse(g[k][1]) < t) g[k] = q ? [v, p.time, q] : [v, p.time];
  }
  ctx.waitUntil(caches.default.put(key, new Response(JSON.stringify(g), { headers: { "cache-control": "max-age=" + TTL_S } })));
  return g;
}

// _headers rules may not apply to responses that pass through this worker (Cloudflare docs), so gauge pages set them here when missing.
// Keep in step with templates/_headers (the /* block).
const SECURITY = {
  "x-content-type-options": "nosniff",
  "referrer-policy": "strict-origin-when-cross-origin",
  "strict-transport-security": "max-age=31536000",
  "x-frame-options": "DENY",
  "permissions-policy": "geolocation=(), camera=(), microphone=(), payment=(), usb=()",
};

function secure(res, url) {
  const o = new Response(res.body, res);
  for (const [k, v] of Object.entries(SECURITY)) if (!o.headers.has(k)) o.headers.set(k, v);
  if (url.hostname.endsWith(".workers.dev")) o.headers.set("x-robots-tag", "noindex"); // the workers.dev mirror is never indexed
  return o;
}

// x-rwl-edge says what the edge did with this page (swapped / static / static-unknown) and how old its USGS answer is, so the live gate can see it
function tag(res, what, g) {
  const o = new Response(res.body, res);
  o.headers.set("x-rwl-edge", what + (g && g.at ? "; live-age-s=" + Math.round((Date.now() - Date.parse(g.at)) / 1000) : "; live-age-s=none"));
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
  // every string is computed HERE, before streaming starts: a throw inside a handler mid-stream would cut the page off (HTMLRewriter docs)
  const [fv, ft] = g.f, tz = m[2], built = m[1], mins = (Date.now() - Date.parse(ft)) / 60000;
  const builtAt = local(built, tz), nowAt = local(ft, tz), flow = Math.round(fv).toLocaleString("en-US"), ageTxt = age(ft);
  const ab = "ab " + (mins <= 90 ? "fresh" : mins <= 360 ? "ageing" : "stale");
  const asofHtml = '<small class="asof"> (as of the ' + builtAt + " reading)</small>";
  const note = '<p id="lbn" class="src lf2">Flow and gage height at the top updated ' + nowAt + ". Charts, tables and comparisons below are as of the page build, " + builtAt + ".</p>";
  const stage = g.h && !g.h[2] && g.h[0] > -999 && Date.parse(g.h[1]) > Date.parse(built) ? Number(g.h[0]).toFixed(2) : null;
  const text = (s) => ({ element(e) { e.setInnerContent(s); } });
  const out = new HTMLRewriter()
    .on('span[data-live="flow"]', text(flow)) // same rounding as fmtc() in lib/common.py
    .on('span[data-live="lead"]', text(flow + " cfs"))
    // dv = text the build derived from its own reading (class word, trend, flood distance, forecast vs now): not recomputed here, so it carries its own time
    .on(".dv", { element(e) { e.append(asofHtml, { html: true }); } })
    .on('span[data-live="obs"]', text(nowAt))
    .on('span[data-live="age"]', { element(e) { e.setAttribute("data-t", ft); e.setInnerContent(ageTxt); } })
    .on("span.ab", { element(e) { e.setAttribute("class", ab); } })
    .on(".hero", { element(e) { e.after(note, { html: true }); } });
  if (stage) out.on('span[data-live="stage"]', text(stage));
  const r = out.transform(res);
  const o = new Response(r.body, r);
  o.headers.delete("etag");
  o.headers.set("cache-control", "public, max-age=0, must-revalidate");
  return o;
}
