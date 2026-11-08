# v4 delivery — 11/2026

## Presentation only
The card and the same section in the decision brief now lead with SNAP sign-ups, a plain badge, rounded households-in-100 comparison, a possible organizer action, one plain reason and a short caution. How we got this is closed by default and retains exact expected/actual/MOE/gap, raw label, model reason, ridge/five-fold method, error allowance/MOE rule, three associations, ACS vintage and limitations. Expanded details remain available in HTML; the default PDF shows the simple view. University-area cards retain a plain caution about student benefit rules and checking who qualifies.

No model script, dependencies, exact prediction, flag, underlying label, CSV/JSON model output, tract/geometry, map/ranking, resident flyer or any other workflow was changed. Model data were not retrained. Whole-number counts are presentation rounding only. All 484 uncertain cases remain Not enough data to say; no About as expected classification was invented because the existing model has no such category. Four flagged cases display Fewer sign-ups than expected, two unavailable cases display Unavailable.

## Exact Apopka default text (card and brief)
SNAP sign-ups
Fewer sign-ups than expected
About 22 in 100 households here get SNAP. Similar neighborhoods usually have about 36 in 100.
Why it matters: Some eligible families may not be signed up. A SNAP sign-up event here could help.
Main reason we expected more: High poverty for this area
This is an estimate to check with local partners, not proof.
How we got this [closed]

The original exact Apopka values remain actual 21.5% ±7.5 pp, expected 35.531141%, gap −14.031141 pp. Technical detail clarifies that similar neighborhoods is a model-based comparison, not an observed average of matched neighbors. This is not proof of eligibility or a count of eligible families missing benefits.

## Verification
- App: 35 tests pass (original 26 retained). New coverage checks exact plain text, uncertainty mapping across all 490 rows, University-area caution, closed HTML technical disclosure with retained numeric/method text, and jargon-free default text. Actual compiled-bundle workflow checks the closed card and can expand/collapse it.
- Python: all original cleaner/model contracts retained, plus updated one-page brief regression checks that technical method/association text is hidden in the rendered default PDF while the plain comparison is visible.
- SHA-256 comparison to v3 verifies model script, model requirements, CSV/metadata/JSON predictions, tract CSV/JSON and geometry unchanged. Existing flag counts and CV metrics are unchanged.
- Apopka card and brief are each one page, genuine React/HTML → WeasyPrint PDF → pdftoppm PNG, inspected visually. Not live-browser screenshots. Live-browser visual/print behavior remains unverified because no permitted browser delegate is available.
- ZIP CRC and per-payload SHA-256 checks; see V4_PACKAGE_MANIFEST.json for package verification.

## Current files
- beacon-action-desk-static-v4.zip: unzip, python3 -m http.server 5173 from the extracted directory, open http://localhost:5173/?tract=12095017703.
- beacon-action-desk-source-v4.zip: unzip, cd beacon-cfl/app, npm ci once, npm start. npm test rebuilds and runs 35 app tests. Includes unchanged model and minimal audited snapshots; original full cleaner/raw sources remain in the separate analysis bundle.
- DEMO_SCRIPT.md: plain-language 15-second beat.
- exports/apopka-snap-gap-v4-card.html/.pdf and screenshots/apopka-snap-gap-v4-card.png.
- exports/apopka-17703-snap-gap-v4-brief.html/.pdf and screenshots/apopka-snap-gap-v4-brief.png.
- Same current examples are under public/examples/v4/ and packaged static examples/v4/.

No upload, deployment, git push, message, external sharing or submission occurred. Historical v2/v3 packages and samples remain intact.
