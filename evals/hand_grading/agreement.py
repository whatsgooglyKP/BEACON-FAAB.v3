"""Hand-grading workflow: a 30-item sheet for Kevin + grader-vs-human agreement.

``to_grade.csv`` is (re)generated only while no human grades are filled in,
so Kevin's work is never overwritten. Fill the ``human_faithful`` column with
yes/no (and optional notes), then rerun ``python -m evals.run --all`` or
``python -m evals.hand_grading.agreement`` to get Cohen's kappa and raw agreement.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from ..metrics import cohen_kappa

SHEET = Path(__file__).parent / "to_grade.csv"
COLS = ["item_id", "config", "mode", "geoid", "place_name", "facts_json", "writeup", "auto_faithful",
        "auto_problems", "human_faithful", "human_notes"]
INSTRUCTIONS = ("Mark human_faithful = yes only if every number and place matches facts_json, the evidence "
                "confidence label is stated correctly, and nothing is invented. Otherwise no.")


def _filled():
    if not SHEET.exists():
        return False
    with SHEET.open() as fh:
        return any((r.get("human_faithful") or "").strip() for r in csv.DictReader(fh))


def refresh_template(results, n=30, seed=7):
    if _filled():
        return False
    pool = [w for r in results for w in r["writeups"] if w["text"]]
    live = [w for w in pool if w["mode"] == "gemini"]
    pool = live or pool
    random.Random(seed).shuffle(pool)
    with SHEET.open("w", newline="") as fh:
        wr = csv.DictWriter(fh, COLS)
        wr.writeheader()
        for i, w in enumerate(pool[:n], 1):
            g = w["grade"]
            probs = [f"numbers:{g['unsupported_numbers']}" if g["unsupported_numbers"] else "",
                     f"places:{g['wrong_places']}" if g["wrong_places"] else "",
                     "" if g["confidence_correct"] else f"confidence stated:{g['stated_confidence']}"]
            wr.writerow({"item_id": i, "config": w["config_name"], "mode": w["mode"], "geoid": w["geoid"],
                         "place_name": w["facts"]["place_name"], "facts_json": json.dumps(w["facts"]),
                         "writeup": w["text"], "auto_faithful": "yes" if g["faithful"] else "no",
                         "auto_problems": "; ".join(p for p in probs if p), "human_faithful": "", "human_notes": ""})
    return True


def agreement():
    """Return grader-vs-human agreement, or a 'pending' status if no hand grades yet."""
    if not _filled():
        return {"status": "pending", "instructions": INSTRUCTIONS, "sheet": str(SHEET.name)}
    with SHEET.open() as fh:
        rows = [r for r in csv.DictReader(fh) if (r["human_faithful"] or "").strip().lower() in ("yes", "no")]
    a = [r["auto_faithful"] == "yes" for r in rows]
    h = [r["human_faithful"].strip().lower() == "yes" for r in rows]
    return {"status": "done", "n": len(rows), "raw_agreement": sum(x == y for x, y in zip(a, h)) / len(rows),
            "cohen_kappa": cohen_kappa(a, h)}


if __name__ == "__main__":
    print(json.dumps(agreement(), indent=1))
