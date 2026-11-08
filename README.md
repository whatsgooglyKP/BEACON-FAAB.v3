# BEACON Food Access Action Board v3

Neighborhood Action Desk for DevFest Florida 2026, DataKind Beacon challenge.
This repository publishes the **current v4 app build** under the requested **v3 project name**.
Previous project: https://github.com/whatsgooglyKP/BEACON-FAAB.v1 (unchanged).

## What it does / who it helps
Helps Central Florida food-access organizers compare 490 Census tracts, inspect
plain-English evidence cards, and shortlist places for local follow-up. Friendly
place names label actual tract polygons; they are not always official neighborhoods.
The SNAP comparison is one supporting signal, not a measurement of food need.

## Run the app
**New here? Follow [RUN_LOCALLY.md](RUN_LOCALLY.md) for step-by-step setup, with a Windows PowerShell section first.** On Windows PowerShell, the commands below are the same; run `cd app` and then `npm install` and `npm start` on separate lines.

Requires Node.js 20.19+ or 22.12+ (Vite 7), npm, and Python 3.
Cleaned data and static assets are included; no API key or Python packages are
needed to launch the app.

```bash
cd app
npm install && npm start
# Open http://localhost:5173
```

```bash
cd app
npm test       # builds and runs app tests
npm run build  # generates app/dist
```

See `app/README.md`, `app/DEMO_SCRIPT.md`, and `app/V4_DELIVERY.md` for the demo.

## Pipeline and model
Run these commands from the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt -r requirements-model.lock.txt
# After restoring the source snapshots described below:
.venv/bin/python clean.py --config pipeline_config.json
# Can run directly against the included cleaned outputs:
.venv/bin/python snap_gap_model.py
.venv/bin/python -m unittest discover -s tests -v
```

The cleaner also needs `pdftotext` (poppler-utils). Full pipeline/integration/drift
tests require the omitted raw snapshots. `audited_baseline/` contains regression
fixtures, not a second independent source. See `PIPELINE_README.md`,
`PIPELINE_DESIGN.md`, `VALIDATION.md`, and `MODEL_CARD.md`.

## Data sources and restoring inputs
Source snapshots: November 2026; data vintages differ. Source collection:
https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p

Restore `labor.zip`, `income.zip`, `snap.zip`, `grocery.zip`, `poverty.zip`,
`population.zip`, and `retailers.csv` into `raw/` from that collection. Archives
and the large retailer source are intentionally omitted. Small non-archive
supporting sources are included. Exact source hashes and accepted schemas are in
`output/input_manifest.json` and `pipeline_config.json`; do not substitute newer
data without reviewing the config and provenance.

Restore `geography/tracts.zip` from
https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_12_tract.zip
and `geography/places.zip` from
https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_12_place.zip .
The included Orlando neighborhood snapshot comes from
https://gis.orlando.gov/server/rest/services/Socrata_OpenData/OrlandoPoliticalBoundaries/MapServer/2 .
USDA access definitions:
https://www.ers.usda.gov/data-products/food-access-research-atlas/documentation/snap-authorized-retailer-access-map-reference-guide

## Limitations
ACS tract estimates can have wide error bars. Access flags refer to SNAP-authorized
retailers, not necessarily supermarkets. Place labels may be approximate. Inputs
are aggregate area data, not household eligibility or individual outcomes.
The small ridge-regression model estimates expected SNAP participation from six
non-SNAP factors, with out-of-fold comparisons and uncertainty screening. It does
not predict a food-need percentage, prove under-enrollment, or establish causality;
student eligibility and other unobserved factors can explain apparent gaps.
Verify findings with local partners before acting. See `MODEL_CARD.md` and
`FINDINGS.md` for scope, metrics, and caveats.

## Packaging
Included: app source/static assets/tests, cleaned outputs, pipeline/model code,
locked dependencies, regression fixtures, and methodology docs. Excluded:
node_modules, virtual environments, dist, archives, audit downloads, caches,
large raw retailer data, and files over 50 MB. No deployment or submission is
performed by publishing this repository.
