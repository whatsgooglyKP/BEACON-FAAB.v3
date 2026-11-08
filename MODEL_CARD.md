# SNAP enrollment gap — model card (11/2026)

## Purpose and safe use
Predicts expected SNAP participation among all households, not eligibility, food need or proven under-enrollment. Correlation is not causation. ACS 01/2020–12/2024 five-year estimates; verify with local outreach partners.
The label **likely under-enrolled** is only a model-relative outreach hypothesis. Eligibility and the eligible-but-not-enrolled population are unobserved. Never claim this model identifies eligible residents, predicts future demand, proves under-enrollment or dispatches resources. It predicts a contemporaneous tract aggregate, not individuals or future outcomes.

## Data and features
Input: `output/tract_clean.csv`; SHA-256 `cda498d3d20de1a30c822ada1c501cf3118c0d5e7e016c2fa75f1fb24f54fac3`. Four counties: Lake, Orange, Osceola, Seminole. 490 tracts; 488 modeled; 2 excluded (missing SNAP rate / non-household tracts). Target: ACS percent of **all households** receiving SNAP, not a participation rate among eligible households. ACS 01/2020–12/2024 five-year estimates. SRAM uses 04/2020 population and 06/2025 SNAP-store data, release 07/2026; not FARA supermarket access.

Allowlisted predictors: poverty_pct, log_median_household_income, unemployment_pct, low_access_population_sd_pct_2020, urban, lila_sd_half_10. Income is natural-log transformed; nonpositive/topcoded-unavailable income is missing, not fabricated. No SNAP count, rate, MOE, confidence, SNAP-derived completeness/ranking, GEOID, neighborhood, county, or local review enters prediction. SNAP MOE is used **only after prediction** for the labeling rule.

## Reproducibility and validation
Run `.venv/bin/python snap_gap_model.py` after `.venv/bin/python clean.py --config pipeline_config.json`, then `cd app && npm run build`. Dependencies in `requirements-model.lock.txt`. No network or model API. Sorted string GEOIDs; fixed seed 42; five shuffled folds; ridge alpha 10.0, SVD solver, no tuning. Median imputation and standardization fit only inside training folds. Each modeled tract's displayed prediction is from a model that never saw its target. No in-sample predictions are displayed. Baseline is the matching outer training-fold mean. Per-tract error allowance is max(5 pp, five-fold inner-OOF MAE on outer training rows), never its own error. No final full-data model is substituted for OOF outputs.

| Metric | Ridge OOF | Naive mean OOF |
|---|---:|---:|
| MAE (percentage points) | 5.5826 | 8.2076 |
| R² (pooled OOF) | 0.5033 | -0.0051 |

Metrics are against noisy ACS estimates, not ground truth. Equal tract weighting, not household weighting. Predictions clipped to 0–100; contribution sums reconstruct the raw prediction before clipping. Coefficient contributions (standardized feature × fold coefficient) are relative to the training-fold mean, are not causal, and can be unstable with correlated predictors. Top three absolute contributions shown; all stored for audit.

## Conservative flag rule
expected-actual > SNAP 90% MOE + max(5pp, inner-training-OOF MAE); MOE<10pp; MOE/(1.645*actual)<=0.30; actual>0; all predictors present; model beats baseline overall.
Gap = **actual minus expected**, in pp (negative = below expected). Strong labels disabled if model fails to improve MAE over baseline or R² <=0. Missing predictors force uncertain, even when imputed. Missing targets/non-household tracts are unavailable. All other cases are uncertain; this does **not** establish adequate enrollment. Labels: {"likely under-enrolled": 4, "unavailable": 2, "uncertain": 484}.

The SNAP MOE gate follows the existing conservative CV heuristic. MOE is a 90% ACS margin, not a calibrated probability of under-enrollment. Adding model MAE to MOE is a screening allowance, NOT a combined confidence interval or hypothesis test. No calibrated probability, multiple-comparison control, spatial CV, external/temporal validation, eligibility labels or actual sample sizes exist. Predictor uncertainty (including poverty/income MOEs) is **not** propagated. Nearby tracts may be correlated, making random-fold performance optimistic. Demographic composition and eligibility rules are unmodeled; aggregate associations can obscure inequities. Do not reduce food allocation based on this output. Validate with organizers, eligible-household denominators and current outreach outcomes before operational use.

## Files and refresh safety
`output/snap_gap.csv` and `snap_gap_metadata.json` are separate derived outputs. App reads a separate snapshot; source tract JSON/CSV and geometry stay unchanged. Snapshot sync checks the input hash and refuses stale model results. Resident flyers never receive this section. No deployment, submission, transmission or paid service is used.
