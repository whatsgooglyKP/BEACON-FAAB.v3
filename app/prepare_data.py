"""Refresh the static app from audited CSV/GeoJSON outputs; standard library only."""
import base64
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/"output"
DEST=ROOT/"public/data"
KEEP_TEXT={"geoid","county_fips","place_geoid","tract_number"}

def typed(key,value):
    if value=="": return None
    if key in KEEP_TEXT: return value
    if value in ["True","False"]: return value=="True"
    if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?",value):
        number=float(value)
        return int(number) if number.is_integer() else number
    return value


def load_snap_gap(source, geoids):
    """Refuse stale or partial derived outputs, preserving audited tract JSON."""
    metadata = json.loads((source / "snap_gap_metadata.json").read_text())
    raw = (source / "tract_clean.csv").read_bytes()
    # Accept Windows (CRLF) checkouts: compare against both the raw and LF-normalized bytes.
    candidates = {hashlib.sha256(raw).hexdigest(), hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()}
    if metadata.get("input_sha256") not in candidates:
        raise ValueError("SNAP model is stale; rerun .venv/bin/python snap_gap_model.py before building the app")
    with (source / "snap_gap.csv").open(newline="") as file:
        rows = [{key: typed(key, value) for key, value in row.items()} for row in csv.DictReader(file)]
    if len(rows) != len(geoids) or {r["geoid"] for r in rows} != geoids:
        raise ValueError("SNAP model tract keys must exactly match audited tract keys")
    for row in rows:
        row["drivers"] = json.loads(row.pop("drivers_json"))
    return {"rows": rows, "metadata": metadata}


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    with (SOURCE/"tract_clean.csv").open(newline="") as file:
        tracts=[{key:typed(key,value) for key,value in row.items()} for row in csv.DictReader(file)]
    assert len(tracts)==490 and len({row["geoid"] for row in tracts})==490
    assert all(isinstance(row["geoid"],str) for row in tracts)
    gap = load_snap_gap(SOURCE, {row["geoid"] for row in tracts})
    (DEST/"snap_gap.json").write_text(json.dumps(gap,separators=(",",":"),allow_nan=False))
    (DEST/"tracts.json").write_text(json.dumps({"tracts":tracts},separators=(",",":"),allow_nan=False))
    for name in ["tracts.geojson","review_report.json","summary.json","run_info.json","input_manifest.json"]:
        shutil.copy2(SOURCE/name,DEST/name)
    logo=ROOT/"public/brand/beacon-white.png"
    metadata={"sourceSnapshot":"11/2026","dataHash":hashlib.sha256((SOURCE/"tract_clean.csv").read_bytes().replace(b"\r\n",b"\n")).hexdigest(),"brandLogoData":"data:image/png;base64,"+base64.b64encode(logo.read_bytes()).decode(),"sourceFolder":"https://drive.google.com/drive/folders/1zuwSZjkK3gcvEzNFPJ8THFRw9ulCgA-p","appendix":"https://docs.google.com/document/d/1L25DTxI31BlrH3QvB7k8H0rt6eowMiYA3YqHEwfJer0","usdaDocumentation":"https://www.ers.usda.gov/data-products/food-access-research-atlas/documentation/snap-authorized-retailer-access-map-reference-guide"}
    (DEST/"metadata.json").write_text(json.dumps(metadata))
    print(f"Synced {len(tracts)} audited tracts, boundary geometry, source hashes and latest review report.")

if __name__=="__main__":main()
