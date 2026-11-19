"""Facility candidates for one village and their verification (the Damarakunta checks: inside the study area, a detected footprint within 20 m of the point,
and a sanity check against mis-geocoded records)."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
FOOT_TOL_M = 20.0                       # Damarakunta rule: a footprint within 20 m of the facility point supports it

SCHOOL = {"school", "elementary_school", "high_school", "middle_school", "private_school", "public_school", "preschool", "education", "college_university",
          "nursing_school", "language_school", "montessori_school"}
HEALTH = {"hospital", "health_care", "medical_center", "urgent_care_clinic", "community_health_center", "health_and_medical", "childrens_hospital"}
GOVERNMENT = {"government_office", "community_and_government", "city_hall", "local_and_state_government_offices", "town_hall"}


def kind_of(tax: str | None, name: str | None) -> str | None:
    t = tax.lower() if isinstance(tax, str) else ""
    n = name.lower() if isinstance(name, str) else ""
    if t in SCHOOL or "school" in t:
        return "school"
    if t in HEALTH or t.endswith("hospital"):
        return "health"
    if t in GOVERNMENT or "panchayat" in n or "municipal" in n:
        return "government"
    return None


def candidates(places: gpd.GeoDataFrame, cell, footprints: gpd.GeoDataFrame, exclusions: pd.DataFrame | None = None) -> pd.DataFrame:
    p = places.copy()
    p["facility_type"] = [kind_of(t, n) for t, n in zip(p.taxonomy_primary, p.name)]
    p = p[p.facility_type.notna()].copy()
    p["inside_window"] = p.geometry.within(cell)
    fp = footprints
    sidx = fp.sindex
    dist = []
    for g in p.geometry:
        near = list(sidx.query(g.buffer(200)))
        dist.append(float(fp.geometry.iloc[near].distance(g).min()) if near else float("inf"))
    p["dist_to_nearest_footprint_m"] = np.round(dist, 1)
    p["footprint_within_20m"] = p.dist_to_nearest_footprint_m <= FOOT_TOL_M
    ex = {} if exclusions is None else dict(zip(exclusions["id"], exclusions["reason"]))
    p["manual_exclusion"] = p["id"].map(ex)
    # duplicates: same normalised name within 150 m -> keep the record with the highest confidence
    norm = p["name"].fillna("").str.lower().str.replace(r"[^a-z0-9]+", "", regex=True)
    p["_n"] = norm
    p = p.sort_values("confidence", ascending=False)
    dup = []
    kept = []
    for i, r in p.iterrows():
        if r["_n"] and any(k["_n"] == r["_n"] and k.geometry.distance(r.geometry) < 150 for k in kept):
            dup.append(i)
        else:
            kept.append(r)
    p.loc[dup, "manual_exclusion"] = p.loc[dup, "manual_exclusion"].fillna("duplicate record (same name within 150 m, lower confidence)")

    def status(r):
        if not r.inside_window:
            return "OUTSIDE_WINDOW_NOT_USED"
        if isinstance(r.manual_exclusion, str):
            return "EXCLUDED_MISGEOCODED_OR_NOT_A_FACILITY"
        if not r.footprint_within_20m:
            return "NO_FOOTPRINT_WITHIN_20M_NOT_USED"
        return "VERIFIED_USED"
    p["status"] = p.apply(status, axis=1)
    wgs = p.to_crs(4326)
    p["lon"], p["lat"] = wgs.geometry.x.round(6), wgs.geometry.y.round(6)
    p["x_epsg32644"], p["y_epsg32644"] = p.geometry.x.round(1), p.geometry.y.round(1)
    return p
