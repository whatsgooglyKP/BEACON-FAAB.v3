# Central Florida food-access data findings

Prepared 11/2026. This is a public-data screening foundation, not proof of unmet pantry demand or an operational allocation recommendation.

## Bottom line

Use a **food-bank organizer’s neighborhood triage workbench**, not a generic chatbot or an autonomous route optimizer. The data are usable after deterministic normalization, but their definitions and uncertainty matter more than superficial formatting.

## Scope supported by the files

The five ACS archives all contain 3,085 actual tract records across the three target regions, plus a second descriptive-header row and an empty trailing column. Their shared Florida footprint is **490 tracts: Lake 75, Orange 267, Osceola 59, Seminole 89**. These four counties define this analysis; it is not a claim that Central Florida has only four counties.

The three USDA SRAM tables are nationwide (84,119 rows each); Florida coverage is 5,122 tracts in all 67 counties. They cover every one of the 490 core tracts. The mortgage workbook uses a larger seven-county Central Florida footprint: Brevard 144, Lake 75, Marion 91, Orange 264, Osceola 59, Seminole 89, Volusia 129. It has 487 core tract records. The Florida CRA PDF has 489 core tract records. Polk and Sumter are available in nationwide USDA/retailer data but have no core ACS records in the supplied archives. Do not expand the scope silently and then compare counties with missing ACS inputs.

The address-level retailer file has 248,872 national records, of which **1,695** are in the four core counties. It has no tract GEOID. Per Appendix B, it remains an optional address/point lookup; no systematic retailer-per-tract counts were fabricated.

## What is actually messy

- Census exports have two headers, cryptic column IDs, 90% MOE companion columns, structural `(X)` cells, `-`, `N`, `**`, `***`, and income values such as `250,000+`. Some subgroup columns are mostly inapplicable; that is not wholesale missingness in the core food indicators.
- No `-666666666`, `N/A` or standalone `*` values were observed in the core observations. They are plausible future schema cases, not observed problems in this batch.
- GEOIDs arrive as `1400000US120...`, plain 11-digit tract codes, and decimal tract numbers inside county-grouped PDF pages. USDA general-characteristics IDs lose leading zeros in states beginning with zero; the Florida state prefix 12 itself does not lose a leading zero. A decimal tract without county/state context cannot safely be repaired.
- USDA national files require Windows-1252 for some names; lookup files include a UTF-8 BOM. Different sources use county suffixes or uppercase names. No County20/County24 county-name changes were found inside the core footprint.
- ACS and USDA `share` variables here are already **0–100 percentages**, not fractions. HMDA `denial_rate` is 0–1; its separate percentage column is scaled by 100. CRA loan dollar columns are **thousands of dollars**. Median household income and median family income are different measures and remain separate.
- No duplicate tract keys or duplicate full observational rows were found in the core source tables; no conflicting duplicates needed arbitration. Missing HMDA/CRA rows are unknown, not zeros.
- The biggest semantic trap: the supplied “Low Grocery Access” archive is **USDA SRAM, access to all SNAP-authorized food stores**, not the supermarket-only FARA measure. The included Read Me says initial release 07/2026; the filename alone is misleading.
- Sources have mixed vintages: ACS 01/2020–12/2024, population base 04/2020, SNAP-store snapshot 06/2025, SRAM release 07/2026. These cannot establish current pantry need, current store openings, affordability, food quality or opening hours.

## What the analysis fixes and preserves

The exported tables use string 11-digit tract FIPS, a fixed four-county allowlist, normalized field names, source-prefixed collisions, one-to-one joins, numeric nulls for coded unknown/inapplicable values, and a cell-level original-value/reason ledger. Censored incomes have explicit lower bounds in `censored_value_bounds.csv`; they are not treated as exactly $250,000. Metadata retains the distinction between percentages, percentage-point MOEs, counts, dollars, fractions and thousands of dollars. Zero remains zero. Business/mortgage data are joined for completeness but excluded from food-need logic. Retailer points are separate.

`tract_all_sources.parquet` has 490 rows and 1,726 data columns. `tract_clean.parquet` is the curated app-ready view. The inventory covers all Central Florida-relevant files and their metadata/notes; every column is profiled in `column_inventory.csv`.

**The repeatable cleaner is now implemented.** Run `.venv/bin/python clean.py --config pipeline_config.json` to regenerate the outputs from the source snapshots. Schema changes and unknown files are made explicit in `output/review_report.json`; missing/renamed required fields block publication. The original audited outputs are preserved in `audited_baseline/`. See `README.md`, `PIPELINE_DESIGN.md` and `TEST_RESULTS.md` for usage and verification.

