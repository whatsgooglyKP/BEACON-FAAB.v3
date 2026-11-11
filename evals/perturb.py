"""Perturbation and stability tests for rankings and confidence labels.

Two kinds of tests:

1. Targeted cases from the gold set: edit one number, recompute flags with the
   pipeline rule, re-rank, and check the rule-derived expectation.
2. Monte Carlo stability: redraw every tract's poverty and SNAP estimates
   inside their published 90% margins of error (normal noise, sd = MOE/1.645),
   re-rank, and measure how much the top 10 moves. A fixed seed makes this
   exactly reproducible.
"""
from __future__ import annotations

import random

from .beacon_rules import eligible, recompute_flags
from .ranking import rank


def _lens(spec):
    return "dd" if spec["variant"] == "screening_driving" else "sd"


def run_cases(tracts, cases, spec):
    """Return a list of {id, passed, detail} for one ranking spec."""
    results = []
    for case in cases:
        if case.get("lens") and case["lens"] != _lens(spec):
            continue
        if case.get("variants") and spec["variant"] not in case["variants"]:
            continue
        edited = [recompute_flags({**t, **case["changes"]}) if t["geoid"] == case["geoid"] else t for t in tracts]
        target = next(t for t in edited if t["geoid"] == case["geoid"])
        order = [t["geoid"] for t in rank(edited, spec)]
        got = {"confidence": target["evidence_confidence"], "in_shortlist": case["geoid"] in order,
               "rank": order.index(case["geoid"]) + 1 if case["geoid"] in order else None}
        exp = case["expect"]
        ok = True
        if "confidence" in exp: ok &= got["confidence"] == exp["confidence"]
        if "confidence_not" in exp: ok &= got["confidence"] != exp["confidence_not"]
        if "in_shortlist" in exp:
            # Membership expectations for the straight-line rule; the driving lens only shares structural ones.
            ok &= got["in_shortlist"] == exp["in_shortlist"]
        if "rank" in exp: ok &= got["rank"] == exp["rank"]
        results.append({"id": case["id"], "passed": bool(ok), "got": got, "expect": exp})
    return results


def _redraw(tracts, rng):
    out = []
    for t in tracts:
        n = dict(t)
        for v, m in (("poverty_pct", "poverty_moe_pp"), ("snap_pct", "snap_moe_pp")):
            if n.get(v) is not None and n.get(m) is not None:
                n[v] = min(100.0, max(0.0, rng.gauss(n[v], n[m] / 1.645)))
        out.append(recompute_flags(n))
    return out


def monte_carlo(tracts, spec, draws: int, seed: int, k: int = 10):
    """Top-k stability + per-tract shortlist flip rates under sampling noise."""
    rng = random.Random(seed)
    base = [t["geoid"] for t in rank(tracts, spec)]
    base_top, base_set = set(base[:k]), set(base)
    lens = _lens(spec)
    conservative = spec["variant"] == "screening_conservative"
    jacc, flips = [], {t["geoid"]: 0 for t in tracts}
    for _ in range(draws):
        noisy = _redraw(tracts, rng)
        top = set(t["geoid"] for t in rank(noisy, spec)[:k])
        jacc.append(len(top & base_top) / len(top | base_top) if top | base_top else 1.0)
        for t in noisy:
            if eligible(t, lens, conservative) != (t["geoid"] in base_set):
                flips[t["geoid"]] += 1
    return {"top10_jaccard": jacc, "flip_rate": {g: c / draws for g, c in flips.items()}}


def calibration(tracts, flip_rate, lens="sd"):
    """Mean shortlist flip rate grouped by the stored confidence label.

    Only tracts whose membership can actually depend on noisy numbers are used
    (access flag set, complete, not small, not group quarters). A well-behaved
    label should show High < Medium flip rates: "High confidence" picks should
    be the ones that stay put when the estimates wobble.
    """
    groups: dict[str, list[float]] = {}
    for t in tracts:
        if t.get(f"lila_{lens}_half_10") == 1 and t.get("core_completeness") == 1 and not t.get("small_denominator_proxy") and t.get("group_quarters_flag") != 1:
            groups.setdefault(t["evidence_confidence"], []).append(flip_rate[t["geoid"]])
    return {k: {"n": len(v), "mean_flip_rate": sum(v) / len(v)} for k, v in sorted(groups.items())}
