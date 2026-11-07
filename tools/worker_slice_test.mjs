// Self-test of worker/index.js slice(): one gauge out of the stored live copy without parsing all of it (node tools/worker_slice_test.mjs; gates.py runs it).
import { readFileSync } from "node:fs";
const src = readFileSync(new URL("../worker/index.js", import.meta.url), "utf8");
const body = src.slice(src.indexOf("function slice(text, site) {"));
const fn = body.slice(0, body.search(/\r?\n}\r?\n/) + 3);
const slice = new Function(fn + "; return slice;")();
const g = {}; for (let i = 0; i < 3000; i++) g[String(10000000 + i)] = { f: [i, "2026-11-07T18:00:00+00:00"], h: [1.5, "2026-11-07T18:00:00+00:00", "Ice"] };
g["07032000"] = { f: [246000, "2026-11-07T18:00:00+00:00"] };
const text = JSON.stringify({ t: "2026-11-07T18:57:13.242Z", cur: "2026-11-07T18:50:00Z", rem: 812, g });
const want = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) { console.error("FAIL", m, JSON.stringify(a)); process.exit(1); } };
want(slice(text, "07032000"), { t: "2026-11-07T18:57:13.242Z", rem: 812, g: { "07032000": g["07032000"] } }, "one gauge");
want(slice(text, "10000001").g["10000001"], g["10000001"], "a gauge with a flag");
want(slice(text, "99999999").g, {}, "an absent gauge");
want(slice(text, "0703200").g, {}, "a prefix of a real id is not that gauge");
want(slice(JSON.stringify({ t: "x", g: {} }), "1").rem, null, "no rem");
console.log("worker slice selftest OK");
