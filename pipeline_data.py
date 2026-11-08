"""Deterministic source-table and indicator adapters for the Beacon demo.

No network calls, imputation or statistical model inference. Column semantics
come from approved Census/USDA metadata and pipeline_config.json.
"""

from pathlib import Path
import json
import re
import hashlib
import subprocess
import pandas as pd
import numpy as np
from clean import read_checked, normalize_geoid


def build_tables(P, O, cfg):
    pdf_text = subprocess.run(
        ["pdftotext", "-layout", str(P / "raw/small_business_fl.pdf"), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    from pathlib import Path
    import pandas as pd, numpy as np, re, json, hashlib, collections

    O.mkdir(exist_ok=True)
    COUNTIES = cfg["county_names"]
    SOURCES = {
        "population": "10w8GD8h8uUiZ0oAROgjY68S249ukD5GB",
        "poverty": "1uDti0UPJkGyMgwd34swYUIekprINb9Y7",
        "snap": "1hFRGr_jOE6huGqhrDknDXdKXlE8SVclN",
        "income": "1fuTva4EVsnRLPlRKNQ1GLEUih5ubYQow",
        "labor": "1TP5D10Kn8bB3Radixk8jYEZMY1skjc5o",
        "grocery": "1hXW0xzQs6pi4neh9AQr7m7roSLfmm2s2",
        "retailers": "1jAhYp9mp8Ywj2GhhXM-9Rec0PyaE3rgy",
        "mortgage": "1FsXM_sRakArOWBLmwsYfrBHpFlactfGP",
        "small_business_fl": "1pV5Bb3wFn826InKwytSAKwdLqCKQlXqJ",
    }

    def snake(s):
        if re.match(r"^[SB]\d", s):
            return s.lower()
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        return re.sub("[^a-z0-9]+", "_", s.lower()).strip("_")

    def geoid(v):
        return normalize_geoid(v)

    inventory = []
    columns = []
    events = []
    tables = {}
    wide = None
    sentinels = {
        "": "blank",
        "(X)": "not_applicable",
        "N": "insufficient_sample_or_not_displayable",
        "-": "unavailable_or_not_computable",
        "**": "moe_not_computable",
        "***": "moe_for_open_ended_estimate",
        "N/A": "unavailable",
        "NA": "unavailable",
        "*": "suppressed",
        "null": "missing",
        "-666666666": "acs_sentinel",
        "-999999999": "acs_sentinel",
        "-888888888": "acs_sentinel",
        "-555555555": "acs_sentinel",
        "-333333333": "acs_sentinel",
        "-222222222": "acs_sentinel",
    }
    sentinels.update(cfg["missing_codes"])

    def numeric_frame(d, source, key, skip, labels=None):
        values = {"geoid": key.to_numpy()}
        for column in d.columns:
            if column in skip or column.startswith("Unnamed:"):
                continue
            raw = d[column].astype(str).str.strip()
            label = labels.get(column, "") if labels else ""
            declared_percent = (
                "Percent" in label
                or "share" in column.lower()
                or column in ["PovertyRate", "PCTGQTRS"]
            ) and "dollars" not in label
            if raw.str.endswith("%").any() and not declared_percent:
                raise ValueError(
                    f"Unexpected percent syntax in {source}/{column}; review units"
                )
            missing = raw.isin(sentinels)
            top = raw.str.match(r"^[\d,]+\+$")
            bottom = raw.str.match(r"^[\d,]+-$")
            numeric = pd.to_numeric(
                raw.str.replace(",", "", regex=False)
                .str.replace("%", "", regex=False)
                .mask(missing | top | bottom),
                errors="coerce",
            )
            name = snake(column)
            values[name] = numeric.to_numpy()
            reason = (
                raw.map(sentinels)
                .fillna("unparsed_value")
                .mask(top, "topcoded_lower_bound")
                .mask(bottom, "bottomcoded_upper_bound")
            )
            flag = missing | top | bottom | numeric.isna()
            for index in d.index[flag]:
                events.append(
                    dict(
                        source=source,
                        geoid=key.loc[index],
                        column=name,
                        original_value=raw.loc[index],
                        reason=reason.loc[index],
                    )
                )
            label = labels.get(column, "") if labels else ""
            percent = (
                "Percent" in label
                or "share" in column.lower()
                or column in ["PovertyRate", "PCTGQTRS"]
            ) and "dollars" not in label
            unit = "percentage_points" if percent else "count_or_other_numeric"
            if "dollars" in label or "Income" in column:
                unit = "USD"
            columns.append(
                dict(
                    source=source,
                    original_column=column,
                    clean_column=name,
                    label=label,
                    unit=unit,
                    core_rows=len(d),
                    blank_cells=int(raw.eq("").sum()),
                    coded_missing_cells=int((missing & ~raw.eq("")).sum()),
                    topcoded_cells=int(top.sum()),
                    unparsed_cells=int(
                        (numeric.isna() & ~missing & ~top & ~bottom).sum()
                    ),
                    numeric_missing_cells=int(numeric.isna().sum()),
                    min=numeric.min(),
                    max=numeric.max(),
                    is_moe=column.endswith("M"),
                    moe_estimate_column=(
                        snake(column[:-1] + "E") if column.endswith("M") else ""
                    ),
                )
            )
        return pd.DataFrame(values, index=d.index)

    for kind in ["population", "poverty", "snap", "income", "labor"]:
        f = next((P / "extracted" / kind).glob("*Data.csv"))
        raw = read_checked(f, cfg)
        d = raw[~raw.GEO_ID.eq("Geography")].copy()
        d["geoid"] = d.GEO_ID.map(geoid)
        allrows = len(d)
        d = d[d.geoid.str[:5].isin(COUNTIES)].copy()
        labs = pd.read_csv(next((P / "extracted" / kind).glob("*Metadata.csv")))
        labels = dict(zip(labs["Column Name"], labs.Label))
        num = numeric_frame(
            d, kind, d.geoid, ["GEO_ID", "NAME", "geoid"], labels
        ).set_index("geoid")
        num = num.loc[:, ~num.columns.duplicated()]
        tables[kind] = num
        if wide is None:
            wide = pd.DataFrame(
                {"geoid": d.geoid, "tract_census_name": d.NAME}
            ).set_index("geoid")
        wide = wide.join(num, how="outer", validate="one_to_one")
        vals = d.drop(columns=["GEO_ID", "NAME", "geoid"])
        vc = vals.stack().value_counts()
        badcount = {
            str(k): int(v)
            for k, v in vc.items()
            if k in sentinels or str(k).endswith("+")
        }
        inventory.append(
            dict(
                source=kind,
                path=str(f.relative_to(P)),
                source_url="https://drive.google.com/file/d/" + SOURCES[kind] + "/view",
                geography="tract",
                vintage="ACS 01/2020–12/2024; boundaries 01/2024",
                encoding="UTF-8",
                rows_with_label_header=len(raw),
                actual_rows_all_regions=allrows,
                core_rows=len(d),
                columns=len(raw.columns),
                geoid_format="1400000US + 11-digit FIPS",
                duplicate_rows=int(d.duplicated().sum()),
                duplicate_geoids=int(d.geoid.duplicated().sum()),
                county_values="Lake County; Orange County; Osceola County; Seminole County",
                special_values=json.dumps(badcount),
                notes="Drop second descriptive header and all-empty trailing unnamed column. MOEs are 90% MOEs; percentages already 0–100.",
            )
        )
        # Inventory dictionary and notes too
        for aux in sorted((P / "extracted" / kind).iterdir()):
            if aux == f:
                continue
            inventory.append(
                dict(
                    source=kind,
                    path=str(aux.relative_to(P)),
                    source_url="https://drive.google.com/file/d/"
                    + SOURCES[kind]
                    + "/view",
                    geography="metadata / documentation",
                    vintage="ACS 01/2020–12/2024",
                    core_rows="",
                    actual_rows_all_regions=(
                        len(pd.read_csv(aux))
                        if aux.suffix == ".csv"
                        else len(aux.read_text().splitlines())
                    ),
                    columns=2 if aux.suffix == ".csv" else 1,
                    notes="Not observational rows; consumed as data dictionary / method notes.",
                )
            )
    for kind in [
        "General Tract Characteristics",
        "Straight Line Distance",
        "Driving Distance",
    ]:
        f = P / f"extracted/grocery/SRAM {kind} Data.csv"
        try:
            raw = read_checked(f, cfg)
            encoding = "UTF-8"
        except UnicodeDecodeError:
            raw = read_checked(f, cfg)
            encoding = "Windows-1252"
        raw["geoid"] = raw.CensusTract20.map(geoid)
        d = raw[raw.geoid.str[:5].isin(COUNTIES)].copy()
        source = {
            "General Tract Characteristics": "usda_general",
            "Straight Line Distance": "usda_sd",
            "Driving Distance": "usda_dd",
        }[kind]
        lookup = pd.read_csv(
            P / f"extracted/grocery/SRAM Variable Lookup {kind}.csv",
            encoding="utf-8-sig",
        )
        labels = dict(zip(lookup.Field, lookup.Description))
        num = numeric_frame(
            d,
            source,
            d.geoid,
            ["CensusTract20", "State", "County20", "County24", "geoid"],
            labels,
        ).set_index("geoid")
        if source == "usda_general":
            num = num.add_prefix("usda_")
        tables[source] = num
        wide = wide.join(num, how="outer", validate="one_to_one")
        inventory.append(
            dict(
                source=source,
                path=str(f.relative_to(P)),
                source_url="https://drive.google.com/file/d/"
                + SOURCES["grocery"]
                + "/view",
                geography="tract, nationwide",
                vintage="Released 07/2026; SNAP stores 06/2025; population 04/2020; income ACS 01/2020–12/2024",
                encoding=encoding,
                actual_rows_all_regions=len(raw),
                core_rows=len(d),
                columns=len(raw.columns) - 1,
                geoid_format=(
                    "10/11 digit numeric string"
                    if kind == "General Tract Characteristics"
                    else "11 digit string with leading zeros"
                ),
                duplicate_rows=int(d.duplicated().sum()),
                duplicate_geoids=int(d.geoid.duplicated().sum()),
                county_values="; ".join(sorted(d.County24.unique())),
                special_values=json.dumps({"blank": int(d.eq("").sum().sum())}),
                notes="All share columns are 0–100 percentages, not fractions. CensusTract20 is 2020 boundary code. County20 vs County24 retained in raw files; no core county-name differences. SRAM is access to SNAP-authorized stores, NOT supermarket-only FARA.",
            )
        )
        inventory.append(
            dict(
                source=source,
                path=str(
                    (
                        P / f"extracted/grocery/SRAM Variable Lookup {kind}.csv"
                    ).relative_to(P)
                ),
                source_url="https://drive.google.com/file/d/"
                + SOURCES["grocery"]
                + "/view",
                geography="metadata",
                vintage="07/2026",
                actual_rows_all_regions=len(lookup),
                columns=3,
                notes="Variable names, descriptions and distance definitions.",
            )
        )
    raw = read_checked(P / "raw/mortgage.xlsx", cfg, sheet="Data")
    raw["geoid"] = raw.census_tract.map(geoid)
    d = raw[raw.geoid.str[:5].isin(COUNTIES)].copy()
    num = (
        numeric_frame(
            d, "mortgage", d.geoid, ["census_tract", "county_fips", "area", "geoid"]
        )
        .set_index("geoid")
        .add_prefix("hmda_")
    )
    num["hmda_denial_rate_pct"] = num.hmda_denial_rate * 100
    tables["mortgage"] = num
    wide = wide.join(num, how="outer", validate="one_to_one")
    inventory.append(
        dict(
            source="mortgage",
            path="raw/mortgage.xlsx / Data",
            source_url="https://drive.google.com/file/d/"
            + SOURCES["mortgage"]
            + "/view",
            geography="tract; 7 FL counties plus NYC/SLC",
            vintage="Activity 01/2025–12/2025 (README)",
            actual_rows_all_regions=len(raw),
            core_rows=len(d),
            columns=7,
            geoid_format="11-digit FIPS; county_fips is 5 digits",
            duplicate_rows=int(d.duplicated().sum()),
            duplicate_geoids=int(d.geoid.duplicated().sum()),
            county_values="Brevard; Lake; Marion; Orange; Osceola; Seminole; Volusia",
            special_values="No missing core source cells",
            notes="denial_rate is 0–1 fraction. Core has 487/490 rows; absent tract is unknown, not zero loans. Source README says 538 ungeocoded applications excluded. Not used in food ranking.",
        )
    )
    # PDF records, deliberately segregated from food indicators.
    rows = []
    county = None
    income_group = None
    for line in pdf_text.splitlines():
        m = re.match(r"\s*([A-Z ]+) COUNTY \((\d{3})\), FL", line)
        if m:
            county = m.group(2)
        if line.strip() in [
            "Low Income",
            "Moderate Income",
            "Middle Income",
            "Upper Income",
            "Unknown Income",
        ]:
            income_group = line.strip()
        m = re.match(r"\s*(\d{4}\.\d{2})\s+(.+)", line)
        if m:
            fields = m.group(2).split()
            assert len(fields) == 8
            vals = [int(x.replace(",", "")) for x in fields]
            gid = "12" + county + m.group(1).replace(".", "")
            r = dict(geoid=gid, cra_income_group=income_group)
            for nm, v in zip(
                [
                    "loans_le100k_count",
                    "loans_le100k_amount_thousands_usd",
                    "loans_100k_250k_count",
                    "loans_100k_250k_amount_thousands_usd",
                    "loans_gt250k_count",
                    "loans_gt250k_amount_thousands_usd",
                    "loans_revenue_le1m_count",
                    "loans_revenue_le1m_amount_thousands_usd",
                ],
                vals,
            ):
                r["cra_" + nm] = v
            rows.append(r)
    cra = pd.DataFrame(rows)
    assert not cra.geoid.duplicated().any()
    cra.to_csv(O / "small_business_fl_extracted.csv", index=False)
    wide = wide.join(cra.set_index("geoid"), how="outer", validate="one_to_one")
    inventory.append(
        dict(
            source="small_business_fl",
            path="raw/small_business_fl.pdf",
            source_url="https://drive.google.com/file/d/"
            + SOURCES["small_business_fl"]
            + "/view",
            geography="tract under county/page/group headings",
            vintage="Activity 01/2024–12/2024",
            actual_rows_all_regions=489,
            core_rows=489,
            columns="8 numeric + tract + county context",
            geoid_format="0302.06 requires state 12 and county 069 context",
            duplicate_rows=0,
            duplicate_geoids=0,
            county_values="Lake; Orange; Osceola; Seminole",
            notes="23-page CRA report, not SBA lending. Eight columns; dollar amounts in thousands. 489 extracted records; one core tract absent. Group/subtotal/page rows excluded. Extraction not visually verified line by line. Not used in food ranking.",
        )
    )
    # Keep retailer geography at address/point level per Appendix B; do NOT infer tract counts.
    r = read_checked(P / "raw/retailers.csv", cfg)
    rr = r[
        (r.State.str.upper().eq("FL"))
        & r.County.str.strip().str.title().isin(COUNTIES.values())
    ].copy()
    rr.columns = [snake(c) for c in rr.columns]
    rr = rr.rename(
        columns={"additonal_address": "additional_address", "zip_code": "zip5"}
    )
    rr["county"] = rr.county.str.strip().str.title()
    rr["zip5"] = rr.zip5.str.zfill(5)
    rr["latitude"] = pd.to_numeric(rr.latitude, errors="coerce")
    rr["longitude"] = pd.to_numeric(rr.longitude, errors="coerce")
    rr["coordinate_valid"] = rr.latitude.between(-90, 90) & rr.longitude.between(
        -180, 180
    )
    rr["source_vintage"] = "Not stated in file"
    rr["retrieved"] = "11/2026"
    rr = rr.drop_duplicates()
    rr.to_csv(O / "snap_retailers_core.csv", index=False)
    inventory.append(
        dict(
            source="retailers",
            path="raw/retailers.csv",
            source_url="https://drive.google.com/file/d/"
            + SOURCES["retailers"]
            + "/view",
            geography="address/point; nationwide",
            vintage="Not stated in file; retrieved 11/2026",
            actual_rows_all_regions=len(r),
            core_rows=len(rr),
            columns=len(r.columns),
            geoid_format="No tract GEOID. Record_ID is not a geography.",
            duplicate_rows=int(r.duplicated().sum()),
            duplicate_geoids="not applicable",
            county_values="Uppercase county names in source",
            special_values=json.dumps(
                {k: int(v) for k, v in rr.eq("").sum().items() if v}
            ),
            notes="Renamed misspelled Additonal_Address. X/Y are projected coordinates, Latitude/Longitude are geographic. Retained points separately for manual lookup, not systematic per-tract count. SNAP authorization does not prove food quality, hours or stock.",
        )
    )
    inventory.append(
        dict(
            source="usda_readme",
            path="extracted/grocery/SRAM Read Me.txt",
            source_url="https://drive.google.com/file/d/"
            + SOURCES["grocery"]
            + "/view",
            geography="documentation",
            vintage="07/2026",
            notes="Confirms initial release 07/2026 and intentional blank cells.",
        )
    )
    wide = wide.sort_index()
    assert len(wide) == 490
    wide.to_csv(O / "tract_all_sources.csv", index_label="geoid")
    wide.to_parquet(O / "tract_all_sources.parquet")
    # Curated organizer-facing field names with explicit units and estimate/MOE pairing.
    mapping = cfg["curated_fields"]
    for k, v in mapping.items():
        assert v in wide.columns, (k, v)
    c = wide[list(mapping.values())].rename(columns={v: k for k, v in mapping.items()})
    c["county"] = c.index.str[:5].map(COUNTIES)
    c["county_fips"] = c.index.str[:5]
    c["geoid"] = c.index
    c["low_access_population_sd_pct_2020"] = (
        c.low_access_population_sd.div(c.population_base_2020.replace(0, np.nan)) * 100
    )
    c["low_access_population_dd_pct_2020"] = (
        c.low_access_population_dd.div(c.population_base_2020.replace(0, np.nan)) * 100
    )
    c["unemployment_pct"] = (
        c.unemployed.div(c.civilian_labor_force.replace(0, np.nan)) * 100
    )
    # Core completeness is only the three decision inputs, not structural N/A cells in hundreds of subgroup columns.
    core = ["poverty_pct", "snap_pct", "lila_sd_half_10"]
    c["core_completeness"] = c[core].notna().mean(axis=1)
    c["small_denominator_proxy"] = (c.poverty_universe < 500) | (c.households < 200)
    c["actual_sample_size"] = "Not provided"
    c["poverty_cv"] = c.poverty_moe_pp.div(1.645 * c.poverty_pct.replace(0, np.nan))
    c["snap_cv"] = c.snap_moe_pp.div(1.645 * c.snap_pct.replace(0, np.nan))
    c["high_poverty_moe"] = (c.poverty_cv > 0.30) | (c.poverty_moe_pp >= 10)
    c["high_snap_moe"] = (c.snap_cv > 0.30) | (c.snap_moe_pp >= 10)
    c["distance_definition_sensitive"] = (
        c.lila_sd_half_10.ne(c.lila_dd_half_10)
        & c.lila_sd_half_10.notna()
        & c.lila_dd_half_10.notna()
    )
    q = float(c.poverty_pct.quantile(cfg["screening"]["poverty_quantile"]))
    c["poverty_q75_pct"] = q
    c["poverty_lower90_pct"] = (c.poverty_pct - c.poverty_moe_pp).clip(0, 100)
    c["poverty_upper90_pct"] = (c.poverty_pct + c.poverty_moe_pp).clip(0, 100)
    c["poverty_above_q75_robust"] = c.poverty_lower90_pct > q
    c["high_poverty_lila_candidate"] = (c.poverty_pct >= q) & c.lila_sd_half_10.eq(1)
    c["missing_mortgage_source"] = ~c.index.isin(num.index)
    c["missing_cra_source"] = ~c.index.isin(cra.geoid)
    c["acs_period"] = "01/2020–12/2024"
    c["retailer_snapshot"] = "06/2025 (USDA SRAM)"
    c["usda_population_base"] = "04/2020"
    c["sram_release"] = "07/2026"
    c["tract_boundary_vintage"] = "01/2024"
    c["mixed_vintage_flag"] = True
    c["transportation_rate_available"] = False
    c["evidence_confidence"] = np.where(
        (c.core_completeness < 1)
        | c.small_denominator_proxy
        | c.group_quarters_flag.eq(1),
        "Low",
        np.where(
            c.high_poverty_moe | c.high_snap_moe | c.distance_definition_sensitive,
            "Medium",
            "High",
        ),
    )
    c["review_tier"] = np.where(
        c.evidence_confidence.eq("Low"), "Review required", "Review recommended"
    )
    n = pd.read_csv(
        O / "tract_neighborhoods.csv",
        dtype={"geoid": str, "tract_number": str, "place_geoid": str},
    )
    c = c.reset_index(drop=True).merge(
        n, on=["geoid", "county"], how="left", validate="one_to_one"
    )
    c["limitations"] = (
        "Screening signals, not measured unmet food need. No pantry capacity, service coverage, current hours, food insecurity prevalence or CFL reliable-transportation rate. Census places are not neighborhoods; review spatial labels. Population denominators are not sample sizes."
    )
    c.to_csv(O / "tract_clean.csv", index=False)
    c.to_parquet(O / "tract_clean.parquet", index=False)
    qualitycols = [
        "geoid",
        "county",
        "neighborhood_label",
        "mapping_confidence",
        "core_completeness",
        "small_denominator_proxy",
        "actual_sample_size",
        "high_poverty_moe",
        "high_snap_moe",
        "poverty_cv",
        "snap_cv",
        "poverty_lower90_pct",
        "poverty_upper90_pct",
        "poverty_above_q75_robust",
        "group_quarters_flag",
        "distance_definition_sensitive",
        "missing_mortgage_source",
        "missing_cra_source",
        "evidence_confidence",
        "review_tier",
        "acs_period",
        "retailer_snapshot",
        "usda_population_base",
        "sram_release",
        "mixed_vintage_flag",
        "transportation_rate_available",
        "limitations",
    ]
    c[qualitycols].to_csv(O / "data_quality.csv", index=False)
    e = pd.DataFrame(events)
    e.to_parquet(O / "cell_quality_flags.parquet", index=False)
    e.to_csv(O / "cell_quality_flags.csv", index=False)
    e.groupby(["source", "reason", "original_value"], dropna=False).size().rename(
        "cells"
    ).to_csv(O / "sentinel_summary.csv")
    pd.DataFrame(inventory).to_csv(O / "source_inventory.csv", index=False)
    pd.DataFrame(columns).to_csv(O / "column_inventory.csv", index=False)
    top = (
        c[c.high_poverty_lila_candidate]
        .sort_values(["poverty_pct", "low_income_low_access_sd"], ascending=False)
        .iloc[:10]
        .copy()
    )
    top["why_flagged"] = top.apply(
        lambda r: f"Poverty {r.poverty_pct:.1f}% ± {r.poverty_moe_pp:.1f} pp (90% MOE), above core Q75 {q:.3f}%; USDA straight-line LILA 0.5 urban/10 rural miles = 1; modeled low-income/low-access population {r.low_income_low_access_sd:,.0f}. SNAP {r.snap_pct:.1f}% ± {r.snap_moe_pp:.1f} pp (context only).",
        axis=1,
    )
    top["rank"] = range(1, len(top) + 1)
    top[
        [
            "rank",
            "geoid",
            "neighborhood_label",
            "mapping_confidence",
            "poverty_pct",
            "poverty_moe_pp",
            "snap_pct",
            "snap_moe_pp",
            "low_access_population_sd",
            "low_income_low_access_sd",
            "lila_dd_half_10",
            "distance_definition_sensitive",
            "poverty_above_q75_robust",
            "evidence_confidence",
            "why_flagged",
            "limitations",
        ]
    ].to_csv(O / "top_need_candidates.csv", index=False)
    coverage = []
    for k in tables:
        coverage.append(
            {
                "source": k,
                **{
                    nm: int(tables[k].index.str.startswith(fp).sum())
                    for fp, nm in COUNTIES.items()
                },
            }
        )
    pd.DataFrame(coverage).to_csv(O / "county_coverage.csv", index=False)
    summary = {
        "core_counties": COUNTIES,
        "core_tracts": len(c),
        "all_source_columns": len(wide.columns),
        "poverty_q75_pct": q,
        "lila_sd_count": int(c.lila_sd_half_10.eq(1).sum()),
        "lila_dd_count": int(c.lila_dd_half_10.eq(1).sum()),
        "high_poverty_lila_candidates": int(c.high_poverty_lila_candidate.sum()),
        "distance_sensitive_count": int(c.distance_definition_sensitive.sum()),
        "core_incomplete_count": int((c.core_completeness < 1).sum()),
        "small_denominator_proxy_count": int(c.small_denominator_proxy.sum()),
        "high_poverty_moe_count": int(c.high_poverty_moe.sum()),
        "high_snap_moe_count": int(c.high_snap_moe.sum()),
        "group_quarters_count": int(c.group_quarters_flag.eq(1).sum()),
        "retailers_core": len(rr),
        "mapping_confidence_counts": c.mapping_confidence.value_counts().to_dict(),
        "actual_orlando_neighborhood_assignments": int(
            c.official_neighborhood.notna().sum()
        ),
        "robust_high_poverty_lila_count": int(
            (c.high_poverty_lila_candidate & c.poverty_above_q75_robust).sum()
        ),
    }
    (O / "summary.json").write_text(json.dumps(summary, indent=2))
    manifest = [
        {
            "path": str(f.relative_to(P)),
            "bytes": f.stat().st_size,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        }
        for f in sorted((P / "raw").iterdir())
        if f.is_file()
    ]
    (O / "input_manifest.json").write_text(json.dumps(manifest, indent=2))
    return summary


def build_inventories(P, O, cfg):
    import pandas as pd, numpy as np, re, json
    from pathlib import Path

    C = cfg["county_names"]
    ids = {
        "population": "10w8GD8h8uUiZ0oAROgjY68S249ukD5GB",
        "poverty": "1uDti0UPJkGyMgwd34swYUIekprINb9Y7",
        "snap": "1hFRGr_jOE6huGqhrDknDXdKXlE8SVclN",
        "income": "1fuTva4EVsnRLPlRKNQ1GLEUih5ubYQow",
        "labor": "1TP5D10Kn8bB3Radixk8jYEZMY1skjc5o",
        "grocery": "1hXW0xzQs6pi4neh9AQr7m7roSLfmm2s2",
        "retailers": "1jAhYp9mp8Ywj2GhhXM-9Rec0PyaE3rgy",
        "mortgage": "1FsXM_sRakArOWBLmwsYfrBHpFlactfGP",
        "small_business_fl": "1pV5Bb3wFn826InKwytSAKwdLqCKQlXqJ",
    }
    S = {
        "": "blank",
        "(X)": "not_applicable",
        "N": "insufficient_sample_or_not_displayable",
        "-": "unavailable_or_not_computable",
        "**": "moe_not_computable",
        "***": "moe_for_open_ended_estimate",
        "N/A": "unavailable",
        "NA": "unavailable",
        "*": "suppressed",
        "-666666666": "acs_numeric_sentinel",
        "-999999999": "acs_numeric_sentinel",
    }

    def snake(c):
        if re.match(r"^[SB]\d", c):
            return c.lower()
        return re.sub(
            "[^a-z0-9]+", "_", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", c).lower()
        ).strip("_")

    S.update(cfg["missing_codes"])
    inv = []
    col = []
    events = []
    coverage = []
    for kind in [
        "population",
        "poverty",
        "snap",
        "income",
        "labor",
        "usda_general",
        "usda_sd",
        "usda_dd",
    ]:
        acs = kind in ids and kind != "grocery"
        grocery_kind = {
            "usda_general": "General Tract Characteristics",
            "usda_sd": "Straight Line Distance",
            "usda_dd": "Driving Distance",
        }.get(kind)
        f = (
            next((P / "extracted" / kind).glob("*Data.csv"))
            if acs
            else P / f"extracted/grocery/SRAM {grocery_kind} Data.csv"
        )
        enc = "utf-8-sig"
        try:
            raw = read_checked(f, cfg)
        except UnicodeDecodeError:
            enc = "cp1252"
            raw = read_checked(f, cfg)
        if acs:
            actual = raw[~raw.GEO_ID.eq("Geography")].copy()
            actual["geoid"] = actual.GEO_ID.map(normalize_geoid)
            meta = next((P / "extracted" / kind).glob("*Metadata.csv"))
            md = pd.read_csv(meta)
            labels = dict(zip(md["Column Name"], md.Label))
            skip = ["GEO_ID", "NAME", "geoid"]
            sourcekind = kind
        else:
            actual = raw.copy()
            actual["geoid"] = actual.CensusTract20.map(normalize_geoid)
            meta = P / f"extracted/grocery/SRAM Variable Lookup {grocery_kind}.csv"
            md = pd.read_csv(meta, encoding="utf-8-sig")
            labels = dict(zip(md.Field, md.Description))
            skip = ["CensusTract20", "State", "County20", "County24", "geoid"]
            sourcekind = "grocery"
        d = actual[actual.geoid.str[:5].isin(C)].copy()
        schema_key = (kind if acs else "grocery") + ".zip!" + f.name
        enc = cfg["_encodings"].get(schema_key, enc)
        county = {name: int(d.geoid.str.startswith(fp).sum()) for fp, name in C.items()}
        coverage.append(dict(source=kind, **county))
        for c in d.columns:
            if c in skip or c.startswith("Unnamed:"):
                continue
            s = d[c].str.strip()
            n = pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")
            flag = s.isin(S) | n.isna()
            label = labels.get(c, "")
            cn = snake(c)
            cn = ("usda_" + cn) if kind == "usda_general" else cn
            reason = s.map(S).fillna("unparsed_value")
            reason = reason.mask(s.str.match(r"^[\d,]+\+$"), "topcoded_lower_bound")
            ef = pd.DataFrame(
                {
                    "source": kind,
                    "geoid": d.geoid,
                    "column": cn,
                    "original_value": s,
                    "reason": reason,
                }
            )
            events.append(ef[flag])
            unit = (
                "percentage points / 0–100 percent"
                if (
                    (
                        "Percent" in label
                        or c.lower().endswith("share")
                        or c in ["PovertyRate", "PCTGQTRS"]
                    )
                    and "dollars" not in label
                )
                else "count or other"
            )
            unit = "USD" if "dollars" in label or c == "MedianFamilyIncome" else unit
            col.append(
                dict(
                    source=kind,
                    original_column=c,
                    clean_column=cn,
                    label=label,
                    unit=unit,
                    core_rows=len(d),
                    blank_cells=int(s.eq("").sum()),
                    coded_missing_cells=int((s.isin(S) & ~s.eq("")).sum()),
                    topcoded_cells=int(s.str.match(r"^[\d,]+\+$").sum()),
                    numeric_missing_cells=int(n.isna().sum()),
                    min=n.min(),
                    max=n.max(),
                    is_moe=bool(acs and c.endswith("M")),
                    estimate_column=(
                        c[:-1].lower() + "e" if acs and c.endswith("M") else ""
                    ),
                )
            )
        vals = d.drop(columns=skip + [c for c in d if c.startswith("Unnamed:")]).stack()
        vc = vals.value_counts()
        special = {
            str(k): int(v) for k, v in vc.items() if k in S or str(k).endswith("+")
        }
        inv.append(
            dict(
                source=kind,
                path=str(f.relative_to(P)),
                source_url="https://drive.google.com/file/d/"
                + ids[sourcekind]
                + "/view",
                geography="tract",
                actual_rows_all_regions=len(actual),
                core_rows=len(d),
                columns=len(raw.columns),
                encoding=enc,
                duplicate_rows=int(d.duplicated().sum()),
                duplicate_geoids=int(d.geoid.duplicated().sum()),
                vintage=(
                    "ACS 01/2020–12/2024; boundaries 01/2024"
                    if acs
                    else "Release 07/2026; retailers 06/2025; population 04/2020; ACS 01/2020–12/2024"
                ),
                geoid_format=(
                    "1400000US + 11 digits"
                    if acs
                    else "10 or 11 numeric digits; normalize to 11"
                ),
                county_counts=json.dumps(county),
                special_values=json.dumps(special),
                trailing_empty_column=bool(any(c.startswith("Unnamed:") for c in d)),
                second_label_header=acs,
                county_name_mismatches=(
                    0 if acs else int(d.County20.ne(d.County24).sum())
                ),
                notes=(
                    "No rate recomputation necessary; percentages already 0–100. Zero is not missing."
                    if acs
                    else "SRAM SNAP-authorized store access, not supermarket-only access."
                ),
            )
        )
        inv.append(
            dict(
                source=kind,
                path=str(meta.relative_to(P)),
                source_url="https://drive.google.com/file/d/"
                + ids[sourcekind]
                + "/view",
                geography="column metadata",
                actual_rows_all_regions=len(md),
                columns=len(md.columns),
                vintage="12/2024 ACS" if acs else "07/2026",
                notes="All column labels used in column_inventory.csv",
            )
        )
        if acs:
            note = next((P / "extracted" / kind).glob("*Notes.txt"))
            inv.append(
                dict(
                    source=kind,
                    path=str(note.relative_to(P)),
                    source_url="https://drive.google.com/file/d/" + ids[kind] + "/view",
                    geography="documentation",
                    actual_rows_all_regions=len(note.read_text().splitlines()),
                    columns=1,
                    vintage="12/2024 ACS",
                    notes="Includes 90% MOE interpretation and scope.",
                )
            )
    # Mortgage field dictionary and source coverage (the full 7-county footprint is preserved here).
    m = pd.read_excel(P / "raw/mortgage.xlsx", sheet_name="Data", dtype=str).fillna("")
    m["geoid"] = m.census_tract.str.zfill(11)
    mc = m[m.geoid.str[:5].isin(C)]
    coverage.append(
        dict(
            source="mortgage",
            **{name: int(mc.geoid.str.startswith(fp).sum()) for fp, name in C.items()},
        )
    )
    m.groupby("area").size().rename("tracts").to_csv(
        O / "mortgage_all_region_coverage.csv"
    )
    inv.append(
        dict(
            source="mortgage",
            path="raw/mortgage.xlsx / Data",
            source_url="https://drive.google.com/file/d/" + ids["mortgage"] + "/view",
            geography="tract",
            actual_rows_all_regions=len(m),
            core_rows=len(mc),
            columns=7,
            duplicate_rows=int(mc.duplicated().sum()),
            duplicate_geoids=int(mc.geoid.duplicated().sum()),
            vintage="Activity 01/2025–12/2025 per README",
            geoid_format="11-digit FIPS; county_fips 5-digit",
            county_counts=json.dumps(m.groupby("area").size().to_dict()),
            notes="7 FL counties: Brevard, Lake, Marion, Orange, Osceola, Seminole, Volusia. Denial rate is FRACTION 0–1. Converted separate hmda_denial_rate_pct to 0–100. Three missing core tracts are unknown, not zero. README reports 538 ungeocoded applications excluded. Not a food-need input.",
        )
    )
    inv.append(
        dict(
            source="mortgage",
            path="raw/mortgage.xlsx / README",
            geography="documentation",
            actual_rows_all_regions=len(
                pd.read_excel(P / "raw/mortgage.xlsx", sheet_name="README")
            ),
            columns=1,
            notes="Provenance and exclusions supplied by hackathon.",
        )
    )
    for c in [
        "mortgages_originated",
        "mortgage_denials",
        "total_applications",
        "denial_rate",
    ]:
        v = pd.to_numeric(mc[c])
        col.append(
            dict(
                source="mortgage",
                original_column=c,
                clean_column="hmda_" + c,
                label=c,
                unit="fraction 0–1" if c == "denial_rate" else "count",
                core_rows=len(mc),
                numeric_missing_cells=int(v.isna().sum()),
                min=v.min(),
                max=v.max(),
                is_moe=False,
            )
        )
    r = pd.read_csv(P / "raw/retailers.csv", dtype=str, keep_default_na=False)
    rc = r[r.State.eq("FL") & r.County.str.title().isin(C.values())]
    rr = pd.read_csv(O / "snap_retailers_core.csv", dtype=str, keep_default_na=False)
    inv.append(
        dict(
            source="retailers",
            path="raw/retailers.csv",
            source_url="https://drive.google.com/file/d/" + ids["retailers"] + "/view",
            geography="address/point (NOT tract)",
            actual_rows_all_regions=len(r),
            core_rows=len(rc),
            columns=17,
            duplicate_rows=int(rc.duplicated().sum()),
            duplicate_geoids="Not applicable",
            vintage="Not stated in source file; retrieved 11/2026",
            geoid_format="None; Record_ID is store identifier",
            county_counts=json.dumps(rc.County.value_counts().to_dict()),
            special_values=json.dumps(
                {k: int(v) for k, v in rc.eq("").sum().items() if v}
            ),
            notes=f'All county names uppercase; normalized title case. Duplicate Record_ID: {rc.Record_ID.duplicated().sum()}; invalid geographic coordinates: {rr.coordinate_valid.eq("False").sum()}. Misspelled Additonal_Address renamed. X/Y projected, Latitude/Longitude geographic. No systematic retailer-to-tract count per Appendix B.',
        )
    )
    for c in r.columns:
        col.append(
            dict(
                source="retailers",
                original_column=c,
                clean_column={
                    "Additonal_Address": "additional_address",
                    "Zip_Code": "zip5",
                }.get(c, snake(c)),
                label=c,
                unit=(
                    "geographic decimal degrees"
                    if c in ["Latitude", "Longitude"]
                    else (
                        "projected coordinate; not degrees"
                        if c in ["X", "Y"]
                        else "text identifier/address/category"
                    )
                ),
                core_rows=len(rc),
                blank_cells=int(rc[c].eq("").sum()),
                is_moe=False,
            )
        )
    cra = pd.read_csv(O / "small_business_fl_extracted.csv", dtype={"geoid": str})
    coverage.append(
        dict(
            source="small_business_fl",
            **{name: int(cra.geoid.str.startswith(fp).sum()) for fp, name in C.items()},
        )
    )
    inv.append(
        dict(
            source="small_business_fl",
            path="raw/small_business_fl.pdf",
            source_url="https://drive.google.com/file/d/"
            + ids["small_business_fl"]
            + "/view",
            geography="tract under county/page headings",
            actual_rows_all_regions=len(cra),
            core_rows=len(cra),
            columns="8 numeric + tract + county/income-group context",
            duplicate_rows=int(cra.duplicated().sum()),
            duplicate_geoids=int(cra.geoid.duplicated().sum()),
            vintage="Activity 01/2024–12/2024",
            geoid_format="0302.06 + county 069 + state 12 → 12069030206",
            county_counts=json.dumps(cra.geoid.str[:5].map(C).value_counts().to_dict()),
            notes="23-page CRA Small Business Loans report, NOT SBA loans. Eight numeric columns; dollar amounts in THOUSANDS. 489 tract records; absent one core tract not imputed. Subtotals excluded. Not used for food ranking. PDF numeric extraction not visually reviewed line by line.",
        )
    )
    for c in cra.columns:
        if c == "geoid":
            continue
        col.append(
            dict(
                source="small_business_fl",
                original_column=c,
                clean_column=c,
                label=c,
                unit=(
                    "thousands USD"
                    if "thousands" in c
                    else "count" if c.endswith("count") else "category"
                ),
                core_rows=len(cra),
                is_moe=False,
            )
        )
    inv.append(
        dict(
            source="grocery",
            path="extracted/grocery/SRAM Read Me.txt",
            geography="documentation",
            vintage="07/2026",
            notes="Initial release 07/2026; blanks intentionally mark unavailable/not-applicable.",
        )
    )
    e = pd.concat(events, ignore_index=True)
    e.to_csv(O / "cell_quality_flags.csv", index=False)
    e.to_parquet(O / "cell_quality_flags.parquet", index=False)
    e.groupby(["source", "reason", "original_value"], dropna=False).size().rename(
        "cells"
    ).to_csv(O / "sentinel_summary.csv")
    pd.DataFrame(inv).to_csv(O / "source_inventory.csv", index=False)
    pd.DataFrame(col).to_csv(O / "column_inventory.csv", index=False)
    pd.DataFrame(coverage).to_csv(O / "county_coverage.csv", index=False)
    quality = pd.read_csv(O / "data_quality.csv", dtype={"geoid": str})
    agg = (
        e.groupby(["geoid", "reason"])
        .size()
        .unstack(fill_value=0)
        .add_prefix("flagged_cells_")
        .reset_index()
    )
    quality = quality.merge(agg, on="geoid", how="left", validate="one_to_one")
    quality.to_csv(O / "data_quality.csv", index=False)
    return inv, col
