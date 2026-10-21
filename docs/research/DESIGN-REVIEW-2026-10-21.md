# Design review 2026-10-21: riverwaterlevels.com vs Lakebrief

Screenshots and `measurements.json` (getComputedStyle dump, every page x viewport x scheme) in `docs/research/design/`:

| file | what |
|---|---|
| `ours-potomac-phone-light.png`, `-dark.png`, `-phone-light-full.png` | Potomac at Little Falls, 390x844 |
| `ours-potomac-desktop-light.png`, `-dark.png`, `-desktop-light-full.png` | same, 1280x900 |
| `ours-columbia-phone-*.png`, `ours-columbia-desktop-*.png` | Columbia at The Dalles |
| `lb-powell-phone-*.png`, `lb-powell-desktop-*.png` | lakebrief.com/lake/lake-powell/water |
| `lb-lanier-phone-*.png`, `lb-lanier-desktop-dark.png` | lakebrief.com/lake/lanier/water (desktop-light timed out on networkidle; dark shot is identical because Lakebrief has no dark mode) |

Lakebrief did not block. All four pages returned 200.

## VERDICT

No. Ours does not look human-made and it is not as good as Lakebrief, and the screenshots show why in one glance: Lakebrief is one system (one blue, one grey, three faces each with one job, white 12 px cards on a pale blue page, 24 px inside every card, label / number / unit / one line, in that order, every time). Ours is five redesigns stacked in one 281-line stylesheet (`site.css` lines 50, 86, 102, 134, 232 and the final `body .tile` "editorial flat" override at line 247) and the page shows the seams: Georgia old-style numerals at 49.6 px that sit unevenly ("3.33" renders with a hanging point, "4,810" with a dropped 4), a unit that wraps under the number on the Columbia page, three underlined "chips" that are neither pills nor sentences, the data age stated seven ways on one screen, 27 words of NWS prose under a 50 px number, 11 named hues, 0 px radius on everything, a text-only sparkline floating in a 588 px column on desktop, and a dark mode that is pure #0a0a0b. None of that is ugly on its own. Together it reads as a machine that kept adding rules. What already beats Lakebrief: honest freshness ("56 min old", Lakebrief silently shows a 3-day-old reading), the 96-year percentile bar, the normal-range answer in words, and a real dark mode. Keep the content, rebuild the skin to one spec.

## DEFECTS (worst first)

1. **Numerals in a serif with old-style figures.** `body .tile b` = Georgia 700, 49.6 px (3.1rem), `letter-spacing:-.025em`. Georgia's figures descend, so "4,810" and "3.33" look uneven and the decimal point sits mid-height (see `ours-potomac-phone-light.png`, y 462). Lakebrief: Space Grotesk 700, 48 px, lining tabular, `-0.96px` tracking, same on every tile. Fix: `.tile b{font-family:"Space Grotesk",system-ui,sans-serif;font-weight:700;font-size:3rem;line-height:1;letter-spacing:-.02em;font-variant-numeric:lining-nums tabular-nums}` and load the face (Google Fonts, one weight). If no webfont is allowed: `font-family:system-ui` with `font-variant-numeric:lining-nums tabular-nums` and drop Georgia from `.tile b`, `.fc b`, `.sn b`, `.chip b` (site.css 21, 96, 97).

2. **Unit wraps under the number.** Columbia phone: "81,100" at 49.6 px fills the 163 px column and "cfs" drops to its own line at y 525, then the sparkline (`ours-columbia-phone-light.png`). Lakebrief: one column on phone, 350 px wide, number never fights for width. Fix: on `max-width:760px` make `.hero2{grid-template-columns:1fr}` (one tile per row) and `.tile b{font-size:2.6rem}`; or keep two columns and `.tile.flow b,.tile.stage b{font-size:2.2rem}` with `white-space:nowrap` on `.tile b`.

