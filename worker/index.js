// Edge live layer (plan approved 2026-10-26: readers' phones + one tiny "what changed" poll).
// A cron every 3 minutes asks USGS only which flow / gage height readings CHANGED since the last poll (last_modified cursor; Phase 0
// measured 20 changed rows of 105 in 10 min at 53 gauges, one national call covers the whole US) and merges them into ONE stored copy
// (KV "live"). It is the only writer and never steps a reading back. Every gauge page and /live/<site>.json read that copy: no USGS call
// on any page view, so people and crawlers cost our key nothing. Readers' browsers also ask USGS directly (lib/page.py LIVE_JS).
// Pages: HTMLRewriter swaps in the stored reading when it is newer than the build's; text the build derived from its own reading is
// stamped with that reading's time. Any error, a missing, older or flagged reading, or a non-gauge path serves the static page untouched.

const LATEST = "https://api.waterdata.usgs.gov/ogcapi/v1/collections/latest-continuous/items";
const UA = "riverwaterlevels.com (https://riverwaterlevels.com/about/)";
const CHUNK = 300; // ids per call; ponytail: past ~1,500 gauges switch to one national query filtered in code (Phase 0: 1 call, 804 KB / 10 min)
const OVERLAP_MS = 120000; // the cursor steps back 2 min so a row USGS commits late is not missed (the merge drops repeats)

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(poll(env));
    ctx.waitUntil(build(env, new Date(event.scheduledTime)));
  },

  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    try {
      const lj = url.pathname.match(/^\/live\/(\d{8,15})\.json$/);
      if (lj) {
        const L = await stored(env, lj[1]), g = L && L.g && L.g[lj[1]];
        const o = new Response(JSON.stringify({ t: L ? L.t : null, g: g ? { [lj[1]]: g } : {} }), {
          headers: { "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=60" },
        });
        if (L && L.rem != null) o.headers.set("x-rwl-usgs-remaining", String(L.rem)); // our key's hourly budget after the last poll (watchdog reads it)
        const d = await env.LIVE.get("dispatch", { cacheTtl: 300 });
        if (d) o.headers.set("x-rwl-build-trigger", d); // the last time the cron asked GitHub for a build, and GitHub's answer
        return secure(o, url);
      }
      if (!url.pathname.startsWith("/river/")) return perm(await env.ASSETS.fetch(req));
      let res = await env.ASSETS.fetch(req);
      if (res.status === 307) return secure(perm(res), url);
      if (res.status === 404) { // a river with one gauge has no hub page: its address leads to that gauge (build.py writes the map)
        const to = (await (await env.ASSETS.fetch("https://riverwaterlevels.com/single-rivers.json")).json())[url.pathname];
        if (to) return secure(new Response(null, { status: 301, headers: { location: to } }), url);
      }
      if (res.status !== 304 && (!res.ok || !(res.headers.get("content-type") || "").includes("text/html"))) return secure(res, url);
      const m = (await sites(env))[url.pathname], L = m ? await stored(env, m[0]) : null; // sites() is cached per isolate; only a gauge page reads the stored copy
      const g = m && L && L.g && L.g[m[0]];
      // never swap a flagged (Ice, Equipment, ...) or sentinel reading: the built page prints the flag in words, the edge does not
      if (!g || !g.f || !(Date.parse(g.f[1]) > Date.parse(m[1]) || (Date.parse(g.f[1]) === Date.parse(m[1]) && g.f[0] !== m[3])) || g.f[2] || !(g.f[0] > -999)) return secure(tag(res, m ? "static" : "static-unknown", L), url);
      if (res.status === 304) { // the browser holds the built copy but a newer reading exists: send the full page so it can be updated
        const h = new Headers(req.headers);
        h.delete("if-none-match");
        h.delete("if-modified-since");
        res = await env.ASSETS.fetch(new Request(req, { headers: h }));
      }
      return secure(tag(rewrite(res, g, m), "swapped", L), url);
    } catch (e) {
      return env.ASSETS.fetch(req);
    }
  },
};

// Assets answer the trailing-slash and index.html redirects with 307; the address change is permanent, so Google should move the URL's credit (SEO audit 2026-11-05)
function perm(res) {
  return res.status === 307 ? new Response(null, { status: 301, headers: { location: res.headers.get("location") } }) : res;
}

