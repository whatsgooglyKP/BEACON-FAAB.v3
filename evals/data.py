"""Load the cleaned tract data the Beacon app ships with, plus a content hash.

We hash the input file so every telemetry row records exactly which data the
experiment ran on (if the data changes, the hash changes and runs are not
silently compared across different inputs).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TRACTS_JSON = REPO / "app" / "public" / "data" / "tracts.json"
SNAP_GAP_JSON = REPO / "app" / "public" / "data" / "snap_gap.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tracts() -> list[dict]:
    """Return the 490 Central Florida tracts as plain dicts (one per GEOID)."""
    tracts = json.loads(TRACTS_JSON.read_text())["tracts"]
    gaps = {r["geoid"]: r for r in json.loads(SNAP_GAP_JSON.read_text())["rows"]}
    for t in tracts:
        t["snap_gap"] = gaps.get(t["geoid"])
    return tracts


def data_fingerprint() -> str:
    """Short combined hash of the two input files used by the lab."""
    h = hashlib.sha256()
    for p in (TRACTS_JSON, SNAP_GAP_JSON):
        h.update(file_sha256(p).encode())
    return h.hexdigest()[:16]


def display_name(t: dict) -> str:
    """Same friendly-name rule as ``displayName`` in app/src/domain.js."""
    return t.get("official_neighborhood") or t.get("place_name") or f"Unincorporated {t['county']}"