## Quality and confidence

The three decision-input fields are poverty percentage, SNAP percentage and straight-line LILA. **488/490 tracts have all three**. The exceptions are `12095016515` (University area, group-quarters-heavy, estimated population 12,624 but zero households) and `12095990000` (zero population and households). Neither should be ranked as ordinary household neighborhoods.

There are 372 high-poverty-MOE flags and 367 high-SNAP-MOE flags under the stated heuristic: coefficient of variation above 0.30 (MOE / [1.645 × estimate]) **or** absolute MOE at least 10 percentage points. These are deliberately conservative review flags, not a claim that all these estimates are unusable. Actual sample sizes are absent; low population/household denominators are only a proxy, not sample sizes.

At the core’s nominal poverty top-quartile cutoff **17.025%**, 68 tracts also have straight-line LILA at ½ urban / 10 rural miles. Only seven candidates remain above that fixed cutoff when subtracting their poverty MOE. This is a descriptive robustness check, not a formal significance test that accounts for uncertainty in the cutoff or multiple comparisons.

The access definition changes the picture: **118** core tracts are straight-line LILA versus **157** driving-distance LILA, with **39** changed flags. Show that toggle; do not describe it as a real-world deterioration. Binary LILA itself should not be quartile-ranked to implement the appendix’s “blind spot” case. A later adaptation could use the continuous low-access population share, with its denominator and vintage explicit.

The official “no reliable transportation” adult rate is not available for Central Florida. USDA includes no-vehicle housing-unit estimates, which could be explored as a distinct proxy, never passed off as that transportation rate.

## Tracts to readable areas

Full Census TIGER/Line Florida tract and place/CDP polygons (01/2024) were intersected in equal-area EPSG:5070. City of Orlando’s 125 official neighborhood polygons add true local neighborhood labels where their largest overlap covers at least half a tract. A tract is not a neighborhood.

For the remaining tracts, use the largest Census place/CDP intersection when it covers at least half the tract; otherwise label it mixed/unincorporated with tract/county context. Do not assign a nearest city as if the tract lies inside it. Preserve all overlaps for inspection. High mapping confidence means at least 80% area overlap, Medium at least 50%, otherwise Low. These are geometric labels, not estimated population coverage and not calibrated probabilities.

There are **38 true Orlando-neighborhood assignments**; overall mapping confidence is High 182, Medium 116, Low 192. Low-confidence labels need a local organizer’s correction, especially where tracts mix municipal and unincorporated areas or have substantial water. The Orlando layer’s boundary vintage is not stated; retrieval is 11/2026. Place/CDP labels such as Pine Hills can be useful but are not automatically official local neighborhood boundaries. Every GEOID remains visible.

## Top ten areas to investigate

Selection: straight-line LILA ½ urban / 10 rural miles = 1 and poverty at or above the four-county Q75. Sort by poverty percentage descending, then modeled low-income/low-access count to break ties. This is an interpretable screening order, not a severity league table or measured count of hungry residents. SNAP participation is context, not a penalty or eligibility inference. “Low income” in the modeled count means up to 200% of the federal poverty threshold, not the separate below-poverty count.

| Rank | Tract GEOID | Friendly area label | Poverty % ± 90% MOE (pp) | SNAP % | Modeled low-income/low-access people |
|---|---|---|---:|---:|---:|
| 1 | 12095017703 | Apopka (Orange Co.) | 43.7 ± 11.4 | 21.5 | 271 |
| 2 | 12095017600 | Apopka (Orange Co.) | 35.6 ± 12.8 | 40.8 | 353 |
| 3 | 12117020901 | Sanford (Seminole Co.) | 31.1 ± 12.2 | 24.4 | 722 |
| 4 | 12097042902 | Unincorporated Osceola Co. — tract 429.02 | 30.6 ± 13.3 | 14.8 | 660 |
| 5 | 12095017019 | Unincorporated Orange Co. — tract 170.19 | 30.3 ± 25.8 | 31.4 | 1,193 |
| 6 | 12095016406 | Unincorporated Orange Co. — tract 164.06 | 28.5 ± 9.8 | 6.5 | 226 |
| 7 | 12095012402 | Rosemont (Orange Co.) | 27.9 ± 11.7 | 36.1 | 1,326 |
| 8 | 12095016504 | Mixed / unincorporated near Union Park (Orange Co.) | 26.7 ± 7.9 | 17.3 | 1,277 |
| 9 | 12095014812 | Florida Center (Orange Co.) | 26.6 ± 10.8 | 17.6 | 310 |
| 10 | 12095015104 | Lockhart (Orange Co.) | 25.9 ± 11.1 | 25.8 | 1,256 |

