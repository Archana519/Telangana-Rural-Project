"""visual_audit_protocol.py - builds the Visual Grounding Table, a Google Earth KML and imagery crops for the priority-facility audit.

It fills every objective column from project files (model coordinates, offsets to detected footprints and to Google Open Buildings polygons, roof areas,
distance to the nearest TGRAC road, school-compound membership) and leaves the columns that need a human looking at high-resolution imagery EMPTY.
It does not look at Google Earth and does not claim any facility is visually confirmed.

Outputs (outputs/visual_audit/): visual_grounding_table.csv/.md, facilities_for_google_earth.kml, crops/<facility>_plain.png and _annotated.png,
protocol.md (decision rules). Lat/long are WGS84 (EPSG:4326) from the EPSG:32644 geometry.
usage: python src/validation/visual_audit_protocol.py --out outputs/visual_audit
"""
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import scenario_names as SN

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
IMG = V / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
CUES = {"School": "one or more large roofs (typically 200 m2 or more), open ground or playground beside the building, boundary wall or fence, road or lane access",
        "Healthcare": "a small single building (about 50-300 m2), signboard or compound gate, road or lane access",
        "Anganwadi": "a small single building (about 30-150 m2), often with a small yard, near the habitation",
        "Administrative (Gram Panchayat headquarters)": "a single building with a Gram Panchayat signboard (about 100-400 m2), usually near the settlement centre, with a yard or meeting space and road or lane access; the TGRAC point is a headquarters location, so check the building",
        "Government building": "NOT IN DATA: no government-building layer exists in the project; add coordinates to audit"}
RADIUS = 100


