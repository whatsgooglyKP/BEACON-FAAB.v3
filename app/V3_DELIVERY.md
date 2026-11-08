# v3 delivery record — 11/2026

## Scope
ONLY the SNAP-gap supervised model was added: organizer evidence-card section and decision-brief section. No clustering, Gemini, GenAI, reinforcement learning, new filtering/ranking, resident scores, deployment, upload, push, messages or submission. v2 workflows remain.

## Actual model results
- Fixed standardized ridge, alpha 10, seed 42; six allowlisted non-SNAP predictors; five-fold OOF predictions for 488 of 490 tracts. Two non-household/missing-SNAP tracts are unavailable.
- Pooled OOF R² 0.5033119972, MAE 5.5826467784 pp. Naive fold-training mean: R² −0.0051428481, MAE 8.2075550587 pp.
- Four “likely under-enrolled” outreach hypotheses; 484 uncertain; two unavailable. Gap = actual minus expected, not an eligible-but-unenrolled rate.

| GEOID | Area label (tract ≠ neighborhood) | Actual % ± 90% MOE pp | Expected % | Gap pp |
|---|---|---:|---:|---:|
|12095016510|University (Orange Co.)|18.8 ±9.2|49.7976|−30.9976|
|12095017703|Apopka (Orange Co.)|21.5 ±7.5|35.5311|−14.0311|
|12069030806|Tavares (Lake Co.)|7.3 ±2.5|21.0765|−13.7765|
|12069030915|Mixed / unincorporated near Mount Dora (Lake Co.)|11.7 ±4.9|22.4016|−10.7016|

Apopka model-error allowance = 5.4740 pp. Its 14.0311 pp shortfall exceeds 7.5+5.4740 = 12.9740 pp. Top contributions vs training-fold mean: poverty +14.2479 pp; income +7.5059 pp; unemployment −0.7312 pp. These are model associations, not causal effects.

## Conservative labeling rule
Flag only if expected−actual > SNAP 90% MOE + max(5 pp, inner-training-OOF MAE), SNAP MOE <10 pp, MOE/(1.645×actual) ≤0.30, actual >0, all predictors observed, and the model improves over the naive baseline. Imputation/scaling, coefficients and per-tract error allowance never use the tract’s held-out outcome. Missing predictors force uncertainty. No calibrated probability or combined confidence interval is claimed.

## Verification
- App: `npm test` builds and passes **31/31**, including all original 26 and real compiled-bundle evidence/brief workflows. Flyer tests confirm no model scores.
- Python: original **12/12** cleaner acceptance/regression tests plus **5/5** new model/freshness contracts; optional one-page render test also passes (**18 total** when WeasyPrint is installed).
- Model CSV and metadata byte-identical across complete rerun; input-row shuffle produces identical sorted results. Held-out target perturbation leaves that row’s prediction, drivers, baseline and error allowance unchanged; injected SNAP-derived columns cannot enter features.
- `tract_clean.csv`, `tracts.geojson`, app `tracts.json` and app geometry are SHA-256 identical to pre-v3. Main screening counts remain 68/97 and conservative 7/14.
- Real one-page Apopka decision-brief PDF rendered and inspected, including a normal sample rationale/note/assignment in the pagination regression. No fictitious approvals appear in the delivered sample.
- Genuine PNGs: `screenshots/apopka-snap-gap-v3-brief.png` (decision-PDF raster) and `screenshots/apopka-snap-gap-v3-card.png` (server-rendered actual React component → PDF raster). These are **not live-browser screenshots**. No permitted browser/subagent tool was available, so interactive browser visual/print testing remains unverified.
- No independent reviewer subagent was available. Contract, compilation, data-immutability and document-render checks performed locally; no PR or commit was created.

## Files / run
- `beacon-action-desk-static-v3.zip`: unzip, serve its directory with `python3 -m http.server 5173`, open http://localhost:5173/. Browser HTTP required; no training/install needed.
- `beacon-action-desk-source-v3.zip`: unzip, `cd beacon-cfl/app`, `npm ci` once, `npm start`. Source includes minimal audited snapshots, model/requirements/tests/card. Original full cleaner/raw-data bundle remains separate.
- Model command from beacon-cfl: `.venv/bin/python snap_gap_model.py`. Install `requirements-model.lock.txt` in a Python 3.13 venv first on another machine. App consumes separate CSV+metadata snapshot and refuses stale source hashes/partial keys. No automatic retraining during the demo.
- Model card: `../MODEL_CARD.md`; outputs `../output/snap_gap.csv`, `../output/snap_gap_metadata.json`; runtime snapshot `public/data/snap_gap.json`.
- Demo: `DEMO_SCRIPT.md`, 15-second ML beat using Apopka real numbers.
- Samples: `exports/apopka-17703-snap-gap-v3-brief.html/.pdf`, `exports/apopka-snap-gap-v3-card.html/.pdf`. Current static examples under `public/examples/v3/`.

## Caveats to say out loud
This predicts aggregate expected SNAP participation among **all** households, not eligibility, future pantry demand or verified under-enrollment. No eligible-household denominator or outcome labels exist. ACS five-year estimates (01/2020–12/2024) and mixed USDA vintages are not live data. Predictor MOEs are not propagated; neighboring-tract correlation can make random-fold CV optimistic. Student eligibility/composition and other omitted variables may explain a gap—especially review a University-area flag before drawing conclusions. “Likely” is an outreach hypothesis, not a calibrated probability. Do not allocate/reduce services or infer an individual’s status from it. The model does not satisfy any separate GenAI requirement.