let SITES = null; // url -> [site, built reading time, time zone], from the built live-sites.json; kept for the life of this isolate

// The hourly build (2026-10-26 review: GitHub's own schedule ran 7 of 52 refreshes in a day; this cron runs on time). Once an hour, at the
// first tick of the hour, when the deployed build is over 40 min old, ask GitHub to start refresh.yml. GitHub's one-run-at-a-time group
// queues it behind a running build. GH_DISPATCH_TOKEN can only start workflows on this repo; without it nothing happens.
async function build(env, now) {
  if (!env.GH_DISPATCH_TOKEN || now.getUTCMinutes() >= 3) return;
  await start(env, "watchdog.yml");
  const s = await (await env.ASSETS.fetch("https://riverwaterlevels.com/status.json")).json();
  if (now - Date.parse(s.built_at) < 40 * 60000) return;
  const r = await start(env, "refresh.yml");
  await env.LIVE.put("dispatch", now.toISOString() + " " + r.status + " " + (r.headers.get("github-authentication-token-expiration") || "")); // 204 = GitHub accepted; one write an hour at most
}

async function start(env, file) { // called only from build(): the cron
  return fetch("https://api.github.com/repos/MwooVancity/riverwaterlevels/actions/workflows/" + file + "/dispatches", {
    method: "POST",
    headers: { authorization: "Bearer " + env.GH_DISPATCH_TOKEN, accept: "application/vnd.github+json", "user-agent": UA },
    body: JSON.stringify({ ref: "main" }),
  });
}

async function sites(env) {
  if (!SITES) {
    const list = await (await env.ASSETS.fetch("https://riverwaterlevels.com/live-sites.json")).json(); // [[site, url, built iso, tz]]
    SITES = Object.fromEntries(list.map((x) => [x[1], [x[0], x[2], x[3], x[4]]]));
  }
  return SITES;
}

// One gauge out of the stored copy without parsing all of it (scale debate 2026-11-07: a whole-copy JSON.parse on every page request grows with the
// gauge count; p99 8.9 ms at 142 gauges against the 10 ms CPU limit). The copy is written by poll() as {"t":..,"cur":..,"rem":..,"g":{"<site>":{"f":[..],"h":[..]}}}:
// a site id is digits, its value object holds only arrays, so the first "}" after '"<site>":{' closes it.
async function stored(env, site) {
  const text = await env.LIVE.get("live", { type: "text", cacheTtl: 30 });
  return text ? slice(text, site) : null;
}

function slice(text, site) {
  const t = (text.match(/"t":"([^"]*)"/) || [])[1] || null;
  const rem = (text.match(/"rem":(-?\d+)/) || [])[1];
  let one = null;
  const i = site ? text.indexOf('"' + site + '":{') : -1;
  if (i >= 0) {
    const s0 = text.indexOf("{", i), e = text.indexOf("}", s0);
    try { one = JSON.parse(text.slice(s0, e + 1)); } catch (x) { one = null; }
  }
  return { t, rem: rem == null ? null : Number(rem), g: one ? { [site]: one } : {} };
}

