"""Explainable, deterministic held-out SNAP-rate screening. Not eligibility estimation.

Run: .venv/bin/python snap_gap_model.py
Inputs never modified. Outputs are separate from audited tract/geometry snapshots.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 42
ALPHA = 10.0
FEATURES = (
    "poverty_pct", "log_median_household_income", "unemployment_pct",
    "low_access_population_sd_pct_2020", "urban", "lila_sd_half_10",
)
NAMES = {
    "poverty_pct": "Poverty rate",
    "log_median_household_income": "Median household income (log scale)",
    "unemployment_pct": "Unemployment rate",
    "low_access_population_sd_pct_2020": "Population share with low store access",
    "urban": "Urban versus rural classification",
    "lila_sd_half_10": "Low-income / low-store-access classification",
}
CAVEAT = ("Predicts expected SNAP participation among all households, not eligibility, "
          "food need or proven under-enrollment. Correlation is not causation. "
          "ACS 01/2020–12/2024 five-year estimates; verify with local outreach partners.")


def feature_frame(frame):
    """Strict allowlist: no SNAP counts, rates, MOEs, confidence or derived fields."""
    x = frame[["poverty_pct", "unemployment_pct", "low_access_population_sd_pct_2020", "urban", "lila_sd_half_10"]].apply(pd.to_numeric, errors="raise").copy()
    income = pd.to_numeric(frame["median_household_income_usd"], errors="raise")
    x["log_median_household_income"] = np.log(income.where(income > 0))
    return x[list(FEATURES)].replace([np.inf, -np.inf], np.nan)


def estimator():
    # Every transform is fitted inside its training fold, including inner CV.
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=ALPHA, solver="svd"))


def classify_gap(actual, expected, moe, tolerance, enabled=True, complete=True):
    if actual is None or expected is None or not np.isfinite(actual) or not np.isfinite(expected):
        return "unavailable", "No model result: missing SNAP estimate or non-household tract."
    if not enabled:
        return "uncertain", "Model did not improve on the naive baseline; strong labels disabled."
    if not complete:
        return "uncertain", "At least one predictor was missing and imputed; local review required."
    if moe is None or not np.isfinite(moe) or moe < 0 or actual <= 0 or moe >= 10 or moe / (1.645 * actual) > 0.30:
        return "uncertain", "SNAP estimate has a wide, missing or unstable margin of error."
    if expected - actual > moe + tolerance:
        return "likely under-enrolled", "Outreach hypothesis only: shortfall exceeds SNAP MOE plus held-out model-error allowance."
    return "uncertain", "No robust shortfall signal after SNAP MOE and model-error allowance; not proof of adequate enrollment."


def build_predictions(frame):
    frame = frame.copy().sort_values("geoid", kind="stable").reset_index(drop=True)
    frame["geoid"] = frame.geoid.astype(str)
    if frame.geoid.duplicated().any() or not frame.geoid.str.fullmatch(r"\d{11}").all():
        raise ValueError("Unique 11-digit string GEOIDs are required")
    x_all = feature_frame(frame)
    y_all = pd.to_numeric(frame.snap_pct, errors="raise")
    valid = y_all.notna() & y_all.between(0, 100) & (frame.households > 0) & (frame.population > 0)
    x, y = x_all.loc[valid].reset_index(drop=True), y_all.loc[valid].reset_index(drop=True)
    indexes = frame.index[valid].to_numpy()
    if len(y) < 20:
        raise ValueError("At least 20 valid household tracts required")
    rows = []
    for idx, row in frame.iterrows():
        rows.append({"geoid": row.geoid, "actual_pct": float(row.snap_pct) if pd.notna(row.snap_pct) else None,
                     "snap_moe_pp": float(row.snap_moe_pp) if pd.notna(row.snap_moe_pp) else None,
                     "expected_pct": None, "gap_pp": None, "baseline_pct": None,
                     "fold": None, "model_tolerance_pp": None, "intercept_pct": None,
                     "drivers_json": "[]", "label": "unavailable",
                     "reason": "No model result: missing SNAP estimate or non-household tract."})
    preds, baselines = np.zeros(len(y)), np.zeros(len(y))
    outer = KFold(n_splits=5, shuffle=True, random_state=SEED)
    fold_metrics = []
    for fold, (train, test) in enumerate(outer.split(x)):
        fit = estimator().fit(x.iloc[train], y.iloc[train])
        predictions = np.clip(fit.predict(x.iloc[test]), 0, 100)
        baseline = float(y.iloc[train].mean())
        # No outer held-out outcomes affect their own model-error allowance.
        inner = cross_val_predict(estimator(), x.iloc[train], y.iloc[train], cv=KFold(5, shuffle=True, random_state=SEED))
        tolerance = max(5.0, float(mean_absolute_error(y.iloc[train], np.clip(inner, 0, 100))))
        preds[test], baselines[test] = predictions, baseline
        z = fit[1].transform(fit[0].transform(x.iloc[test]))
        contributions = z * fit[2].coef_
        for j, pos in enumerate(test):
            idx = indexes[pos]
            drivers = []
            for f, contribution in zip(FEATURES, contributions[j]):
                drivers.append({"feature": f, "name": NAMES[f], "contribution_pp": float(contribution),
                    "description": f"{NAMES[f]}: {abs(contribution):.1f} pp {'higher' if contribution >= 0 else 'lower'} expected participation versus the training-fold average (association, not cause)."})
            drivers.sort(key=lambda d: (-abs(d["contribution_pp"]), d["feature"]))
            r = rows[idx]
            r.update(expected_pct=float(predictions[j]), gap_pp=float(y.iloc[pos] - predictions[j]),
                     baseline_pct=baseline, fold=fold, model_tolerance_pp=tolerance,
                     intercept_pct=float(fit[2].intercept_), drivers_json=json.dumps(drivers, separators=(",", ":"), allow_nan=False))
        fold_metrics.append({"fold": fold, "train_tracts": len(train), "test_tracts": len(test),
                             "mae_pp": float(mean_absolute_error(y.iloc[test], predictions)),
                             "r2": float(r2_score(y.iloc[test], predictions)), "tolerance_pp": tolerance})
    meta = {"model": "Standardized ridge regression", "alpha": ALPHA, "seed": SEED,
            "features": list(FEATURES), "tracts_total": len(frame), "tracts_modeled": len(y),
            "tracts_excluded": int((~valid).sum()), "cv_folds": 5,
            "cv_r2": float(r2_score(y, preds)), "cv_mae_pp": float(mean_absolute_error(y, preds)),
            "baseline_r2": float(r2_score(y, baselines)), "baseline_mae_pp": float(mean_absolute_error(y, baselines)),
            "baseline": "Outer-training-fold mean SNAP rate", "fold_metrics": fold_metrics,
            "caveat": CAVEAT,
            "flag_rule": "expected-actual > SNAP 90% MOE + max(5pp, inner-training-OOF MAE); MOE<10pp; MOE/(1.645*actual)<=0.30; actual>0; all predictors present; model beats baseline overall",
            "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit-learn": sklearn.__version__}}
    enabled = meta["cv_mae_pp"] < meta["baseline_mae_pp"] and meta["cv_r2"] > 0
    for i in indexes:
        r = rows[i]
        r["label"], r["reason"] = classify_gap(r["actual_pct"], r["expected_pct"], r["snap_moe_pp"], r["model_tolerance_pp"], enabled=enabled, complete=not x_all.iloc[i].isna().any())
    result = pd.DataFrame(rows)
    meta["label_counts"] = {str(k): int(v) for k, v in result.label.value_counts().sort_index().items()}
    return result, meta


def write_outputs(source, output):
    frame = pd.read_csv(source, dtype={"geoid": str})
    result, meta = build_predictions(frame)
    meta["input_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    result.to_csv(output / "snap_gap.csv", index=False, float_format="%.10f")
    (output / "snap_gap_metadata.json").write_text(json.dumps(meta, indent=2, allow_nan=False) + "\n")
    card = f"""# SNAP enrollment gap — model card (11/2026)