3. **No tile shape.** `body .tile` = `border-radius:0; background:transparent; border-top:1px solid #e3e6eb; padding:14px 0 10px` (site.css 248-250). Two tiles in a row share nothing but a hairline; on desktop each is 588 px wide with a 34 px sparkline stretched across the whole width and empty space right of the number. Lakebrief: `background:#fff; border:1px solid #e6edf3; border-radius:12px; padding:24px` on a `#f4f9fd` page, four 298 px tiles of 188 px. Fix: delete the `body .card,body .blk,body .tile...{border-radius:0;...}` line (site.css 248) and the four `body .tile` lines after it; set `.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;box-shadow:none}` with `--card:#fff` and `--bg:#f4f8fc` in light; desktop `.hero2{grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}`.

4. **Data age stated seven ways on the first two screens** (Potomac): "observed Oct 21, 8:50 AM EDT", chip "56 min old", "(as of 6:50 AM)" x2 in the answer line, "The flow above is newer than this comparison, which is as of Oct 21, 6:50 AM EDT", then the rule "Flow and gage height at the top updated Oct 21, 8:50 AM EDT. Charts, tables and comparisons below are as of the page build, Oct 21, 6:50 AM EDT." Lakebrief: once, "Last reading 18/10/2026, 11:00:00". Fix (markup, `lib/render.py` / `lib/ui.py`): keep the chip "56 min old" and the single "observed Oct 21, 8:50 AM EDT"; delete "(as of H:MM AM)" from `.answer span` text; delete the two "newer than this comparison" sentences; keep the one build-time line but move it to the Sources fold.

5. **Prose under numbers.** First phone screen word counts under each number: flow 6 ("cfs = cubic feet per second"), gage 27 (NWS impact sentence), normal 11. Lakebrief: 5, 0, 5, each one line, 12 px. Fix: `.tile>small` is ONE line, max 7 words, `font-size:.75rem;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis`. Gage tile line becomes "Caution for boaters at 3.5 ft" (6 words); the full NWS sentence moves to the flood-impacts block. Delete "cfs = cubic feet per second" (the `<abbr title>` already carries it) and put "7 days" or "Falling 5% in 6 h" there instead.

6. **The three answer "chips" are neither chips nor sentences.** `.answer span` = 15.2 px 600, underline 2 px in a different hue each (`#a85a00`, `#6b3fa0`, `#e3e6eb`), one wraps to two lines on the phone. Lakebrief has no chips; it has one 12 px breadcrumb and a two-line sentence under the H1. Fix: either one sentence (`.sub`, 14.4 px, `#5d6470`): "Falling, levelling off. Above normal for Oct 21. No active NWS alerts." or real pills: `.answer span{font:500 .8rem system-ui;padding:6px 12px;border-radius:99px;background:#eef3f9;color:#0f2a4a;border:0}` with one 8 px dot in the family colour, never an underline. Pick one; delete the `body .answer` override lines (site.css 262-264).

7. **Label style is three systems.** Tile labels `.7rem` 600 uppercase `letter-spacing:.12em` with an 8 px coloured dot; `.rc .rt` `.7rem` 400 `.05em` no dot; `th` `.72rem` `.06em`; `.blk>h2 .tag` `.75rem` `.1em`. Lakebrief: one label class (`font-label-caps`): Space Grotesk 400, 16 px on phone / 20 px desktop, uppercase, `#475569`, no tracking, no dot. Fix: one rule `.lbl{font:500 .75rem/1.3 system-ui;letter-spacing:.08em;text-transform:uppercase;color:#5d6470}` applied to `.tile>span`, `.rc .rt`, `th`, `.chip span`, `.tag`; delete `body .tile>span::before` (the dot) unless the dot means something a legend explains.