All ten are also driving-distance LILA. Tract `12095017019` has a particularly wide poverty MOE (25.8 pp): do not confidently rank it over another tract. Rosemont is an actual Orlando neighborhood intersection; Apopka, Sanford, Lockhart and Union Park are Census place/CDP context, with exact overlap/confidence in the mapping CSV.

## Three concrete product ideas, ranked

1. **Neighborhood Action Desk — recommended.** Organizer-facing map and shortlist of areas to validate for outreach or a mobile-pantry pilot. Each card shows “why flagged,” source/vintage/MOE, straight-line vs driving sensitivity, readable name + tract ID, and what the data do not know. A reviewer can approve for a site visit, reject a flag, correct a label, assign an owner and add partner observations. No automatic allocation or dispatch. Add current pantry locations, schedules and capacity supplied/validated by organizers before making service-gap claims. Small enough for a credible hackathon demo and directly useful.
2. **Data Refresh & Trust Agent.** Drop in a fresh Census/USDA export; it profiles schemas and units, proposes deterministic mappings, quarantines ambiguous fields/duplicate conflicts, and shows row-level “what changed and why” for human sign-off. Best as the ingestion/audit component behind #1, not a black-box cleaning chatbot. It never invents suppressed values or silently infers geography.
3. **SNAP Access Field Briefs.** An area-specific outreach pack combining the tract’s poverty/SNAP/access evidence with manually checked SNAP-store and pantry lookup records, plus questions for a site visit. Useful for partnerships and grant narratives, but cannot infer retailer quality, program eligibility or benefit-redemption failure from SNAP participation alone.

## Suggested demo arc (90–120 seconds)

- Show one real messy Census row and its normalized GEOID, code-specific flags and metadata.
- Open Apopka tract `12095017703`: poverty 43.7% ± 11.4 pp, LILA under both distance definitions, modeled low-income/low-access count 271. Say explicitly that this is a screening signal, not 271 confirmed unserved clients.
- Compare tract `12095017019`: 30.3% ± 25.8 pp, visibly wide uncertainty and mandatory label review. Explain why the tool does not act autonomously.
- Switch straight-line to driving access: 118 → 157 LILA flags, 39 differences. Reveal the definition change rather than hiding it in a single score.
- A reviewer marks an area for local validation, assigns a teammate and records a clearly labeled demonstration note. Do not present a fabricated pantry observation as real.
- Close on adoption: “Built on open Census/USDA and local geography; not yet co-designed with food-bank organizers. Next: validate names and actual service coverage with a local partner, then pilot a human-reviewed outreach shortlist.” Do not claim a partnership that has not happened.

## Files and sources

- `output/tract_clean.csv` and `.parquet`: curated 490-tract view.
- `output/tract_all_sources.csv` and `.parquet`: wide joined indicators; unrelated financial indicators remain separate fields.
- `output/data_quality.csv`, `cell_quality_flags.csv/.parquet`, `sentinel_summary.csv`, `censored_value_bounds.csv`: uncertainty, null provenance and censored bounds.
- `output/tract_neighborhoods.csv`, `tract_place_overlaps.csv`, `tract_orlando_neighborhood_overlaps.csv`, `tracts.geojson`: readable labels, auditable spatial intersections and map geometries.
- `output/top_need_candidates.csv`: all ten screening explanations.
- `output/source_inventory.csv`, `column_inventory.csv`, `curated_field_dictionary.csv`, `county_coverage.csv`, `mortgage_all_region_coverage.csv`, `usda_florida_county_coverage.csv`, `input_manifest.json`: coverage, metadata and hashes.
- `output/snap_retailers_core.csv`: 1,695 address/point records, no inferred tract count.

Source folder: https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p

Appendix B: https://docs.google.com/document/d/1L25DTxI31BlrH3QvB7k8H0rt6eowMiYA3YqHEwfJer0

USDA semantics: https://www.ers.usda.gov/data-products/food-access-research-atlas/documentation/snap-authorized-retailer-access-map-reference-guide

Census tract geometry: https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_12_tract.zip

Census place geometry: https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_12_place.zip

Orlando neighborhoods: https://gis.orlando.gov/server/rest/services/Socrata_OpenData/OrlandoPoliticalBoundaries/MapServer/2

Every Central Florida-relevant source was accessible. NYC/SLC rows inside the ACS/USDA/mortgage files were inspected only for schema/coverage. NYC/SLC-only small-business PDFs and the transportation CSV were not downloaded; the appendix explicitly rules out the latter as a Central Florida decision input.
