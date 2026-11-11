"""Ranking variants that the A/B experiments compare.

Each variant takes the tract list and returns an ordered shortlist. The
reference variant ("screening_v1") is exactly what the shipped app does today.
The others each change ONE idea so a comparison isolates its effect:

- screening_conservative: use the 90% lower bound of poverty for the cutoff
  (the app's "conservative" toggle).
- screening_driving: use the driving-distance access flag instead of
  straight-line (the app's distance toggle).
- composite: same eligibility filter, but order by a weighted score of
  standardized poverty, LILA population and SNAP-gap shortfall instead of by
  poverty alone. Weights come from the config file.
"""
from __future__ import annotations

import statistics

from .beacon_rules import candidates


def _z(values: list[float]) -> list[float]:
    mu = statistics.fmean(values)
    sd = statistics.pstdev(values) or 1.0
    return [(v - mu) / sd for v in values]


def rank(tracts: list[dict], spec: dict) -> list[dict]:
    """Return the ordered shortlist for one ranking spec from a config file."""
    variant = spec["variant"]
    if variant == "screening_v1":
        return candidates(tracts, "sd", False)
    if variant == "screening_conservative":
        return candidates(tracts, "sd", True)
    if variant == "screening_driving":
        return candidates(tracts, "dd", False)
    if variant == "composite":
        w = spec.get("weights", {})
        rows = candidates(tracts, "sd", False)
        if not rows:
            return rows
        pov = _z([t["poverty_pct"] for t in rows])
        lila = _z([float(t.get("low_income_low_access_sd") or 0) for t in rows])
        gap = _z([-(t.get("snap_gap") or {}).get("gap_pp", 0.0) or 0.0 for t in rows])
        score = {
            t["geoid"]: w.get("poverty", 1.0) * a + w.get("lila", 0.0) * b + w.get("snap_shortfall", 0.0) * c
            for t, a, b, c in zip(rows, pov, lila, gap)
        }
        return sorted(rows, key=lambda t: (-score[t["geoid"]], t["geoid"]))
    raise ValueError(f"Unknown ranking variant: {variant}")
