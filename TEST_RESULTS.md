# Cleaner verification

Prepared 11/2026.

## Fresh acceptance suite

Command: `.venv/bin/python -m unittest discover -s tests -v`

**12 tests passed, zero failures/errors, 55.299 seconds.** Tests cover GEOID normalization/ambiguity, sentinel/censored-value preservation, declared units, whole-file encoding detection, duplicate conflicts, quarantine of new columns/files, visible rename/missing-column review, preservation of accepted output on blocking drift, fresh golden-batch generation and second-run idempotence. The intentional mutated-input test prints “REVIEW REQUIRED” and returns exit 2 as expected.

## Actual one-command build

Command: `.venv/bin/python clean.py --config pipeline_config.json`

**Exit 0; 26.462 seconds**, 490 tracts. Generated every one of the 24 original audited artifacts, plus review_report.json/.csv and run_info.json. The run uses raw source snapshots and raw boundary snapshots only—not prior extracted/ or output/ data.

## Audited-baseline comparison

All 24 original artifact row counts, tract keys and substantive values match. The curated and wide Parquet tables match the audited frames (numeric tolerance 1e-12; column and row order retained). All CSV data match exactly except the textual representation of one spatial-overlap fraction column: 150 of 490 strings differ in final decimal digits, maximum exact decimal difference 2e-16; parsed numeric values are identical. All friendly names, GEOIDs, confidence labels and remaining mapping columns match. Input hashes, summary JSON and GeoJSON match.

See `baseline_comparison.csv` for each artifact. Key checks: four-county counts 75/267/59/89; 488 complete core records; 118 straight-line LILA and 157 driving LILA; 39 changed flags; 68 high-poverty/LILA candidates; poverty Q75 17.025%; 1,695 separate retailer points; 78,595 audited coded/blank cell flags; 12 censored bounds; 38 actual Orlando-neighborhood labels. No transportation rate is invented.

The current review report has no blocking items. Its single nonblocking reminder requires visual verification of PDF-extracted business figures before operational use. Low-confidence neighborhood labels and uncertainty flags remain in the data-quality outputs.

## Reproducibility and remaining limits

Same-input second-run CSV and GeoJSON bytes were identical. Runtime is deliberately isolated in run_info.json and varies; it is excluded from byte-idempotence checks. Source snapshots, accepted schemas, metadata fingerprints, config hash and dependency versions are retained. No independent reviewer was available in this executor session; verification consists of automated tests, artifact comparison and local code inspection. No git repository, remote push or external write was involved.

This is a hackathon data pipeline, not a production service or proof of unmet food need. A food-bank organizer should validate names and current service capacity before making allocation decisions.
