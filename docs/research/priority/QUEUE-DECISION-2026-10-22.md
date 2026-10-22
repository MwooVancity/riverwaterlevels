# Queue decision: adopt ChatGPT's revised build order (2026-10-22)

Planning doc. Does not change the live site (owner: no more rivers for now).

## What happened
1. Claude ranked all 9,099 gauges by river-name fame + city reach (ALL-GAUGES-RANKED.csv). Known flaw: keys off the name, so famous names in the wrong state scored high, and city reaches duplicated.
2. ChatGPT audited it (paste 2026-10-22). Verdict: good discovery list, bad build order. Fix before building: dedupe to one gauge per city-river search intent; state-aware identity; verify each gauge is active with real flow.
3. Claude ground-truthed ChatGPT's proposed Tier-1 + Tier-2 USGS site numbers against the live USGS latest-continuous API: 44 of 44 are real and reporting discharge (00060). ChatGPT's IDs are trustworthy.

## Adopted as the next-build order
ChatGPT's revised top-100 (in the paste) is the canonical build order when releases reopen, NOT Claude's raw rank or the old formula. It is deduped and state-corrected.

## Confirmed fixes (both reviewers agree)
- State mismatches to DROP the inherited fame: Guadalupe at San Jose CA (11169025), Rogue at Rockford MI (04118500), Salt at Shepherdsville KY (03298500). The famous Guadalupe/Rogue/Salt are TX/OR/AZ.
- One page per city-river intent: pick one Chattahoochee-Atlanta (02336000), one White-Indianapolis (03353000), one WF-Trinity-Ft-Worth (08048000), one Rio-Grande-Albuquerque (08330000). Drop the near-duplicate stations.
- Still true from 2026-10-21: lower Salt for AZ tubing is 09502000; Gauley cfs is dead (03189600 flow ends 2003), Belva stays the Gauley page; San Marcos city gauge 08170500 not Luling.

## Validated Tier-1 (build first when reopened), all real + reporting flow this date
06893000 Missouri KC; 06610000 Missouri Omaha; 03294500 Ohio Louisville; 07164500 Arkansas Tulsa; 02336000 Chattahoochee Atlanta; 08330000 Rio Grande Albuquerque; 03255000 Ohio Cincinnati; 07032000 Mississippi Memphis; 08158000 Colorado Austin TX; 01467200 Delaware Philadelphia; 08048000 WF Trinity Ft Worth; 09512165 Salt Phoenix; 03353000 White Indianapolis; 03451500 French Broad Asheville; 10348000 Truckee Reno; 08073600 Buffalo Bayou Houston; 13206000 Boise; 07010000 Mississippi St Louis (already live); 05331000 Mississippi St Paul; 03431500 Cumberland Nashville; 05082500 Red River of the North Grand Forks; 08057000 Trinity Dallas; 07374000 Mississippi Baton Rouge; 12422500 Spokane; 01646500 Potomac (already live).

## Not adopted
- ChatGPT's 5-stage scoring model + weighted formula: that is the measured-data path (DataForSEO) for later, not a hand build.
- Rows marked "match needed" in its Tier 3-4: unverified, do not build until the exact id is confirmed and checked for live flow.

## Next real step (owner's call)
When a wave reopens: build Tier-1 above, one gauge each, in order. The per-gauge release already checks live flow, so a dead gauge aborts its own build.
