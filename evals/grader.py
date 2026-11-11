"""Automated faithfulness grader for write-ups.

A write-up is FAITHFUL when all of these hold:
  1. every number it states can be found in the facts (within rounding),
  2. it names the tract's own place and no other Central Florida place,
  3. it states the evidence confidence label, and the label is correct.
It separately records which "shaky numbers" the write-up asked the organizer
to verify (a question sentence mentioning that topic).

The grader is deliberately simple and auditable. Its own accuracy is checked
two ways: seeded-error tests (we break correct text on purpose and confirm the
grader notices) and, once Kevin fills them in, hand grades (Cohen's kappa).
"""
from __future__ import annotations

import re

NUM = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?")
ALWAYS_OK = {10.0, 90.0, 100.0, 2020.0, 2024.0, 2025.0, 2026.0, 0.5, 1.0, 2.0, 3.0}
TOPIC = {
    "poverty_estimate": ("poverty",),
    "snap_estimate": ("snap",),
    "distance_definition": ("driv", "distance", "straight"),
    "small_population": ("small", "population"),
    "place_label": ("label", "name", "call", "boundar"),
}


def _allowed_numbers(f: dict) -> set[float]:
    vals = set(ALWAYS_OK)
    def add(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            for x in (v, round(v, 1), round(v), round(v, 0)):
                vals.add(float(x))
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)
        elif isinstance(v, str):
            for m in NUM.findall(v):
                add(float(m.replace(",", "")))
    for v in f.values():
        add(v)
    return vals


def unsupported_numbers(text: str, f: dict) -> list[str]:
    allowed = _allowed_numbers(f)
    bad = []
    for raw in NUM.findall(text.replace("#", " ")):
        n = abs(float(raw.replace(",", "")))
        if not any(abs(n - a) <= 0.051 for a in allowed):
            bad.append(raw)
    return bad


def stated_confidence(text: str):
    m = re.search(r"\b(High|Medium|Low)\b[\s*_\"'“”]*(?:evidence[\s*_]+)?confidence", text, re.I) or \
        re.search(r"confidence[^.?!]{0,40}?\b(High|Medium|Low)\b", text, re.I)
    return m.group(1).capitalize() if m else None


def wrong_places(text: str, f: dict, all_places: set[str]) -> list[str]:
    own = f["place_name"].lower()
    low = text.lower()
    out = []
    for p in all_places:
        pl = p.lower()
        if pl in own or own in pl or pl == f["county"].lower():
            continue
        if re.search(rf"\b{re.escape(pl)}\b", low):
            out.append(p)
    return sorted(out)


def asked_about(text: str, f: dict) -> list[str]:
    questions = [s.lower() for s in re.findall(r"[^.?!]*\?", text)]
    return [k for k in f["shaky_numbers"] if any(any(w in q for w in TOPIC[k]) for q in questions)]


def grade(text: str, f: dict, all_places: set[str]) -> dict:
    nums = unsupported_numbers(text, f)
    places = wrong_places(text, f, all_places)
    conf = stated_confidence(text)
    name_ok = f["place_name"].lower() in text.lower()
    asked = asked_about(text, f)
    g = {
        "unsupported_numbers": nums,
        "wrong_places": places,
        "names_own_place": name_ok,
        "stated_confidence": conf,
        "confidence_correct": conf == f["evidence_confidence"],
        "shaky_numbers": f["shaky_numbers"],
        "shaky_asked": asked,
        "shaky_coverage": (len(asked) / len(f["shaky_numbers"])) if f["shaky_numbers"] else None,
    }
    g["faithful"] = not nums and not places and name_ok and g["confidence_correct"]
    return g


def seeded_errors(text: str, f: dict, other_place: str) -> dict[str, str]:
    """Break a correct write-up in known ways; each version SHOULD fail grading."""
    p = f"{f['poverty_pct']}"
    other_label = {"High": "Low", "Medium": "High", "Low": "High"}[f["evidence_confidence"]]
    return {
        "wrong_number": text.replace(p, f"{round(f['poverty_pct'] + 7.3, 1)}", 1),
        "wrong_place": text.replace(f["place_name"], other_place, 1),
        "wrong_confidence": re.sub(rf"\b{f['evidence_confidence']}\b(?=\s+evidence)", other_label, text, count=1),
        "invented_stat": text + " About 2,340 residents lack a car.",
    }