// the cron: ask USGS what changed since the cursor, merge, write once if anything changed
async function poll(env) {
  const list = await (await env.ASSETS.fetch("https://riverwaterlevels.com/live-sites.json")).json();
  const ids = list.map((x) => x[0]).filter((s) => /^\d+$/.test(s)); // agency lakes (CDEC-SHA, TWDB-travis) are on the list for the Python tools; USGS gets only its own ids
  const prev = (await env.LIVE.get("live", { type: "json" })) || {};
  const g = {};
  for (const s of ids) if (prev.g && prev.g[s]) g[s] = prev.g[s]; // gauges no longer live drop out
  const since = prev.cur ? new Date(Date.parse(prev.cur) - OVERLAP_MS).toISOString() : null; // first run: everything
  const cutoff = Date.now() - 8 * 86400000; // the service returns decades-old values for dead sensors
  let changed = 0, cur = prev.cur || null, rem = prev.rem;
  for (let i = 0; i < ids.length; i += CHUNK) {
    let next = LATEST + "?monitoring_location_id=" + ids.slice(i, i + CHUNK).map((x) => "USGS-" + x).join(",") + "&parameter_code=00060,00065"
      + (since ? "&last_modified=" + since + "/.." : "") + "&skipGeometry=true&properties=monitoring_location_id,parameter_code,value,time,qualifier,last_modified,unit_of_measure&limit=10000&f=json";
    for (let page = 0; next && page < 5; page++) {
      const r = await fetch(next, { headers: env.USGS_API_KEY ? { "X-Api-Key": env.USGS_API_KEY, "User-Agent": UA } : { "User-Agent": UA } });
      if (r.headers.get("x-ratelimit-remaining")) rem = Number(r.headers.get("x-ratelimit-remaining"));
      if (!r.ok) return; // keep the stored copy and the cursor as they are; the next poll retries
      const j = await r.json();
      for (const f of j.features || []) {
        const p = f.properties || {}, v = parseFloat(p.value), t = Date.parse(p.time);
        if (p.last_modified && (!cur || p.last_modified > cur)) cur = p.last_modified;
        const k = p.parameter_code === "00060" ? "f" : p.parameter_code === "00065" ? "h" : null;
        const s = String(p.monitoring_location_id || "").slice(5);
        if (!k || isNaN(v) || isNaN(t) || t < cutoff) continue;
        if (String(p.unit_of_measure || "").toLowerCase() !== (k === "f" ? "ft^3/s" : "ft")) continue; // edge test 2026-11-07: a unit change at USGS would swap m^3/s into a cfs page; same allow-list as lib/core.py UNIT_OF
        const q = Array.isArray(p.qualifier) ? p.qualifier.join(",") : (p.qualifier || "");
        g[s] = g[s] || {};
        const o = g[s][k], ot = o ? Date.parse(o[1]) : -Infinity;
        if (ot < t || (ot === t && (o[0] !== v || (o[2] || "") !== q))) { g[s][k] = q ? [v, p.time, q] : [v, p.time]; changed++; } // never steps back; a same-time correction (value or flag) replaces
      }
      next = ((j.links || []).find((l) => l.rel === "next") || {}).href;
    }
  }
  if (!changed && prev.t && Object.keys(g).length === Object.keys(prev.g || {}).length) return; // nothing new: no KV write (free plan: 1,000 writes/day)
  await env.LIVE.put("live", JSON.stringify({ t: new Date().toISOString(), cur, rem, g }));
}

// _headers rules may not apply to responses that pass through this worker (Cloudflare docs), so gauge pages set them here when missing.
// Keep in step with templates/_headers (the /* block).
const SECURITY = {
  "x-content-type-options": "nosniff",
  "referrer-policy": "strict-origin-when-cross-origin",
  "strict-transport-security": "max-age=31536000",
  "x-frame-options": "DENY",
  "permissions-policy": "geolocation=(self), camera=(), microphone=(), payment=(), usb=()",
};

function secure(res, url) {
  const o = new Response(res.body, res);
  for (const [k, v] of Object.entries(SECURITY)) if (!o.headers.has(k)) o.headers.set(k, v);
  if (url.hostname.endsWith(".workers.dev")) o.headers.set("x-robots-tag", "noindex"); // the workers.dev mirror is never indexed
  return o;
}

// x-rwl-edge says what the edge did with this page (swapped / static / static-unknown) and how old the stored copy is, so the live gate can see it
function tag(res, what, L) {
  const o = new Response(res.body, res);
  o.headers.set("x-rwl-edge", what + (L && L.t ? "; live-age-s=" + Math.round((Date.now() - Date.parse(L.t)) / 1000) : "; live-age-s=none"));
  return o;
}

function local(iso, tz) {
  return new Date(iso).toLocaleString("en-US", { timeZone: tz, month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }).replace(/\s/g, "\u00a0").replace(/,\u00a0/g, ", "); // as tzl() in lib/core.py writes a time: no-break spaces (Intl gives narrow ones) except after the comma, so a swapped-in time matches the build's
}

// The age chip's colour cut-offs in minutes: STALE_H "chip_fresh" and "chip_ageing" in lib/core.py, times 60. The worker cannot import Python; check.py --selftest compares this line with STALE_H.
const AGE_CHIP_MIN = [90, 360];

