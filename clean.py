#!/usr/bin/env python3
"""Regenerate the Beacon Central Florida demo data, with human-review gates.

Run: python clean.py --config pipeline_config.json
Inputs are immutable snapshots in raw/ and geography/. No output/ or extracted/
file is ever used as an input. Missing/ambiguous schemas block publication;
new fields/files are reported and quarantined, not silently auto-mapped.
"""

import argparse
import difflib
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import pandas as pd

DEFAULT_SENTINELS = {
    "": "blank",
    "(X)": "not_applicable",
    "N": "insufficient_sample_or_not_displayable",
    "-": "unavailable_or_not_computable",
    "**": "moe_not_computable",
    "***": "moe_for_open_ended_estimate",
    "N/A": "unavailable",
    "NA": "unavailable",
    "*": "suppressed",
    **{
        str(n): "acs_numeric_sentinel"
        for n in [
            -666666666,
            -999999999,
            -888888888,
            -555555555,
            -333333333,
            -222222222,
        ]
    },
}


def normalize_geoid(value, state=None, county=None):
    """Never use floats or infer a county from a tract number."""
    text = str(value).strip()
    if text.startswith("1400000US"):
        text = text[len("1400000US") :]
    if re.fullmatch(r"\d{10,11}\.0", text):
        text = text[:-2]
    if re.fullmatch(r"\d{10,11}", text):
        return text.zfill(11)
    if (
        state is not None
        and county is not None
        and re.fullmatch(r"\d{1,4}\.\d{1,2}", text)
    ):
        whole, fraction = text.split(".")
        if not re.fullmatch(r"\d{2}", str(state)) or not re.fullmatch(
            r"\d{3}", str(county)
        ):
            raise ValueError("State/county must be explicit 2/3-digit FIPS")
        return str(state) + str(county) + whole.zfill(4) + fraction.ljust(2, "0")
    raise ValueError(f"Ambiguous or malformed tract GEOID: {value!r}")


def normalize_unit(value, unit):
    if unit == "fraction":
        return value * 100
    if unit in ["percent", "percentage_points", "count", "USD", "thousands_USD"]:
        return value
    raise ValueError(f"Undeclared unit: {unit}")


def normalize_value(value, unit="count", sentinels=None):
    text = str(value).strip()
    codes = DEFAULT_SENTINELS if sentinels is None else sentinels
    if text in codes:
        return None, codes[text], None
    if re.fullmatch(r"[\d,]+\+", text):
        return None, "topcoded_lower_bound", float(text[:-1].replace(",", ""))
    if text.endswith("%") and unit not in ["percent", "percentage_points"]:
        raise ValueError("Percent symbol conflicts with declared source unit")
    try:
        number = float(text.replace(",", "").removesuffix("%"))
    except ValueError:
        return None, "unparsed_value", None
    return normalize_unit(number, unit), "", None


def deduplicate(frame, key="geoid"):
    exact = frame.drop_duplicates()
    if exact[key].duplicated().any():
        raise ValueError(f"Conflicting duplicate {key} values; source requires review")
    return exact, len(frame) - len(exact)


def schema_diff(expected, observed):
    missing = sorted(set(expected) - set(observed))
    new = sorted(set(observed) - set(expected))
    suggestions = {
        name: difflib.get_close_matches(name, new, n=2, cutoff=0.45) for name in missing
    }
    return {
        "missing": missing,
        "new": new,
        "possible_renames": {k: v for k, v in suggestions.items() if v},
    }


def read_csv_bytes(content, headers_only=False):
    for encoding in ["utf-8-sig", "cp1252"]:
        try:
            content.decode(
                encoding
            )  # Validate encoding beyond the header, without building the full table.
            return (
                pd.read_csv(
                    io.BytesIO(content),
                    dtype=str,
                    keep_default_na=False,
                    encoding=encoding,
                    nrows=0 if headers_only else None,
                ),
                encoding,
            )
        except UnicodeDecodeError:
            continue
    raise ValueError("Unsupported text encoding")