8. **Colour count.** 49 distinct computed colours on the Potomac phone (11 named hues in `:root`: accent, navy, amber, good, low, hi, warn, f-now, f-fc, f-rec, f-area, f-safe). Lakebrief: 28 computed, 1 brand blue `#1565a8`, 1 green `#1b7f3b`, 1 red `#ba1a1a`, greys. Fix: collapse to `--accent:#1d5fa8` (now, links, active tab), `--ink:#0f1d2b`, `--mut:#5d6470`, `--line:#e3e6eb`, `--card:#fff`, `--bg:#f4f8fc`, plus `--low:#a85a00`, `--hi:#6b3fa0`, `--warn:#b3261e` for the percentile bar and alerts only. Delete `--f-fc/--f-rec/--f-area/--f-safe` and `--navy`, `--amber` (site.css 232-233).

9. **H1 and brand in Georgia, everything else system-ui, number in Georgia, label in system-ui**: four role switches in 300 px. Lakebrief also uses three faces but each has one job (Fraunces = H1 and brand only; Inter = body; Space Grotesk = labels and numbers). Fix: Georgia stays for `h1` and `.brand` only (after defect 1); nothing else serif.

10. **Dark mode is pure black.** `--bg:#0a0a0b`, `--ink:#f2f2f3`, cards transparent, so the page is text on black with hairlines (`ours-potomac-phone-dark.png`). Lakebrief has no dark mode (its "dark" shot is the light page). Fix: `--bg:#0f1720;--card:#16202b;--line:#263241;--ink:#e6edf3;--mut:#9aa7b4;--accent:#6aa9ec`; keep the 12 px card.

11. **Desktop header line.** 1280 px: brand 18.4 px Georgia, "Rivers About" tabs, search 210 px, theme button `◐` as a text glyph in a 44 px square with `border-radius:0`. Lakebrief: brand + a location pill + four tabs, one active in a `#e8f1fa` rounded tab, no theme button. Fix: `.themebtn{border-radius:99px;width:40px;height:40px}` with an SVG moon, delete the `body .themebtn{border-radius:0}` entry (site.css 267); tabs `.tabs a.on{background:#e8f1fa;border-radius:8px}`.

12. **Percentile bar legend and footnote repeat the number.** "Above normal / Higher than 80% of the 96 years / that is the 80th percentile; normal is between the 25th and 75th" plus a three-swatch legend plus Lower/Typical/Higher. Fix: keep the headline, the one standfirst sentence and the bar with its three axis words; delete `.dleg` and the "That is the 80th percentile..." sentence (keep "Estimated from the trailing 24 h mean (5,348 cfs) against 96 years of USGS daily statistics for Oct 21" in the Sources fold).

## TILE SPEC

One rule for every stat tile (`.tile`, `.rc`, `.fc`, `.sn`, `.chip`): all become `.tile`.

```
.tile{display:flex;flex-direction:column;gap:6px;background:var(--card);border:1px solid var(--line);
      border-radius:12px;padding:20px;min-height:148px;min-width:0}
.tile>.lbl  {font:500 .75rem/1.3 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
.tile>b     {display:flex;align-items:baseline;gap:8px;font:700 3rem/1 "Space Grotesk",system-ui,sans-serif;
             letter-spacing:-.02em;color:var(--ink);font-variant-numeric:lining-nums tabular-nums;white-space:nowrap}
.tile>b>small{font:500 1rem/1 system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:var(--mut)}
.tile>.line {font:400 .8rem/1.4 system-ui,sans-serif;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile>time  {font:400 .72rem/1.3 system-ui,sans-serif;color:var(--mut);margin-top:auto}
.tile svg.spark{height:28px;width:100%;color:var(--accent);margin:2px 0}
```

Order inside the tile, always: label, number+unit, (sparkline or bar), one line (max 7 words), time ("8:50 AM EDT", once). Number to unit ratio 3:1 (48 px : 16 px). Phone (`max-width:760px`): `.tile{padding:16px;min-height:132px}`, `.tile>b{font-size:2.4rem}`; the flow and gage tiles go one per row (`.hero2{grid-template-columns:1fr}`) or, if two per row is kept, `font-size:2rem`. Desktop: `.hero2{grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}`; all tiles in a row share `min-height`, nothing stretches to fill. Colour inside a tile: ink number, grey label, accent sparkline. Directional colour only on the number of the change tile (`--low` falling, `--hi` rising).

