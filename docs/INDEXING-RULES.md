# Indexing: which pages Google may see

The switch is `data/index-allow.json`: `open` (master), `site_pages` (home, state, about), `allow` (gauge page URLs). `lib/indexing.py` turns it into the robots meta tag and the sitemap; `check.py` refuses a build when an allowed page has no SHIP review or the sitemap and allow list disagree.

- `python -I tools/open_wave.py N` dry run of the next N pages (queue score, live, SHIP). `--apply` writes them. `--pull /river/x/y/` removes a page (kill switch).
- `python -I tools/index_live.py` reads the live site and reports every page whose robots tag disagrees with the allow list. Run it after every deploy.
- A page may be opened only when it is live, has a signed SHIP in `data/reviews.json` for the live template, and `_truth.json` is ok and under 6 h old.

Pace: the owner decides (2026-10-21: "index asap"). Pull a page the same hour a wrong or stale number is found on it without a label. Record each opening in `docs/OPEN-ITEMS.md` with date, URLs and template hash.