def add_review(config, source, category, detail, blocking=False):
    entry = dict(
        source=source, category=category, detail=detail, blocking=bool(blocking)
    )
    if entry not in config["_review"]:
        config["_review"].append(entry)


def read_checked(path, config, sheet=None):
    """Read approved columns only; unexpected columns stay in the review queue."""
    path = Path(path)
    if sheet:
        frame = pd.read_excel(path, sheet_name=sheet, dtype=str).fillna("")
        key = path.name + "!" + sheet
    else:
        frame, encoding = read_csv_bytes(path.read_bytes())
        if path.parent.parent.name == "extracted":
            key = path.parent.name + ".zip!" + path.name
        else:
            key = path.name
        config["_encodings"][key] = encoding
    expected = config["accepted_schemas"].get(key)
    if expected is None:
        raise ValueError(f"No approved schema for {key}")
    diff = schema_diff(expected, frame.columns)
    if diff["missing"]:
        raise ValueError(f"Missing/renamed columns in {key}: {diff}")
    frame = frame[expected].copy()
    for name in frame:
        if name.startswith("Unnamed:") and frame[name].str.strip().ne("").any():
            raise ValueError(
                f"Previously empty trailing column now has values: {key}/{name}"
            )
    for name in config["geoid"]["full_id_aliases"]:
        if name not in frame:
            continue
        for value in frame[name]:
            if value == "Geography":
                continue
            normalize_geoid(value)
        frame, removed = deduplicate(frame, key=name)
        if removed:
            add_review(config, key, "exact_duplicates_removed", str(removed))
        break
    return frame


def inspect_inputs(raw, geography, config):
    """Inspect whole CSVs so encoding/cell failures cannot hide after a header."""
    known = set(config["source_files"])
    ignored = set(config["ignored_derived_files"])
    for file in sorted(raw.rglob("*")):
        if file.is_file() and file.relative_to(raw).as_posix() not in known | ignored:
            add_review(
                config,
                file.relative_to(raw).as_posix(),
                "unknown_file",
                "Not ingested; approve an adapter/mapping before use",
            )
    observed = {}
    for name in config["source_files"]:
        file = raw / name
        if not file.exists():
            add_review(config, name, "missing_file", "Required source missing", True)
            continue
        if file.suffix == ".zip":
            with zipfile.ZipFile(file) as archive:
                expected_members = set(config["archive_members"][name])
                for member in archive.namelist():
                    if member not in expected_members:
                        add_review(
                            config,
                            name + "!" + member,
                            "unknown_archive_member",
                            "Not ingested",
                        )
                    if member.endswith(".csv"):
                        frame, encoding = read_csv_bytes(
                            archive.read(member), headers_only=True
                        )
                        observed[name + "!" + member] = list(frame.columns)
                        config["_encodings"][name + "!" + member] = encoding
                for member in expected_members - set(archive.namelist()):
                    add_review(
                        config,
                        name + "!" + member,
                        "missing_archive_member",
                        "Required member missing",
                        True,
                    )
                for key, digest in config["metadata_hashes"].items():
                    archive_name, member = key.split("!", 1)
                    if (
                        archive_name == name
                        and member in archive.namelist()
                        and hashlib.sha256(archive.read(member)).hexdigest() != digest
                    ):
                        add_review(
                            config,
                            key,
                            "metadata_changed",
                            "Column meaning/unit definitions may have changed; approve updated metadata",
                            True,
                        )
        elif file.suffix == ".csv":
            frame, encoding = read_csv_bytes(file.read_bytes(), headers_only=True)
            observed[name] = list(frame.columns)
            config["_encodings"][name] = encoding
        elif file.suffix == ".xlsx":
            with pd.ExcelFile(file) as book:
                for sheet in book.sheet_names:
                    observed[name + "!" + sheet] = list(
                        pd.read_excel(book, sheet_name=sheet, nrows=0).columns
                    )
    for key, expected in config["accepted_schemas"].items():
        if key not in observed:
            add_review(
                config, key, "missing_table", "Required table/sheet missing", True
            )
            continue
        diff = schema_diff(expected, observed[key])
        if diff["new"] or diff["missing"]:
            add_review(
                config, key, "schema_changed", json.dumps(diff), bool(diff["missing"])
            )
    for key in sorted(set(observed) - set(config["accepted_schemas"])):
        add_review(config, key, "unknown_table", "Not ingested; needs a source adapter")
    for name, expected in config["geometry_files"].items():
        file = geography / name
        if (
            not file.exists()
            or hashlib.sha256(file.read_bytes()).hexdigest() != expected
        ):
            add_review(
                config,
                name,
                "geography_changed_or_missing",
                "Approve boundaries/vintage before relabelling",
                True,
            )