def crop(bounds, annotate, facility, bld, gob, out):
    xmin, ymin, xmax, ymax = bounds
    with rasterio.open(IMG) as s:
        w = from_bounds(xmin, ymin, xmax, ymax, s.transform)
        arr = s.read(window=w, boundless=True, fill_value=0).transpose(1, 2, 0)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(arr, extent=(xmin, xmax, ymin, ymax), origin="upper")
    if annotate:
        bld.boundary.plot(ax=ax, color="#ffea00", lw=1.2)
        gob.boundary.plot(ax=ax, color="#00e5ff", lw=1.2, ls="--")
        ax.scatter([facility.x], [facility.y], marker="+", s=300, c="#ff1744", linewidths=2.5)
        ax.text(0.02, 0.02, "red + = model coordinate; yellow = detected footprints; cyan dashed = Open Buildings v3", transform=ax.transAxes, fontsize=6, color="w", bbox=dict(fc="k", alpha=0.5))
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax); ax.set_axis_off()
    ax.plot([xmin + 10, xmin + 60], [ymin + 6, ymin + 6], color="w", lw=3); ax.text(xmin + 35, ymin + 10, "50 m", ha="center", color="w", fontsize=7)
    fig.savefig(out, dpi=150, bbox_inches="tight"); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "visual_audit"))
    a = ap.parse_args()
    out = Path(a.out)
    (out / "crops").mkdir(parents=True, exist_ok=True)
    fv = pd.read_csv(ROOT / "outputs" / "verification" / "facility_verification.csv", dtype={"facility_id": str})
    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")
    bld = gpd.read_file(V / "results" / "v8_instances" / "buildings_v8_full.gpkg", layer="buildings")
    gob = gpd.read_file(V / "reference" / "external" / "google_open_buildings_v3.gpkg")
    roads = gpd.read_file(V / "reference" / "tgrac_road_network.gpkg")
    ll = lambda g: gpd.GeoSeries([g], crs=32644).to_crs(4326).iloc[0]
    rows, kml = [], []
    for r in fac.itertuples():
        fid = str(r.facility_id)
        p = r.geometry
        v = fv[fv.facility_id == fid].iloc[0]
        nb = bld.assign(d=bld.geometry.distance(p)).sort_values("d").iloc[0]
        ng = gob.assign(d=gob.geometry.distance(p)).sort_values("d")
        leads = ng[ng.d <= 200].head(3)
        lead_txt = "; ".join("%.5f N %.5f E (%.0f m away, %.0f m2, conf %.2f)" % (ll(g.geometry.centroid).y, ll(g.geometry.centroid).x, p.distance(g.geometry), g.area_m2_utm, g.confidence) for g in leads.itertuples()) or "none within 200 m"
        road_d = float(roads.distance(p).min())
        pt = ll(p)
        rows.append({
            "facility_id": fid, "name": r.facility_name, "type": r.facility_type, "model_lat": round(pt.y, 6), "model_lon": round(pt.x, 6),
            "coordinate_source": r.source, "table_lat_lon_if_any": ("%s, %s" % (v.table_lat, v.table_lon)) if pd.notna(v.table_lat) else "",
            "nearest_detected_footprint_m": round(float(nb.d), 1), "nearest_footprint_class": nb.quality_class, "nearest_footprint_roof_m2": round(nb.geometry.area, 0),
            "nearest_open_buildings_m": v.nearest_open_buildings_m, "inside_school_compound": v.inside_school_compound if pd.notna(v.inside_school_compound) else "",
            "distance_to_nearest_TGRAC_road_m": round(road_d, 1), "agreement_verdict": v.verdict, "leads_to_inspect_open_buildings_within_200m": lead_txt,
            "expected_visual_cues": CUES.get(r.facility_type, ""),
            "OBS_feature_at_coordinate (fill)": "", "OBS_offset_to_matching_feature_m (fill)": "", "OBS_roof_size_m2_measured (fill)": "", "OBS_playground_or_open_ground_Y/N (fill)": "",
            "OBS_road_access_Y/N_and_side (fill)": "", "OBS_corrected_lat_lon_if_relocated (fill)": "", "OBS_imagery_date_shown_by_tool (fill)": "", "OBS_decision CONFIRM/RELOCATE/REJECT (fill)": "", "OBS_observer_and_date (fill)": ""})
        b = (p.x - RADIUS, p.y - RADIUS, p.x + RADIUS, p.y + RADIUS)
        near_b = bld[bld.geometry.intersects(gpd.GeoSeries([p.buffer(RADIUS * 1.5)], crs=32644).iloc[0])]
        near_g = gob[gob.geometry.intersects(gpd.GeoSeries([p.buffer(RADIUS * 1.5)], crs=32644).iloc[0])]
        crop(b, False, p, near_b, near_g, out / "crops" / ("%s_plain.png" % fid))
        crop(b, True, p, near_b, near_g, out / "crops" / ("%s_annotated.png" % fid))
        kml.append("<Placemark><name>%s</name><description>%s | %s | model coordinate; verdict %s; nearest detected footprint %.0f m</description><Point><coordinates>%.6f,%.6f,0</coordinates></Point></Placemark>" % (
            r.facility_name, r.facility_type, fid, v.verdict, nb.d, pt.x, pt.y))
        for i, g in enumerate(leads.itertuples(), 1):
            c = ll(g.geometry.centroid)
            kml.append("<Placemark><name>%s lead %d (Open Buildings)</name><description>%.0f m from the model coordinate; conf %.2f; %.0f m2</description><Point><coordinates>%.6f,%.6f,0</coordinates></Point></Placemark>" % (
                r.facility_name, i, p.distance(g.geometry), g.confidence, g.area_m2_utm, c.x, c.y))
    rows.append({"facility_id": "(none)", "name": "Government building", "type": "Government building", "expected_visual_cues": CUES["Government building"], "agreement_verdict": "NOT AUDITABLE"})
    T = pd.DataFrame(rows)
    T.to_csv(out / "visual_grounding_table.csv", index=False, encoding="utf-8-sig")
    obj = ["name", "type", "model_lat", "model_lon", "nearest_detected_footprint_m", "nearest_footprint_roof_m2", "nearest_open_buildings_m", "distance_to_nearest_TGRAC_road_m", "agreement_verdict", "leads_to_inspect_open_buildings_within_200m"]
    (out / "facilities_for_google_earth.kml").write_text('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Damarakunta priority facilities (model coordinates)</name>%s</Document></kml>' % "".join(kml), encoding="utf-8")
    proto = ["# Visual audit protocol for the priority facilities", "",
             "Purpose: check each model coordinate against high-resolution imagery by eye. Nothing in `visual_grounding_table.csv` marked `OBS_` has been filled; the measured columns come from project files.", "",
             "1. Open `facilities_for_google_earth.kml` in Google Earth Pro (File > Open). Each facility has a pin at the model coordinate and up to three lead pins at nearby Open Buildings polygons.",
             "2. Use the historical-imagery slider; record the imagery date shown. Prefer the most recent clear image. Note that the project's Esri mosaic has a recorded capture date of 29 Apr 2026 at one sampled point only (other parts may differ), so a mismatch in date can explain a difference.",
             "3. For each facility record in the `OBS_` columns: the feature at the pin, the distance to the feature that matches the expected cues (Google Earth ruler), roof size (ruler or polygon tool), open ground or playground beside it, and whether a road or lane reaches it (and on which side).",
             "4. Decide: **CONFIRM** if a matching building lies within 20 m of the model coordinate; **RELOCATE** if a matching building lies within 200 m (enter its lat/long); **REJECT** if none matches within 200 m. Use the plain crop first and the annotated crop second, so the detector's outlines do not bias the reading.",
             "5. Record observer and date. A visual match is evidence about position only; it does not show the building's use, ownership or legal access.", "",
             "The sub-centre has two TGRAC records about 236 m apart; check both. The anganwadi was excluded from the deliverables (inputs/EXCLUSIONS.md) and is not in this table. "
             "No government-building layer exists, so that row cannot be audited unless you supply coordinates.", "",
             "## Measured columns", "", T[["facility_id"] + obj].fillna("").to_markdown(index=False), ""]
    (out / "protocol.md").write_text("\n".join(proto), encoding="utf-8")
    (out / "visual_grounding_table.md").write_text("# Visual Grounding Table (measured columns; OBS_ columns are to be filled)\n\n" + T[["facility_id"] + obj + ["expected_visual_cues"]].fillna("").to_markdown(index=False) + "\n", encoding="utf-8")
    print(T[["facility_id", "name", "model_lat", "model_lon", "nearest_detected_footprint_m", "nearest_open_buildings_m", "distance_to_nearest_TGRAC_road_m", "agreement_verdict"]].to_string(index=False))


if __name__ == "__main__":
    main()
