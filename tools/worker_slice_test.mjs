// Self-test of worker/index.js slice() and siteOf(): one gauge out of the stored live copy, one page's row out of live-sites.json, without parsing
// all of either (node tools/worker_slice_test.mjs; gates.py runs it).
import { readFileSync } from "node:fs";
const src = readFileSync(new URL("../worker/index.js", import.meta.url), "utf8");
const fnOf = (name) => {
  const body = src.slice(src.indexOf("function " + name + "("));
  return new Function(body.slice(0, body.search(/\r?\n}\r?\n/) + 3) + "; return " + name + ";")();
};
const slice = fnOf("slice"), siteOf = fnOf("siteOf"), future = fnOf("future");
const n0 = Date.parse("2026-11-10T12:00:00Z");
if (!future(n0 + 2 * 3600000, n0) || future(n0 + 5 * 60000, n0) || future(n0 - 60000, n0)) { console.error("FAIL a reading 2 h ahead was stored, or 5 min of clock skew / a past reading was dropped (gate audit 0a)"); process.exit(1); }
const g = {}; for (let i = 0; i < 3000; i++) g[String(10000000 + i)] = { f: [i, "2026-11-07T18:00:00+00:00"], h: [1.5, "2026-11-07T18:00:00+00:00", "Ice"] };
g["07032000"] = { f: [246000, "2026-11-07T18:00:00+00:00"] };
const text = JSON.stringify({ t: "2026-11-07T18:57:13.242Z", cur: "2026-11-07T18:50:00Z", rem: 812, g });
const want = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) { console.error("FAIL", m, JSON.stringify(a)); process.exit(1); } };
want(slice(text, "07032000"), { t: "2026-11-07T18:57:13.242Z", rem: 812, g: { "07032000": g["07032000"] } }, "one gauge");
want(slice(text, "10000001").g["10000001"], g["10000001"], "a gauge with a flag");
want(slice(text, "99999999").g, {}, "an absent gauge");
want(slice(text, "0703200").g, {}, "a prefix of a real id is not that gauge");
want(slice(JSON.stringify({ t: "x", g: {} }), "1").rem, null, "no rem");

// live-sites.json as build.py writes it (json.dump, separators=(",", ":")): [site, url, built iso, tz, built flow]; the old Worker built a url map of [site, iso, tz, flow]
const rows = [["01234567", "/river/a/b/", "2026-11-07T18:00:00+00:00", "America/New_York", 146.0], ["CDEC-SHA", "/lake/shasta-lake/", "2026-11-07T17:00:00+00:00", "America/Los_Angeles", null],
  ["07032000", "/river/mississippi-river/memphis/", null, "America/Chicago", 246000], ["07032001", "/river/a/b/c/", "2026-11-07T18:00:00+00:00", "America/Chicago", -0.5]];
for (let i = 0; i < 3000; i++) rows.push([String(20000000 + i), "/river/r" + i + "/g/", "2026-11-07T18:00:00+00:00", "America/Denver", i]);
const list = JSON.stringify(rows), old = Object.fromEntries(rows.map((x) => [x[1], [x[0], x[2], x[3], x[4]]]));
for (const u of ["/river/a/b/", "/lake/shasta-lake/", "/river/mississippi-river/memphis/", "/river/a/b/c/", "/river/r2999/g/", "/river/r0/g/"]) want(siteOf(list, u), old[u], "row of " + u);
want(siteOf(list, "/river/a/"), null, "a prefix of a page is not that page");
want(siteOf(list, "/river/zz/"), null, "an absent page");
want(siteOf(list, "America/Denver"), null, "a time zone is not a page");
want(siteOf("<!doctype html>", "/river/a/b/"), null, "an error page instead of the list");
console.log("worker slice selftest OK");