def write_review(output, config):
    output.mkdir(parents=True, exist_ok=True)
    entries = sorted(
        config["_review"],
        key=lambda row: (row["source"], row["category"], row["detail"]),
    )
    report = {
        "blocking": any(row["blocking"] for row in entries),
        "items": entries,
        "encodings": config["_encodings"],
    }
    (output / "review_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True)
    )
    pd.DataFrame(entries, columns=["source", "category", "detail", "blocking"]).to_csv(
        output / "review_report.csv", index=False
    )


def finish_outputs(root, output, config):
    """Add explicit censored bounds, review tiers, coverage and manifests."""
    c = pd.read_parquet(output / "tract_clean.parquet")
    c.loc[c.mapping_confidence.eq("Low"), "review_tier"] = "Review required"
    c.to_csv(output / "tract_clean.csv", index=False)
    c.to_parquet(output / "tract_clean.parquet", index=False)
    q = pd.read_csv(output / "data_quality.csv", dtype={"geoid": str})
    q = q.drop(columns=["review_tier"]).merge(
        c[["geoid", "review_tier"]], on="geoid", validate="one_to_one"
    )
    q.to_csv(output / "data_quality.csv", index=False)
    events = pd.read_parquet(output / "cell_quality_flags.parquet")
    bounds = events[events.reason.eq("topcoded_lower_bound")].copy()
    bounds["lower_bound"] = pd.to_numeric(
        bounds.original_value.str.replace(",", "", regex=False).str.replace(
            "+", "", regex=False
        )
    )
    bounds["upper_bound"] = ""
    bounds["exact_value_known"] = False
    bounds.to_csv(output / "censored_value_bounds.csv", index=False)
    unknown = events[events.reason.eq("unparsed_value")]
    if len(unknown):
        add_review(
            config,
            "numeric_fields",
            "unparsed_values",
            f"{len(unknown)} cells null; inspect cell_quality_flags.csv",
        )
    data, _ = read_csv_bytes(
        (
            root / "extracted/grocery/SRAM General Tract Characteristics Data.csv"
        ).read_bytes()
    )
    data[data.State.eq("Florida")].groupby("County24").size().rename("tracts").to_csv(
        output / "usda_florida_county_coverage.csv"
    )
    manifest = [
        dict(
            path=str(file.relative_to(root)),
            bytes=file.stat().st_size,
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        )
        for folder in ["raw", "geography"]
        for file in sorted((root / folder).iterdir())
        if file.is_file()
    ]
    (output / "input_manifest.json").write_text(json.dumps(manifest, indent=2))
    # Audited curated aliases, including source-specific unit semantics.
    fields = []
    for name, source in config["curated_fields"].items():
        fields.append(
            dict(
                field=name,
                wide_source_column=source,
                unit=(
                    "percentage points"
                    if name.endswith("pp")
                    else (
                        "percent 0–100"
                        if name.endswith("pct")
                        else "see source metadata"
                    )
                ),
                vintage=(
                    "ACS 01/2020–12/2024"
                    if source.startswith(("s0", "s1", "s2", "b2"))
                    else "SRAM released 07/2026; mixed sources"
                ),
            )
        )
    pd.DataFrame(fields).to_csv(output / "curated_field_dictionary.csv", index=False)
    assert not c.geoid.duplicated().any()
    assert c.geoid.str.fullmatch(r"12\d{9}").all()
    assert c.poverty_pct.dropna().between(0, 100).all()
    assert c.snap_pct.dropna().between(0, 100).all()
    assert len(c) == len(pd.read_csv(output / "tract_neighborhoods.csv"))


