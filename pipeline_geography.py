"""Label tracts by explicit polygon overlap, never by a guessed neighborhood."""

import geopandas as gpd
import pandas as pd


def build_geography(root, output, config):
    geography = root / "geography"
    tracts = gpd.read_file(geography / "tracts.zip")
    counties = config["county_names"]
    tracts = (
        tracts[tracts.GEOID.str[:5].isin(counties)]
        .copy()
        .to_crs(config["spatial_labels"]["crs"])
    )
    tracts["tract_area_m2"] = tracts.area
    places = gpd.read_file(geography / "places.zip").to_crs(tracts.crs)
    overlap = gpd.overlay(
        tracts[["GEOID", "tract_area_m2", "geometry"]],
        places[["GEOID", "NAME", "NAMELSAD", "geometry"]].rename(
            columns={
                "GEOID": "place_geoid",
                "NAME": "place_name",
                "NAMELSAD": "place_type_name",
            }
        ),
        how="intersection",
        keep_geom_type=False,
    )
    overlap["overlap_area_m2"] = overlap.area
    overlap["tract_area_share"] = overlap.overlap_area_m2 / overlap.tract_area_m2
    overlap = overlap[overlap.tract_area_share > 0.000001].sort_values(
        ["GEOID", "tract_area_share"], ascending=[True, False]
    )
    overlap.drop(columns="geometry").rename(columns={"GEOID": "geoid"}).to_csv(
        output / "tract_place_overlaps.csv", index=False
    )
    rows = []
    high = config["spatial_labels"]["confidence_area_share"]["high"]
    medium = config["spatial_labels"]["confidence_area_share"]["medium"]
    for _, tract in tracts.iterrows():
        matches = overlap[overlap.GEOID.eq(tract.GEOID)]
        county = counties[tract.GEOID[:5]]
        number = f"{int(tract.TRACTCE)//100}.{int(tract.TRACTCE)%100:02d}"
        if len(matches):
            match = matches.iloc[0]
            share = match.tract_area_share
            confidence = (
                "High" if share >= high else "Medium" if share >= medium else "Low"
            )
            label = (
                f"{match.place_name} ({county} Co.)"
                if share >= medium
                else f"Mixed / unincorporated near {match.place_name} ({county} Co.)"
            )
            name = match.place_name
            identifier = match.place_geoid
            method = "Largest tract-area intersection with Census place/CDP (not a neighborhood identity)"
        else:
            confidence = "Low"
            share = 0.0
            name = ""
            identifier = ""
            label = f"Unincorporated {county} Co. — tract {number}"
            method = "No Census place/CDP overlap; no neighborhood inferred"
        rows.append(
            dict(
                geoid=tract.GEOID,
                tract_number=number,
                county=county,
                neighborhood_label=label,
                place_name=name,
                place_geoid=identifier,
                largest_place_area_share=share,
                mapping_confidence=confidence,
                mapping_method=method,
                boundary_vintage="01/2024",
                mapping_limitation="Area overlap, not residential population overlap. Census place/CDP is not a local neighborhood. Labels require community review.",
            )
        )
    labels = pd.DataFrame(rows).sort_values("geoid")
    neighborhoods = gpd.read_file(geography / "orlando_neighborhoods.geojson").to_crs(
        tracts.crs
    )
    intersections = gpd.overlay(
        tracts[["GEOID", "tract_area_m2", "geometry"]],
        neighborhoods,
        how="intersection",
        keep_geom_type=False,
    )
    intersections["tract_area_share"] = intersections.area / intersections.tract_area_m2
    intersections = intersections[
        intersections.tract_area_share > 0.000001
    ].sort_values(["GEOID", "tract_area_share"], ascending=[True, False])
    intersections.drop(columns="geometry").rename(columns={"GEOID": "geoid"}).to_csv(
        output / "tract_orlando_neighborhood_overlaps.csv", index=False
    )
    labels["official_neighborhood"] = ""
    labels["neighborhood_area_share"] = float("nan")
    labels["neighborhood_candidates"] = ""
    labels["mapping_source"] = (
        "Census TIGER/Line Florida tract and place/CDP boundaries"
    )
    labels["source_retrieved"] = "11/2026"
    for index, row in labels.iterrows():
        matches = intersections[intersections.GEOID.eq(row.geoid)]
        if not len(matches):
            continue
        match = matches.iloc[0]
        labels.loc[index, "neighborhood_candidates"] = "; ".join(
            f"{value.NeighborhoodName}: {value.tract_area_share:.1%} tract area"
            for _, value in matches.iterrows()
        )
        labels.loc[index, "neighborhood_area_share"] = match.tract_area_share
        if match.tract_area_share >= medium:
            labels.loc[index, "official_neighborhood"] = match.NeighborhoodName
            labels.loc[index, "neighborhood_label"] = (
                f"{match.NeighborhoodName} ({row.county} Co.)"
            )
            labels.loc[index, "mapping_confidence"] = (
                "High" if match.tract_area_share >= high else "Medium"
            )
            labels.loc[index, "mapping_method"] = (
                "Largest tract-area intersection with official Orlando neighborhood; at least 50% of tract area"
            )
            labels.loc[index, "mapping_source"] = (
                "City of Orlando Neighborhoods (125 polygons), with Census tract geometry"
            )
            labels.loc[index, "boundary_vintage"] = (
                "Tracts 01/2024; neighborhoods vintage not provided"
            )
    labels.to_csv(output / "tract_neighborhoods.csv", index=False)
    mapped = tracts.merge(
        labels[["geoid", "neighborhood_label"]], left_on="GEOID", right_on="geoid"
    )
    mapped[["geoid", "neighborhood_label", "geometry"]].to_crs(4326).to_file(
        output / "tracts.geojson", driver="GeoJSON"
    )
    return set(labels.geoid)
