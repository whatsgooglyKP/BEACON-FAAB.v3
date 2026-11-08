# Beacon · Neighborhood Action Desk

Prepared 11/2026. A hackathon prototype for Central Florida food-bank organizers. Open-data evidence, local review, and a defensible decision trail—not an autonomous route optimizer.

## v4: easier-to-read SNAP sign-ups (presentation only)

The evidence card and decision brief now start with **SNAP sign-ups**, a plain-language badge, rounded households-in-100 comparison, why it matters, one plain reason and a short caution. **How we got this** stays closed by default and retains the original numeric/technical explanation. University-area cards also warn that student benefit rules may explain a difference. All uncertain labels remain “Not enough data to say”; none is changed into an “About as expected” claim.

The model script, exact CSV/JSON outputs, flag rule, tract data, geometry, ranking and resident flyer are unchanged. Whole-number counts are display rounding only. Current packages: `beacon-action-desk-static-v4.zip` and `beacon-action-desk-source-v4.zip`. Current samples: `exports/apopka-17703-snap-gap-v4-brief.html/.pdf` and `screenshots/apopka-snap-gap-v4-card.png`, `screenshots/apopka-snap-gap-v4-brief.png`. These are genuine PDF/file rasters, not live-browser screenshots. The brief PDF shows the plain default view; expand the HTML’s **How we got this** to inspect the technical details. See `V4_DELIVERY.md`.

## v3: only the SNAP-gap model added

Each organizer evidence card and decision brief now includes held-out expected SNAP participation, actual estimate/MOE, actual-minus-expected gap, a conservative label and three coefficient-based associations. The audited tract data, geometry, map coloring and shortlist order are unchanged. Resident flyers contain no model scores. No clustering, GenAI, reinforcement learning, automatic dispatch or new external services.

- Five-fold OOF ridge (alpha 10, seed 42); 488 modeled tracts, two unavailable.
- OOF MAE **5.5826 pp** vs naive mean **8.2076 pp**; R² **0.5033** vs **−0.0051**.
- Four “likely under-enrolled” **outreach hypotheses**, 484 uncertain. This does NOT identify eligible-but-not-enrolled households.
- Apopka 12095017703: actual **21.5% ±7.5 pp**, expected **35.5%**, gap **−14.0 pp**. See `../MODEL_CARD.md` for rule, features, limitations and versions.
- Reproduce model after cleaning: from `beacon-cfl/`, create a Python 3.13 venv if needed, `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements-model.lock.txt`, then `.venv/bin/python snap_gap_model.py`. Run `.venv/bin/python -m unittest discover -s tests -p test_snap_gap.py -v` for five model contracts. This model command is a documented separate stage; it is not silently run by `clean.py`.
- `npm start`/build uses the packaged separate `snap_gap.csv` + metadata snapshot; model training is not needed for the demo. A mismatched input hash or partial join blocks sync rather than displaying stale predictions. If the cleaner updates tract data, rerun the model before sync/build.
- Handoff: `beacon-action-desk-static-v3.zip` (unzip + HTTP serve) and `beacon-action-desk-source-v3.zip` (app, model, tests, lockfiles, minimal audited snapshots). The source ZIP omits raw data/the full cleaner; those remain in the separate original analysis bundle.
- `exports/apopka-17703-snap-gap-v3-brief.pdf` is a real one-page sample; `screenshots/apopka-snap-gap-v3-brief.png` is its genuine PDF raster, not a live-browser screenshot.

## v2 additions (retained)

- **Ask the Desk:** deterministic natural-language Q&A for flagged Apopka tracts, individual evidence, missing information and official resource referrals. Every answer carries its active lens, sources and limitations; no LLM/API keys or invented pantry locations.
- **Human recommendation controls:** reason-required replacement, independent confirm/challenge of the screening hypothesis, preserved reviewer disagreement and planning-only manual overrides. The evidence-screening counts never change with local decisions.
- **Editable/deactivatable observations:** own-alias amendments and withdrawal reasons are append-only. Current views and briefs use active amended notes; full history remains inspectable. Aliases are not authentication.
- **Community flyer/message:** separate resident-facing printable HTML and copyable text, no internal scores/staff notes, explicit organizer-to-fill placeholders and verification warnings. No automatic sending or posting. Official food resource: https://feedhopenow.org/find-help/food-finder/ — call ahead; no food-bank warehouse pickup is implied.
- **Source handoff:** `beacon-action-desk-source-v2.zip` contains the app source, tests, lockfile and the six audited output snapshots needed by `prepare_data.py`. Unzip, `cd beacon-cfl/app`, `npm ci` once, then `npm start`. `npm test` rebuilds and runs all tests. No node_modules, credentials or browser notes are bundled. The large cleaner/raw-data bundle remains separate.

Community draft examples: `exports/apopka-community-flyer-v2-draft.html`, `.txt`, `.pdf`; `screenshots/community-flyer-v2.png` is a genuine one-page PDF raster, not a browser screenshot. Public-directory examples are available in the static build at `./examples/`.

No distribution license for original app work or Beacon artwork is invented here; confirm reuse terms before public release. No authenticated cross-device backend, current pantry catalog or operational dispatch is implied.

## Problem