// AGE_FN in lib/page.py, character for character (check.py --selftest): the edge, the page script and age_text() print one age
function age(d){var m=Math.round((Date.now()-d)/60000);return m<180?m+' min':m<2880?Math.round(m/60)+' h':Math.round(m/1440)+' d'}

function rewrite(res, g, m) {
  // every string is computed HERE, before streaming starts: a throw inside a handler mid-stream would cut the page off (HTMLRewriter docs)
  const [fv, ft] = g.f, tz = m[2], built = m[1], mins = (Date.now() - Date.parse(ft)) / 60000;
  const builtAt = local(built, tz), nowAt = local(ft, tz), flow = Math.abs(fv) >= 1000 ? Number(fv.toPrecision(3)).toLocaleString("en-US") : Math.abs(fv) < 1 && fv !== 0 ? fv.toFixed(2) : Math.round(fv).toLocaleString("en-US"), ageTxt = age(Date.parse(ft));
  const ab = "ab " + (mins <= AGE_CHIP_MIN[0] ? "fresh" : mins <= AGE_CHIP_MIN[1] ? "ageing" : "stale");
  const stage0 = g.h && !g.h[2] && g.h[0] > -999 && Date.parse(g.h[1]) > Date.parse(built);
  const note = '<p id="lbn" class="src lf2">' + (stage0 ? "Flow and gage height" : "Flow") + " at the top updated " + nowAt + ". Charts, tables and comparisons below are as of the page build, " + builtAt + ".</p>";
  const stage = stage0 ? Number(g.h[0]).toFixed(2) : null;
  const text = (s) => ({ element(e) { e.setInnerContent(s); } });
  // a tile sparkline's end dot at the live value, on the build's own scale (lib/ui.py spark); off the scale it sits on the edge, the number says how far
  const sparkDot = (v) => ({ element(e) { const lo = Number(e.getAttribute("data-lo")), sp = Number(e.getAttribute("data-span")), h = Number(e.getAttribute("data-h")); if (sp > 0 && h > 0 && Number.isFinite(v)) e.setAttribute("cy", Math.max(1, Math.min(h - 1, 3 + (1 - (v - lo) / sp) * (h - 6))).toFixed(1)); } });
  const out = new HTMLRewriter()
    .on('span[data-live="flow"]', text(flow)) // same rounding as fmtc() in lib/common.py
    .on('circle[data-k="flow"]', sparkDot(fv)) // the tile's 24 h line ends at the live reading, not the build's (owner 2026-11-09)
    .on('span[data-live="lead"]', text(flow + " cfs"))
    // dv = text the build derived from its own reading (class word, trend, flood distance, forecast vs now): not recomputed here, so it carries its own time
    .on('span[data-live="obs"]', text(nowAt))
    .on("span[data-cf]", text(flow))
    .on("span[data-co]", text(nowAt))
    .on('span[data-live="age"]', { element(e) { e.setAttribute("data-t", ft); e.setInnerContent(ageTxt); } })
    .on("span.ab", { element(e) { e.setAttribute("class", ab); } })
    .on("p.answer", { element(e) { e.after(note, { html: true }); } }); // said once, right under the answer it qualifies (was 5 stamps)
  if (stage) out.on('circle[data-k="stage"]', sparkDot(Number(stage))).on('span[data-live="stage"]', text(stage)).on("span[data-cs]", text(stage)).on('span[data-live="stageobs"]', text(local(g.h[1], tz)))
    // the gage tile's flood bar: its tick follows the live stage (a static picture must never disagree with the live number); only ticks the build marked live (no datum gap)
    .on("b.lad-now[data-lo]", { element(e) { const lo = Number(e.getAttribute("data-lo")), sp = Number(e.getAttribute("data-span")); if (sp > 0) e.setAttribute("style", "left:" + Math.max(0, Math.min(100, (Number(stage) - lo) / sp * 100)).toFixed(2) + "%"); } });
  const r = out.transform(res);
  const o = new Response(r.body, r);
  o.headers.delete("etag");
  o.headers.set("cache-control", "public, max-age=0, must-revalidate");
  return o;
}
