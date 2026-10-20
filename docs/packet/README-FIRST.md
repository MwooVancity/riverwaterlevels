# README FIRST: how to use this packet (one zip, four separate chats)

This zip is a review packet for **riverwaterlevels.com**, a US river-conditions website built by one non-coder owner with an AI assistant. The owner wants an independent, fresh look at the whole project, including whether the project's own review prompts and gates are asking the right questions. Earlier prompts were written by the same assistant that built the site, so they were narrow and anchored on its own beliefs. This packet is built to avoid that.

## The four passes (open a NEW chat for each; upload the zip once per chat; paste one prompt)
| Pass | Prompt file | What it is for | Reads |
|---|---|---|---|
| 1 | `prompts/PROMPT-1-unanchored.md` | Big picture and strategy. No project conclusions. Is this the right product, what could make it wrong, what would make it number one. | `00-CONTEXT.md`, `MANIFEST.md`, a few `site/` pages, `evidence/competitors/`, `evidence/our-screens/`, `code/CLAUDE.md` |
| 2 | `prompts/PROMPT-2-verify-claims.md` | Verify what the project says it has done. Hostile and evidence-based. | `late/`, `code/docs/WORK-LIST.md`, `code/` |
| 3 | `prompts/PROMPT-3-gates-and-process.md` | Are the release gates real? What is missing for a safety-relevant data site at thousands of pages? Is the review process converging? | `code/refresh.py`, `code/check.py`, tests, workflows, `evidence/` |
| 4 | `prompts/PROMPT-4-missions.md` | Judge the assistant's old audit missions (`appendix/missions-A-to-L.md`): which are the wrong questions, what is missing, then run the best three. | `appendix/`, plus whatever each mission needs |

Two more prompts exist: `prompts/PROMPT-ALL.md` (one exhaustive prompt covering everything, answered in parts) and `prompts/PROMPT-TEMPLATE.md` (BROWSE the live site, judge the UI, design a Fort Knox template and gate process). Passes 1 to 4 were already run once; this packet is the updated version: it adds new gates (`code/truth_types.py`, `_truth.json` verification record, data-plausibility contract 19, USGS identity check), a UI polish release, and review reports 10-P to 10-S in `late/`. The site is still noindex.

Run pass 1 first and on its own: do not read `late/` or `appendix/` before you have answered it. Pass 2 may build on pass 1's top findings if you paste them in; pass 3 and 4 may also. Each pass is meant to fit one chat; a pass that cannot be finished in one answer should say what it skipped and why.

## Ground rules for every pass
- Label each claim: **[SEEN IN PACKET]**, **[MY KNOWLEDGE, UNVERIFIED]** or **[GUESS]**. Quote file names.
- If you cannot browse or run code, say so once and do not pretend to have verified live pages or run tests.
- You may say a question's premise is wrong. Prefer 10 supported points to 40 weak ones. The most important finding goes first.
- Do not praise anything you did not inspect.

## What is deliberately NOT in this packet
Search Console data (the site has none: it is under a noindex hold), analytics, ad revenue, the Cloudflare and GitHub account settings, the owner's other site's data, the old multi-tab design, and most screenshots (373 slices were removed because they were noise; a few chosen ones are in `evidence/`). The NWS water.noaa.gov gauge page is not captured: it did not render in a headless browser.