def run(config_path, input_path=None, output_path=None):
    started = time.perf_counter()
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    config["_review"] = []
    config["_encodings"] = {}
    base = config_path.parent
    raw = Path(input_path).resolve() if input_path else base / config["input_root"]
    output = (
        Path(output_path).resolve() if output_path else base / config["output_root"]
    )
    geography = base / config["geometry_root"]
    try:
        inspect_inputs(raw, geography, config)
        if any(row["blocking"] for row in config["_review"]):
            write_review(output, config)
            print(
                "REVIEW REQUIRED: inputs changed; accepted data not replaced. See",
                output / "review_report.json",
                file=sys.stderr,
            )
            return 2
        from pipeline_data import build_tables, build_inventories
        from pipeline_geography import build_geography

        with tempfile.TemporaryDirectory(prefix="beacon-clean-") as temporary:
            root = Path(temporary)
            (root / "raw").symlink_to(raw, target_is_directory=True)
            (root / "geography").symlink_to(geography, target_is_directory=True)
            stage = root / "output"
            stage.mkdir()
            (root / "extracted").mkdir()
            for name in config["source_files"]:
                if name.endswith(".zip"):
                    destination = root / "extracted" / Path(name).stem
                    destination.mkdir()
                    with zipfile.ZipFile(raw / name) as archive:
                        for member in config["archive_members"][name]:
                            if Path(member).name != member:
                                raise ValueError(
                                    "Nested/unsafe archive member requires an explicit adapter"
                                )
                            (destination / member).write_bytes(archive.read(member))
            spine = build_geography(root, stage, config)
            summary = build_tables(root, stage, config)
            build_inventories(root, stage, config)
            finish_outputs(root, stage, config)
            accepted = pd.read_parquet(stage / "tract_clean.parquet")
            if set(accepted.geoid) != spine:
                raise ValueError(
                    "Source/boundary tract coverage differs; review geography instead of silently dropping rows"
                )
            add_review(
                config,
                "small_business_fl.pdf",
                "human_verification",
                "Deterministic PDF extraction completed; numeric rows still require visual review before operational use",
            )
            write_review(stage, config)
            (stage / "run_info.json").write_text(
                json.dumps(
                    {
                        "runtime_seconds": round(time.perf_counter() - started, 3),
                        "config_sha256": hashlib.sha256(
                            config_path.read_bytes()
                        ).hexdigest(),
                        "source_snapshot_month": "11/2026",
                        "output_rows": len(accepted),
                    },
                    indent=2,
                )
            )
            output.mkdir(parents=True, exist_ok=True)
            # All calculation/validation completes first. Move each completed file
            # on the destination filesystem; existing accepted files survive errors.
            for file in stage.iterdir():
                destination = output / file.name
                with tempfile.NamedTemporaryFile(dir=output, delete=False) as tmp:
                    temp = Path(tmp.name)
                shutil.copyfile(file, temp)
                temp.replace(destination)
        print(
            f"Built {summary['core_tracts']} tracts in {time.perf_counter()-started:.2f}s; review report: {output/'review_report.json'}"
        )
        return 0
    except Exception as error:
        add_review(config, "pipeline", "processing_error", str(error), True)
        write_review(output, config)
        print(
            f"REVIEW REQUIRED: {error}; existing accepted data retained",
            file=sys.stderr,
        )
        return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="pipeline_config.json")
    parser.add_argument("--input", help="Override raw source directory")
    parser.add_argument("--output", help="Override output directory")
    args = parser.parse_args()
    return run(args.config, args.input, args.output)


if __name__ == "__main__":
    sys.exit(main())