## FIRST SCREEN SPEC (390 x 844)

Measured now (Potomac): nav 0-60, search bar 64-104 (40 px, second row), crumb 131, H1 182-245, meta 272-291, three chips 310-416, tile row 428-669 (241 px), "Is this normal" 684-800, bottom tab bar 788-844. Three different hierarchies before the first number; the first number appears at y 462.

Target, in order, with heights:

| y | h | element | spec |
|---|---|---|---|
| 0 | 56 | nav | brand 18 px Georgia 700 + search icon button 40x40 + theme button 40x40 (no second row; the search field opens on tap) |
| 56 | 16 | gap | page bg `#f4f8fc` from here down |
| 72 | 18 | crumb | "Potomac River, MD" 12 px 500 uppercase `.08em` `#5d6470` |
| 94 | 72 | H1 | "Little Falls water level" 28 px/1.15 Georgia 700, two lines max |
| 170 | 40 | standfirst | one sentence, 14.4 px/1.4 `#5d6470`: "Falling and levelling off, above normal for Oct 21, no NWS alerts. Observed 8:50 AM EDT (56 min ago)." |
| 222 | 148 | tile 1 | LATEST FLOW 4,810 CFS, sparkline, "Falling 5.2% in 6 h", 8:50 AM EDT |
| 382 | 148 | tile 2 | GAGE HEIGHT 3.33 FT, sparkline, "Caution for boaters at 3.5 ft" |
| 542 | 148 | tile 3 | IS THIS NORMAL? "Above normal" 28 px (words, not number), percentile bar 12 px with Lower/Typical/Higher, "Higher than 80% of 96 years" |
| 702 | 86 | tile 4 top | NWS FORECAST 3.2 FT, "Oct 21, 8:00 AM" (cut by the fold; that is fine) |
| 788 | 56 | tab bar | Now / Forecast / History / Data / Area, 12 px 600, icons 20 px, active `#1d5fa8` |

First number at y 262 (was 462). Nothing collapsed, three questions answered above the fold, one statement of the data age.

## KEEP

- The content order (how much, is it normal, forecast, alerts) and the two-question rows.
- "56 min old" freshness chip; Lakebrief shows a 3-day-old reading with no warning. Keep the chip, drop the other six statements.
- Percentile bar against 96 / 148 years of USGS daily stats with the words "Above normal"; nothing on Lakebrief answers "is this normal".
- Sparklines in the tiles (Lakebrief has none above the fold).
- Dark mode exists; only its values need changing.
- Bottom tab bar on the phone; same pattern as Lakebrief and it works.
- Breadcrumb, skip link, 44 px tap targets, `<abbr>` on units, exact USGS gauge id in the meta line.
- The family-colour idea (blue now, teal forecast, violet record, green area, red safety) as a dot on a section heading; not as tile borders, backgrounds and chip underlines.

## NOT CHECKED

- Lakebrief Lanier desktop light (networkidle timeout; dark shot stands in and is the same page).
- Real devices and real fonts: Playwright Chromium on Windows; `system-ui` renders as Segoe UI here, as SF on iPhone, so measured sizes hold but glyph shapes differ.
- Pages below the first two screens (history tables, maps, forecast rail, sources fold) beyond the full-page PNGs; no per-block measurements there.
- Lakebrief's dashboard and forecast tabs; only `/water` pages.
- Load time, CLS, font loading flashes.
- Whether `lib/render.py` / `lib/ui.py` share a tile builder (the markup fixes in defects 4, 5, 12 are written as text, not line numbers).
- Accessibility contrast of the proposed dark values (not run through a checker).
