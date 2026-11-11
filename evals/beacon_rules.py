"""Python ports of Beacon's two deterministic rules, kept line-for-line close.

1. ``candidates`` mirrors ``candidates()`` in app/src/domain.js (the shortlist
   and its ordering). A parity test runs the real JS and compares outputs.
2. ``recompute_flags`` mirrors the confidence rule in pipeline_data.py
   (evidence_confidence High / Medium / Low). We need it so that when we
   *perturb* an input number, the derived flags and label update the same way
   the real pipeline would update them.
"""
from __future__ import annotations

import copy

Q75 = 17.025  # four-county 75th-percentile poverty cutoff, same constant as the app


def recompute_flags(t: dict, q75: float = Q75) -> dict:
    """Recompute uncertainty flags + evidence_confidence from raw indicators.

    Mirrors pipeline_data.py lines ~470-512. Returns a new dict; the input is
    not modified.
    """
    t = copy.copy(t)
    core = [t.get("poverty_pct"), t.get("snap_pct"), t.get("lila_sd_half_10")]
    t["core_completeness"] = sum(v is not None for v in core) / 3
    t["small_denominator_proxy"] = bool(
        (t.get("poverty_universe") or 0) < 500 or (t.get("households") or 0) < 200
    )
    p, pm = t.get("poverty_pct"), t.get("poverty_moe_pp")
    s, sm = t.get("snap_pct"), t.get("snap_moe_pp")
    t["poverty_cv"] = (pm / (1.645 * p)) if p else None
    t["snap_cv"] = (sm / (1.645 * s)) if s else None
    t["high_poverty_moe"] = bool((t["poverty_cv"] or 0) > 0.30 or (pm or 0) >= 10)
    t["high_snap_moe"] = bool((t["snap_cv"] or 0) > 0.30 or (sm or 0) >= 10)
    sd, dd = t.get("lila_sd_half_10"), t.get("lila_dd_half_10")
    t["distance_definition_sensitive"] = bool(sd is not None and dd is not None and sd != dd)
    if p is not None and pm is not None:
        t["poverty_lower90_pct"] = round(min(100, max(0, p - pm)), 6)
        t["poverty_upper90_pct"] = round(min(100, max(0, p + pm)), 6)
    if (
        t["core_completeness"] < 1
        or t["small_denominator_proxy"]
        or t.get("group_quarters_flag") == 1
    ):
        t["evidence_confidence"] = "Low"
    elif t["high_poverty_moe"] or t["high_snap_moe"] or t["distance_definition_sensitive"]:
        t["evidence_confidence"] = "Medium"
    else:
        t["evidence_confidence"] = "High"
    return t


def shaky_numbers(t: dict) -> list[str]:
    """Which numbers on this tract an organizer should double-check.

    These are the pipeline's own uncertainty flags, renamed in plain English.
    The write-up feature is asked to raise a verification question for each.
    """
    out = []
    if t.get("high_poverty_moe"):
        out.append("poverty_estimate")
    if t.get("high_snap_moe"):
        out.append("snap_estimate")
    if t.get("distance_definition_sensitive"):
        out.append("distance_definition")
    if t.get("small_denominator_proxy"):
        out.append("small_population")
    if (t.get("mapping_confidence") or "") == "Low":
        out.append("place_label")
    return out


def eligible(t: dict, distance: str = "sd", conservative: bool = False, q75: float = Q75) -> bool:
    """Shortlist filter from domain.js ``candidates``."""
    pov = t.get("poverty_lower90_pct") if conservative else t.get("poverty_pct")
    return (
        t.get(f"lila_{distance}_half_10") == 1
        and t.get("poverty_pct") is not None
        and pov is not None
        and pov >= q75
        and t.get("core_completeness") == 1
        and not t.get("small_denominator_proxy")
        and t.get("group_quarters_flag") != 1
    )


def candidates(tracts: list[dict], distance: str = "sd", conservative: bool = False, q75: float = Q75) -> list[dict]:
    """Shortlist in the app's order: poverty desc, then LILA count desc, then GEOID."""
    rows = [t for t in tracts if eligible(t, distance, conservative, q75)]
    return sorted(
        rows,
        key=lambda t: (-t["poverty_pct"], -(t.get("low_income_low_access_sd") or 0), t["geoid"]),
    )


def confidence_label(t: dict, variant: str = "pipeline_v1", q75: float = Q75) -> str:
    """Evidence-confidence label under a named rule variant.

    pipeline_v1     — the shipped rule (stored in the data; see recompute_flags).
    margin_aware_v2 — experimental: identical, except a tract can only be
                      "High" if the poverty cutoff lies outside its 90%
                      interval, i.e. the shortlist decision would not change
                      anywhere inside the published margin of error.
    """
    base = t["evidence_confidence"]
    if variant == "pipeline_v1":
        return base
    if variant == "margin_aware_v2":
        if base == "High" and t.get("poverty_lower90_pct", 0) <= q75 <= t.get("poverty_upper90_pct", 0):
            return "Medium"
        return base
    raise ValueError(f"Unknown confidence variant: {variant}")