## Purpose and safe use
{CAVEAT}
The label **likely under-enrolled** is only a model-relative outreach hypothesis. Eligibility and the eligible-but-not-enrolled population are unobserved. Never claim this model identifies eligible residents, predicts future demand, proves under-enrollment or dispatches resources. It predicts a contemporaneous tract aggregate, not individuals or future outcomes.

## Data and features
Input: `output/tract_clean.csv`; SHA-256 `{meta['input_sha256']}`. Four counties: Lake, Orange, Osceola, Seminole. {meta['tracts_total']} tracts; {meta['tracts_modeled']} modeled; {meta['tracts_excluded']} excluded (missing SNAP rate / non-household tracts). Target: ACS percent of **all households** receiving SNAP, not a participation rate among eligible households. ACS 01/2020–12/2024 five-year estimates. SRAM uses 04/2020 population and 06/2025 SNAP-store data, release 07/2026; not FARA supermarket access.

Allowlisted predictors: {', '.join(FEATURES)}. Income is natural-log transformed; nonpositive/topcoded-unavailable income is missing, not fabricated. No SNAP count, rate, MOE, confidence, SNAP-derived completeness/ranking, GEOID, neighborhood, county, or local review enters prediction. SNAP MOE is used **only after prediction** for the labeling rule.

