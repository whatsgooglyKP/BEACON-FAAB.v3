"""The feature under test: a short organizer-facing write-up per shortlisted tract.

NOTE: the shipped Beacon app has no generative AI; its explanations are
deterministic templates. This module is an *evaluation-only candidate feature*
— a Gemini-written note — so we can measure, before anything ships, whether a
model stays faithful to Beacon's numbers.

Two backends:
* mock  — deterministic templates (no network, no cost). Used to test the
          harness itself. Results are always labelled MOCK in reports.
* gemini — the Gemini REST API. The key is read from the GEMINI_API_KEY
          environment variable, sent only in a request header, and never
          printed, logged, or stored.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

from .beacon_rules import Q75, shaky_numbers
from .data import display_name

PROMPTS = Path(__file__).parent / "prompts"
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def facts_for(t: dict, rank: int) -> dict:
    """The only information the writer is allowed to use (also what the grader checks against)."""
    gap = t.get("snap_gap") or {}
    return {
        "rank_on_shortlist": rank,
        "place_name": display_name(t),
        "county": t["county"],
        "census_tract": t["tract_number"],
        "geoid": t["geoid"],
        "poverty_pct": t["poverty_pct"],
        "poverty_margin_of_error_points": t["poverty_moe_pp"],
        "poverty_90pct_interval": [t["poverty_lower90_pct"], t["poverty_upper90_pct"]],
        "poverty_cutoff_pct": round(Q75, 1),
        "low_income_low_access_straight_line": bool(t["lila_sd_half_10"] == 1),
        "low_income_low_access_driving": bool(t["lila_dd_half_10"] == 1),
        "snap_participation_pct": t["snap_pct"],
        "snap_margin_of_error_points": t["snap_moe_pp"],
        "snap_comparison_label": gap.get("label"),
        "evidence_confidence": t["evidence_confidence"],
        "place_label_confidence": t["mapping_confidence"],
        "shaky_numbers": shaky_numbers(t),
    }


QUESTION = {
    "poverty_estimate": "Can a local partner confirm whether the poverty estimate for this area looks right?",
    "snap_estimate": "Can someone check the SNAP participation figure against local enrollment data?",
    "distance_definition": "Does driving access or straight-line distance better match how residents reach stores here?",
    "small_population": "Is the small population base here large enough to act on?",
    "place_label": "Does the place label match what residents call this area?",
}


def mock_writeup(f: dict, prompt_version: str) -> str:
    """Deterministic stand-in for a model. Not evidence of model quality."""
    base = (f"{f['place_name']} in {f['county']} County (tract {f['census_tract']}) is #{f['rank_on_shortlist']} on the shortlist "
            f"because its poverty estimate of {f['poverty_pct']}% is above the {f['poverty_cutoff_pct']}% cutoff and it is flagged for low income and low store access. ")
    if prompt_version == "v1":
        return base + f"It has {f['evidence_confidence']} evidence confidence."
    txt = (base.replace(f"{f['poverty_pct']}%", f"{f['poverty_pct']}% ± {f['poverty_margin_of_error_points']} points")
           + f"It has {f['evidence_confidence']} evidence confidence. This is a screening signal, not proof of unmet food need.")
    for s in f["shaky_numbers"]:
        txt += " " + QUESTION[s]
    return txt


def render_prompt(f: dict, prompt_version: str) -> str:
    return (PROMPTS / f"{prompt_version}.txt").read_text().replace("{facts}", json.dumps(f, indent=1))


class GeminiError(RuntimeError):
    def __init__(self, msg, retries=0):
        super().__init__(msg)
        self.retries = retries


def gemini_writeup(prompt: str, model: str, temperature: float, seed: int, max_retries: int = 3, timeout: int = 90):
    """Call Gemini once (with retries). Returns (text, usage, retries, latency_s).

    Retries only on rate-limit / server errors, with exponential backoff. The
    API key travels only in the x-goog-api-key header; error messages we raise
    contain status codes, never headers.
    """
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiError("GEMINI_API_KEY not set")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "seed": seed, "maxOutputTokens": 2048},
    }
    retries = 0
    while True:
        t0 = time.perf_counter()
        try:
            r = requests.post(API.format(model=model), json=body, timeout=timeout,
                              headers={"x-goog-api-key": key, "Content-Type": "application/json"})
            status = r.status_code
        except requests.RequestException as exc:
            status, r = f"network:{type(exc).__name__}", None
        latency = time.perf_counter() - t0
        if r is not None and status == 200:
            data = r.json()
            parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            return text, data.get("usageMetadata", {}), retries, latency
        if retries >= max_retries or (isinstance(status, int) and status not in (429, 500, 502, 503, 504)):
            detail = ""
            try:
                detail = (r.json().get("error") or {}).get("status", "") if r is not None else ""
            except ValueError:
                pass
            raise GeminiError(f"Gemini call failed with status {status} {detail} after {retries} retries".replace("  ", " "), retries)
        retries += 1
        time.sleep(2 ** retries)
