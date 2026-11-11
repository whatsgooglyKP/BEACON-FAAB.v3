"""Build the labeled test set ("gold set") — transparently, from rules.

IMPORTANT: there are NO human or expert labels in this file. Every expected
outcome is derived mechanically, and each section says how:

* reference_top10 — the shortlist produced by the *shipped app code*
  (app/src/domain.js, executed with Node). It is a regression reference: a
  variant that disagrees with it is not "wrong", it is different, and the
  report measures by how much.
* robust_core — tracts that still pass the screening rule when poverty is
  replaced by its 90% lower bound (the most defensible picks).
* confidence_labels — High/Medium/Low recomputed from the raw indicators with
  the pipeline's documented rule (pipeline_data.py).
* perturbation_cases — synthetic edits to ONE number on a real tract whose
  correct consequence follows directly from the written rule (e.g. "if the
  poverty MOE is widened to 12 points the label must drop to Medium").
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .beacon_rules import Q75, candidates, recompute_flags
from .data import REPO, data_fingerprint, load_tracts

GOLD_PATH = Path(__file__).parent / "gold" / "gold_set.json"


def _reference_lists(tracts):
    """Prefer the real JS implementation; fall back to the verified Python port."""
    if shutil.which("node"):
        out = subprocess.run(
            ["node", str(REPO / "evals" / "js_reference.mjs")],
            check=True, capture_output=True, text=True,
        ).stdout
        return json.loads(out), "app/src/domain.js via node"
    py = {f"{d}_{str(c).lower()}": [t["geoid"] for t in candidates(tracts, d, c)]
          for d in ("sd", "dd") for c in (False, True)}
    return py, "python port (node unavailable)"


def _perturbation_cases(tracts, ref):
    """Hand-written edit templates applied to deterministically chosen tracts."""
    by = {t["geoid"]: t for t in tracts}
    shortlist = ref["sd_false"]
    first, eleventh = shortlist[0], shortlist[10]
    high_in = next(g for g in shortlist if by[g]["evidence_confidence"] == "High")
    # A tract in the shortlist whose two distance flags agree, so making them disagree is a real change.
    agree = next(g for g in shortlist if by[g]["lila_dd_half_10"] == by[g]["lila_sd_half_10"] and by[g]["evidence_confidence"] == "High") if any(
        by[g]["lila_dd_half_10"] == by[g]["lila_sd_half_10"] and by[g]["evidence_confidence"] == "High" for g in shortlist) else high_in
    top_pov = by[first]["poverty_pct"]
    return [
        {"id": "P1_widen_poverty_moe", "geoid": high_in, "changes": {"poverty_moe_pp": 12.0},
         "why": "Rule: poverty MOE >= 10 points sets high_poverty_moe, so a High label must fall to Medium.",
         "expect": {"confidence": "Medium"}},
        {"id": "P2_tiny_household_count", "geoid": first, "changes": {"households": 150},
         "why": "Rule: fewer than 200 households is a small-denominator proxy -> Low confidence and excluded.",
         "expect": {"confidence": "Low", "in_shortlist": False}},
        {"id": "P3_poverty_below_cutoff", "geoid": first, "changes": {"poverty_pct": round(Q75 - 1, 1)},
         "why": f"Rule: poverty below the {Q75}% cutoff removes the tract from the shortlist.",
         "expect": {"in_shortlist": False}},
        {"id": "P4_lose_access_flag", "geoid": first, "changes": {"lila_sd_half_10": 0},
         "why": "Rule: straight-line LILA flag is required for the straight-line shortlist.",
         "expect": {"in_shortlist": False}, "lens": "sd"},
        {"id": "P5_distance_disagreement", "geoid": agree, "changes": {"lila_dd_half_10": 1 - by[agree]["lila_sd_half_10"]},
         "why": "Rule: straight-line vs driving flags disagreeing marks distance sensitivity -> at most Medium.",
         "expect": {"confidence_not": "High"}},
        {"id": "P6_promote_eleventh", "geoid": eleventh, "changes": {"poverty_pct": round(top_pov + 5, 1), "poverty_moe_pp": 5.0},
         "why": "Rule: shortlist is ordered by poverty; a tract with the highest poverty must rank #1.",
         "expect": {"rank": 1}, "variants": ["screening_v1"]},
        {"id": "P7_group_quarters", "geoid": high_in, "changes": {"group_quarters_flag": 1},
         "why": "Rule: group-quarters tracts are Low confidence and excluded.",
         "expect": {"confidence": "Low", "in_shortlist": False}},
        {"id": "P8_no_change_control", "geoid": first, "changes": {},
         "why": "Control: no edit must leave the label and shortlist membership unchanged.",
         "expect": {"confidence": by[first]["evidence_confidence"], "in_shortlist": True}},
    ]


def build_gold() -> dict:
    tracts = load_tracts()
    ref, source = _reference_lists(tracts)
    gold = {
        "label_provenance": "Rule-derived only. No human/expert labels. See evals/gold.py docstring.",
        "data_fingerprint": data_fingerprint(),
        "reference_source": source,
        "poverty_cutoff_pct": Q75,
        "reference_top10": ref["sd_false"][:10],
        "reference_shortlist": ref,
        "robust_core": ref["sd_true"],
        "confidence_labels": {t["geoid"]: recompute_flags(t)["evidence_confidence"] for t in tracts},
        "perturbation_cases": _perturbation_cases(tracts, ref),
    }
    GOLD_PATH.parent.mkdir(exist_ok=True)
    GOLD_PATH.write_text(json.dumps(gold, indent=1, sort_keys=True))
    return gold