## Reproducibility and validation
Run `.venv/bin/python snap_gap_model.py` after `.venv/bin/python clean.py --config pipeline_config.json`, then `cd app && npm run build`. Dependencies in `requirements-model.lock.txt`. No network or model API. Sorted string GEOIDs; fixed seed {SEED}; five shuffled folds; ridge alpha {ALPHA}, SVD solver, no tuning. Median imputation and standardization fit only inside training folds. Each modeled tract's displayed prediction is from a model that never saw its target. No in-sample predictions are displayed. Baseline is the matching outer training-fold mean. Per-tract error allowance is max(5 pp, five-fold inner-OOF MAE on outer training rows), never its own error. No final full-data model is substituted for OOF outputs.

| Metric | Ridge OOF | Naive mean OOF |
|---|---:|---:|
| MAE (percentage points) | {meta['cv_mae_pp']:.4f} | {meta['baseline_mae_pp']:.4f} |
| R² (pooled OOF) | {meta['cv_r2']:.4f} | {meta['baseline_r2']:.4f} |

Metrics are against noisy ACS estimates, not ground truth. Equal tract weighting, not household weighting. Predictions clipped to 0–100; contribution sums reconstruct the raw prediction before clipping. Coefficient contributions (standardized feature × fold coefficient) are relative to the training-fold mean, are not causal, and can be unstable with correlated predictors. Top three absolute contributions shown; all stored for audit.

## Conservative flag rule
{meta['flag_rule']}.
Gap = **actual minus expected**, in pp (negative = below expected). Strong labels disabled if model fails to improve MAE over baseline or R² <=0. Missing predictors force uncertain, even when imputed. Missing targets/non-household tracts are unavailable. All other cases are uncertain; this does **not** establish adequate enrollment. Labels: {json.dumps(meta['label_counts'], sort_keys=True)}.

The SNAP MOE gate follows the existing conservative CV heuristic. MOE is a 90% ACS margin, not a calibrated probability of under-enrollment. Adding model MAE to MOE is a screening allowance, NOT a combined confidence interval or hypothesis test. No calibrated probability, multiple-comparison control, spatial CV, external/temporal validation, eligibility labels or actual sample sizes exist. Predictor uncertainty (including poverty/income MOEs) is **not** propagated. Nearby tracts may be correlated, making random-fold performance optimistic. Demographic composition and eligibility rules are unmodeled; aggregate associations can obscure inequities. Do not reduce food allocation based on this output. Validate with organizers, eligible-household denominators and current outreach outcomes before operational use.

## Files and refresh safety
`output/snap_gap.csv` and `snap_gap_metadata.json` are separate derived outputs. App reads a separate snapshot; source tract JSON/CSV and geometry stay unchanged. Snapshot sync checks the input hash and refuses stale model results. Resident flyers never receive this section. No deployment, submission, transmission or paid service is used.
"""
    (source.parent.parent / "MODEL_CARD.md").write_text(card)
    print(json.dumps(meta, indent=2))
    return result, meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--input", type=Path, default=root / "output/tract_clean.csv")
    parser.add_argument("--output", type=Path, default=root / "output")
    args = parser.parse_args()
    write_outputs(args.input, args.output)
