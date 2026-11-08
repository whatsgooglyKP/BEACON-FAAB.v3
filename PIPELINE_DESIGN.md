# Repeatable cleaning pipeline — proposed design

Prepared 11/2026. Design approved and the repeatable cleaner is implemented in `clean.py`, `pipeline_data.py` and `pipeline_geography.py`. The app itself is not built. The design below remains deliberately conservative and config-driven.

## Recommended approach and alternatives

1. **Deterministic adapters + shared validation (recommended):** Source-specific Census/USDA/PDF/point readers feed a shared schema and a declared tract spine. Reproducible, reviewable, no invented suppressed values; small adapter additions for truly new schemas.
2. Generic dataframe union with inferred units/joins: quick but dangerous. A 0.6 can mean a fraction or 0.6%; a decimal tract is not globally unique; a binary flag is not continuous food need. Reject for operational use.
3. LLM-based auto-cleaning: useful only to propose mappings/explanations for review. Never let it silently infer geography, impute unknown data, conflate measures or write the accepted canonical table.

## Architecture and contracts

- Source discovery enumerates local snapshots and archive members, records source URLs, hashes, encoding, geography, years, columns, row counts and file types. It never downloads newly discovered links automatically.
- Each adapter returns `geoid`, typed indicators, field-level metadata and an event ledger. File shape/metadata IDs, not filename keywords alone, identify schemas. Every source declares geography and unit semantics.
- Canonical keys: preserve full GEOIDs as strings; strip a known Census prefix; restore only documented leading zeros; validate 11-digit state/county/tract against the boundary spine. Decimal `167.00` can become `016700` only when state and county are explicitly available. Reject ambiguous tract-only or scientific-notation IDs rather than silently losing precision.
- Column normalization keeps Census IDs intact as lowercase. Human-readable aliases are a curated semantic view, not replacements for metadata. Prefix USDA general, straight-line, driving and financial fields to prevent name collisions.
- Code-specific nulls carry original values and reasons. `(X)` is structural N/A, not evidence a community has no access. Censored incomes retain bounds and are null as exact values. No imputation of suppressed cells. No blanket replacement of negative numbers outside a source-declared sentinel set.
- Rate harmonization is driven by source metadata/config, never guessed from a column maximum. Existing ACS/USDA shares are 0–100. Fraction-only HMDA rate receives a separate 0–100 alias. Rate MOEs are percentage points. Counts, family/household income and dollar/thousand-dollar measures stay distinct.
- Exact duplicate observations are removed with an audit record. Conflicting same-source tract rows quarantine the source or fail the join. No arbitrary `keep=first` for conflicts.
- One-to-one tract joins use the explicitly verified core spine and retain source-absence flags. Address/point data remain separate. No county/ZIP value is repeated across all tracts as if measured there.
- Data-quality scoring uses the declared three core fields, not all structurally inapplicable subgroup cells. Source-specific missingness, MOEs, CVs, vintage, special population/GQ flags and geography-review requirements remain visible.
- Neighborhood labelling intersects full tract/place geometries in equal-area projection, preferring verified local neighborhoods where adequately overlapping. Preserve many-to-many overlap rows, not just the winner. Area overlap is not residential-population overlap.
- Exports are written to a staging directory; validation must pass before replacing canonical outputs. Input hashes and config hash make repeated runs auditable; no network calls or external side effects are needed for a local refresh.

## Proposed interface

Run: `.venv/bin/python clean.py --config pipeline_config.json`.

The command is implemented and tested. `pipeline_config.json` contains the concrete field/unit/geography rules, accepted schemas and metadata fingerprints. New fields/files are explicitly routed to review; missing or likely renamed required fields block publication. `pipeline_config.proposed.json` is retained only as the original design draft.

## Validation before acceptance

1. GEOID tests: `1400000US12095016700` → `12095016700`; full code unchanged; documented numeric leading-zero case restored; `167.00` + Orange county → `12095016700`; decimal tract without county fails; ZIP/county keys are rejected as tract IDs; no float-based key conversion.
2. Sentinels/censoring: every observed code goes to null + reason; zero remains zero; `250,000+` preserves lower bound and never becomes an exact estimate; true negative-valued metrics are not discarded automatically.
3. Units: explicit 0.42 fraction → 42%; a declared 0.42 percent remains 0.42%; ACS MOE remains in pp; no scaling on counts; family income does not overwrite household income.
4. Duplicate tests: identical observations removed and counted; conflicts quarantined; no row multiplication in joins.
5. Golden batch: 490 unique core tract keys, county counts 75/267/59/89; two incomplete core rows; 118 SD and 157 DD LILA flags; 39 changed distance-definition flags; 68 nominal high-poverty LILA candidates at Q75 17.025%; 1,695 separate retailer points; source-missing mortgage rows stay null.
6. Geography tests: 490 mapping rows; no assertion that a Census place is an official neighborhood; all local-neighborhood labels require >=50% area overlap; low-confidence/no-overlap labels routed to review; CRS and vintage saved.
7. Robustness: fixed-cutoff poverty lower-MOE check; threshold/distance toggles; no transportation rate invented; no quantified unmet demand without service data.
8. Idempotence: rerunning the same inputs/config yields the same tables, input manifest, definitions and event counts (excluding a separately stored run timestamp). Test using a temporary output directory.

## Human review and adoption

The organizer must approve/reject recommendations and can correct labels. Pilot with current partner-provided pantry locations, service schedules, eligibility and capacity, then validate whether flags identify a real gap. No production dispatch, client-level inference or allocation without those inputs and human approval. Do not claim co-design with a food bank before it happens.