Food bank organizers must decide where to place the next mobile pantry or distribution site and defend it. Today they default to the loudest partners or familiar sites; when a funder or board asks 'why there?', the answer is gut feel or a spreadsheet no one else can follow.

## Run locally

Dependencies are installed on this box. From `/workspace/beacon-cfl/app/`, one command:

```bash
npm start
```

Local URL: **http://localhost:5173/**. The server is already running in the background. Node 20.19+ (or 22.12+) and Python 3 are required. On another machine, run `npm ci` once first. `npm start` refreshes the local data snapshot from `../output/` before starting Vite. No accounts, keys, hosted services, network maps or paid APIs are needed. Do not open index.html directly; use HTTP.

For a browser-ready static build:

```bash
npm run build
python3 -m http.server 5174 --directory dist
```

Then open http://localhost:5174/. `dist/` is self-contained, with relative asset paths, tract data, geometry and branding. `beacon-action-desk-static-v4.zip` is the current static option; unzip and serve it over HTTP or, after approval, upload it to a static host. Nothing has been deployed externally. It contains public source data but no browser-local review notes.

## What works

- Clickable/pannable/zoomable offline Leaflet map of all 490 tracts, colored by the poverty estimate among selected LILA/uncertainty-lens tracts. This is an explicitly defined screening score, not a model of hunger or unmet demand.
- Default sorted shortlist of 68 high-poverty + straight-line LILA candidates; 97 under driving. Conservative poverty-lower-bound mode yields 7 straight-line or 14 driving candidates. County/search filters and reason-required manual reordering preserve the evidence values.
- Friendly place/neighborhood labels and mapping confidence. Every tract ID stays visible. The app does not equate a tract, CDP, city and neighborhood.
- Apopka tract 12095017703: poverty 43.7% ±11.4 pp; both distance definitions flagged; SNAP 21.5% ±7.5 pp. Actual sample size is **not provided**. The app correctly avoids claiming a confirmed small sample.
- Plain-English evidence, 90% interval, definition/vintage/transportation limitations, and links to actual sources. Sources are mixed-vintage, not current service data.
- Approve/reject for local verification with a required reason; owner/status assignment; unverified notes/flags; append-only audit entries. Approval does not dispatch a truck.
- Two reviewer aliases retain opposing decisions and surface a disagreement. Same-origin tabs synchronize through localStorage events. This is a **same-browser collaboration demonstration**, not authenticated multi-user storage across machines. Local notes are user-entered and never treated as source data.
- Printable one-page HTML brief with review rationale and clearly labelled local observations; browser Print → Save as PDF. Downloadable audit backup. Packaged sample HTML/PDF is explicitly a sample, not a real approval or verified pantry observation.
- Data Health reads the latest clean.py review report captured when this app starts/builds. It shows blocking versus nonblocking items, metadata hash, source information and limitations. Rerun `npm run sync-data` and refresh after a new cleaner run; this is a snapshot, not a live pipeline monitor.
- About panel includes the problem, open-data foundation, adoption plan and honest lack of an actual food-bank partnership/co-design claim.

## Brand

Applied the supplied Beacon brand guide (04/2026): Primary #1E343F, #385981, #6B8FA8; Accent #F79122 / #FDCB9C; success #388D58 and error #C44A4A. The white logo is proportionally cropped from the official supplied PDF, with its flat background made transparent. Avenir is requested if installed, with system fallbacks; no licensed font files are redistributed. Guide: https://drive.google.com/file/d/1KZY4wAevNOpc0kg6owQqYE42hqKYrB2J/view

## Data provenance

`prepare_data.py` reads the audited `../output/tract_clean.csv`, `tracts.geojson`, source hashes, pipeline run info and review JSON. It preserves string GEOIDs and numeric nulls. Public JSON snapshots are in `public/data/`; no local edits write back to the cleaner. The app keeps data-derived fields separate from user decisions and observations. Original public sources: https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p

Store access is USDA SRAM access to SNAP-authorized stores, not supermarket-only FARA. Adult reliable-transportation data are unavailable for Central Florida. Pantry capacity, hours, site suitability and current unmet service demand are not in these inputs. Local validation is essential.

## Verification

```bash
npm test
```

This builds the actual app, then runs model/data contracts and a real production-bundle workflow in a virtual DOM: approval → demo note → owner assignment → second-reviewer rejection → visible disagreement → exported brief preview. This is not a real-browser visual/layout test. See TEST_RESULTS.md.

`exports/apopka-17703-sample-brief.html` and `.pdf` use real indicators with clearly labelled sample user inputs. `screenshots/exported-brief.png` is a raster rendering of that genuine one-page PDF. Main-view/evidence live-browser screenshots are still pending browser delegation; this executor has no permitted browser-interaction child. See screenshots/CAPTURE_NOTES.md. No browser screenshots are fabricated.

## What is deliberately not production-ready

No authentication, permission model, shared backend, real-time cross-device collaboration, routing/dispatch optimizer, verified pantry catalog, automatic PDF server, or external deployment. localStorage is mutable and can be lost with browser data; the audit is append-only through the UI, not cryptographically tamper-proof. Arbitrarily long notes may extend a printout; the one-page brief caps displayed note excerpts and points to the full local audit. Current service data and organizer co-design are the next real-world work.
