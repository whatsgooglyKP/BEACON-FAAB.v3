# Beacon Central Florida cleaner

Source snapshots and documentation prepared 11/2026. No network access, API keys or LLM calls are needed to run the cleaner.

## Run

From this folder, activate the existing environment once:

```bash
source .venv/bin/activate
python clean.py --config pipeline_config.json
```

Without activation: `.venv/bin/python clean.py --config pipeline_config.json`.

For a fresh environment: `python3 -m venv .venv`, then `.venv/bin/pip install -r requirements.txt`. System dependency: `pdftotext` from poppler-utils.

The one command reads source files from `raw/`, raw boundary snapshots from `geography/`, and regenerates all files in `output/`. It unpacks archives into a temporary directory. It does not read previous `output/` or `extracted/` files. `--input` and `--output` override the source/output directory; boundary snapshots remain relative to the config. Keep `pipeline_config.json`, its approved schemas/metadata fingerprints, and the three Python modules together.

## Automatic vs human-reviewed

Automatic: detect UTF-8/BOM or Windows-1252; remove descriptive Census headers and empty trailing columns; normalize declared tract-ID formats and field names; preserve numeric zero; convert source-declared sentinel values to null plus original-value/reason flags; retain censored-income lower bounds; distinguish fractions, percentage points and percent values; remove exact duplicates; validate one-to-one joins; preserve absent-source rows as null; compute MOE/CV/vintage/completeness flags; intersect official polygons for transparent neighborhood/place labels.

Review report: `output/review_report.json` and `.csv` list unexpected files, archive members, new columns and likely renamed/missing columns. New fields are quarantined, not guessed into semantic aliases. Missing/renamed required columns, changed metadata semantics, conflicting tract duplicates, invalid geography, missing/changed geometry snapshots, source/geometry coverage mismatch or processing errors **block publication** (exit 2). Existing accepted data are retained; only the review report is updated. An unknown extra file or column is nonblocking when the original accepted schema remains intact; it is explicitly reported and excluded. To accept a genuinely changed schema, review its meaning/units and deliberately update config schemas/metadata fingerprints—never auto-approve the suggestions.

Source PDF numbers still need visual review before operational use. Low-confidence geographic labels require local correction; high MOEs and mixed vintages are visible. “No reliable transportation” is not invented for Central Florida. Retailers remain separate address points; there is no inferred per-tract retailer density. LILA here measures SNAP-store access, not supermarket-only access. Output flags mean areas to investigate, not confirmed unmet pantry demand.

## Outputs and tests

`tract_clean.*` is the organizer-facing 490-tract view. `tract_all_sources.*` retains source fields. `data_quality.csv`, cell flags, source/column inventories, neighborhood overlap tables, `top_need_candidates.csv`, and input hashes make each result inspectable. `run_info.json` records runtime and config hash. `summary.json` contains screening counts. See `FINDINGS.md` for interpretation and the proposed demo.

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The integration test builds into a fresh temporary directory, compares the wide and curated tables to `audited_baseline/`, checks all original outputs are regenerated, then repeats the run and checks deterministic CSV/GeoJSON bytes. Drift tests mutate copies of inputs and verify review-report/publication behavior. No test changes source snapshots.

## Optional v3 SNAP-gap stage (11/2026)

After cleaning, run `.venv/bin/python snap_gap_model.py` (install `requirements-model.lock.txt` once). This separate, documented stage writes `output/snap_gap.csv`, `output/snap_gap_metadata.json` and `MODEL_CARD.md`; it does not modify the audited tract/geometry outputs. Then `cd app && npm test` / `npm start`. App sync refuses a model snapshot whose tract input hash is stale. The stage predicts aggregate expected SNAP participation, NOT eligibility, food need or verified under-enrollment. See MODEL_CARD.md and app/V3_DELIVERY.md.
