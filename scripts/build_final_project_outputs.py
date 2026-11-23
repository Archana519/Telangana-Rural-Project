#!/usr/bin/env python
"""Assemble FINAL_PROJECT_OUTPUTS/: every map, facility-coordinate table and master comparison table for both study areas in one folder,
with an INDEX.md that lists every file and the key metrics (all read from the result files, nothing typed in).

    python scripts/build_final_project_outputs.py

Read-only on DELIVERABLES_DAMARAKUNTA_STAGE_B/ and DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/. Re-run it whenever the Adilabad five-map series
(scripts/make_adilabad_map_series.py) has been generated or results change; it rebuilds the folder from scratch.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
DK = REPO / "DELIVERABLES_DAMARAKUNTA_STAGE_B"
C3 = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE"
OPEN, SEG = C3 / "01_ADILABAD", C3 / "01_ADILABAD_SEGMENTATION"
OUT = REPO / "FINAL_PROJECT_OUTPUTS"
Image.MAX_IMAGE_PIXELS = None
CREDIT = "Basemap imagery: Esri, Maxar, Earthstar Geographics, and the GIS User Community."
MAPS = ["map1_imagery_boundary_roads", "map2_footprints_facilities_latlon", "map3_terrain_cost_landcover_slope", "map4_alternatives_vs_network", "map5_village_detail_shared_paths"]
files: list[tuple[str, str]] = []                   # (relative path, description)


def put(src: Path, dst_rel: str, desc: str):
    dst = OUT / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    files.append((dst_rel, desc))


def jpg(src: Path, dst_rel: str, desc: str, width=2000):
    dst = OUT / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    im.resize((width, int(im.height * width / im.width)), Image.LANCZOS).save(dst, quality=90)
    files.append((dst_rel, desc))


def fmt(x, d=1):
    return f"{x:,.{d}f}"


def seg_values(d: Path, area_text: str, open_run: bool = False) -> dict:
    """Master-table column for one village's footprint run (segmentation or open), read from its result files."""
    s = pd.read_csv(d / "routing_strategy_comparison.csv").set_index("strategy")
    sj = json.loads((d / "metrics_summary.json").read_text())
    ps = pd.read_csv(d / "penalty_sensitivity.csv") if (d / "penalty_sensitivity.csv").exists() else None          # absent when the run was --quick (main comparison only)
    og = pd.read_csv(d / "omission_summary.csv").set_index("group") if (d / "omission_summary.csv").exists() else None
    two, ind = s.loc["Two-stage shared plan"], s.loc["Independent least-cost routes"]
    pc = ps[ps.penalty_mode == "centre-in-footprint"].set_index("mu") if ps is not None else None
    n = sj["gap_targets"]
    seg = {
        "Study area (km2)": area_text,
        "Building source": (f"Overture open footprints ({sj['footprints_total']:,} polygons)" if open_run else f"StrongDINOv2Seg instances on 0.6 m Esri imagery ({sj['footprints_total']:,} polygons)"),
        "Footprints used for the penalty layer": f"{sj['footprints_used_for_penalty']:,} " + ("polygons (area >= 30 m2, confidence >= 0.7)" if open_run else "instances (area >= 30 m2)"),
        "House targets": f"{n} (road-gap rule: > 30 m from a road)",
        "Houses routed": f"{int(two.targets_routed)} of {int(two.targets_total)}",
        "Independent routes: total / unique (m)": f"{fmt(ind.total_len_m)} / {fmt(ind.unique_len_m)}",
        "Length-only control: unique (m)": fmt(s.loc['Length-only control', 'unique_len_m']),
        "Roads-only shared reference: unique (m)": fmt(s.loc['Roads-only shared reference', 'unique_len_m']),
        "Two-stage shared plan: unique (m)": fmt(two.unique_len_m),
        "Saving vs independent (%)": f"{two.saving_vs_independent_pct}",
        "Roads-only shared saving (%)": f"{s.loc['Roads-only shared reference', 'saving_vs_independent_pct']}",
        "Length-only control vs independent (%)": f"{s.loc['Length-only control', 'saving_vs_independent_pct']}",
        "Unique length per routed house (m)": f"{two.unique_len_m / two.targets_routed:.1f}",
        "Routes crossing other footprints (two-stage)": f"{int(two.routes_crossing_other_footprints)} of {int(two.targets_total)} ({100 * two.routes_crossing_other_footprints / two.targets_total:.0f}%)",
        "Length inside other footprints (m)": fmt(two.length_inside_other_footprints_m),
        "Facilities planned": f"{sj['facilities_verified']} verified (facility-phase length not reported for this run)",
    }
    if pc is not None:
        seg["mu = 1 -> 4: unique length change (%)"] = f"{pc.loc[4.0, 'length_change_vs_mu1_pct']:+.1f}"
        seg["mu = 1 -> 4: routes crossing (n)"] = f"{int(pc.loc[1.0, 'routes_crossing'])} -> {int(pc.loc[4.0, 'routes_crossing'])}"
    for g, lab in (("omit 10% (random)", "10% random omission: length change (%) / households unserved"), ("omit 20% (random)", "20% random omission: length change (%) / households unserved"),
                   ("omit smallest 10%", "smallest-10% omission: length change (%) / households unserved"), ("omit smallest 25%", "smallest-25% omission: length change (%) / households unserved")):
        if og is not None:
            seg[lab] = f"{og.loc[g, 'delta_len_pct']:+.1f} / {int(round(og.loc[g, 'unserved']))} of {n}"
    return seg


def sources_folder():
    """00_SOURCES_AND_PROVENANCE: where the owner records verified data-source links and proofs for the three study areas."""
    import hashlib
    S = OUT / "00_SOURCES_AND_PROVENANCE"
    for v in ("damarakunta", "adilabad_urban_updated", "aswaraopeta"):
        (S / "proofs" / v).mkdir(parents=True, exist_ok=True)
        (S / "proofs" / v / "README.md").write_text(f"# Proofs for {v}\n\nPut here (not committed unless licence allows): screenshots of the download pages, licence text, API responses, "
                                                    "e-mails or letters that confirm each source in `../../SOURCES_AND_PROOFS.md`. Name files `<source>_<date>.<ext>`.\n", encoding="utf-8")
    rows = [("Esri World Imagery (0.6 m)", "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer", "Esri Master Agreement / World Imagery terms; non-commercial academic use, credit required", "all three"),
            ("Overture Maps (buildings, transportation, places, divisions), release 2026-11-18.0 where used", "https://docs.overturemaps.org/", "ODbL (buildings/transportation) and CDLA-Permissive-2.0 (places, divisions); check per theme", "all three"),
            ("ESA WorldCover 10 m", "https://esa-worldcover.org/", "CC BY 4.0", "all three"),
            ("Copernicus DEM GLO-30", "https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model", "Copernicus licence", "all three"),
            ("OpenStreetMap / Overpass / Nominatim (boundary candidates)", "https://www.openstreetmap.org/copyright", "ODbL", "adilabad_urban_updated, aswaraopeta"),
            ("geoBoundaries ADM3 (2018 reference layer, frozen Adilabad run)", "https://www.geoboundaries.org/", "CC BY 4.0", "adilabad_urban (frozen)"),
            ("TGRAC village polygon (Damarakunta)", "", "OWNER TO FILL", "damarakunta"),
            ("PMGSY rate Rs 75 lakh/km (60-90)", "", "OWNER-SUPPLIED, UNVERIFIED: attach the circular or schedule of rates", "all three (illustrative only)")]
    md = ["# Data sources and provenance proofs (to be completed by the owner)", "",
          "Pre-filled with the sources the pipeline uses. Licences are as understood when written and are NOT verified: fill the last two columns after checking each page, and attach proofs under `proofs/<study area>/`.", "",
          "| source | URL | licence (to verify) | used for | verified by owner (date) | proof file |", "|---|---|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} |  |  |" for a, b, c, d in rows]
    md += ["", "## Study-area boundaries", "", "Polygon files and their provenance JSON are in each study area's `boundary/` folder (Adilabad updated, Aswaraopeta). Damarakunta's polygon is in `DELIVERABLES_DAMARAKUNTA_STAGE_B/` (read-only). "
           "Adilabad updated and Aswaraopeta are derived built-up settlement extents, not administrative boundaries. SHA-256 of the committed files is in `provenance_hashes.csv`.", ""]
    (S / "SOURCES_AND_PROOFS.md").write_text("\n".join(md), encoding="utf-8")
    cand = list((REPO / "configs/multivillage/villages").glob("*_boundary.*")) + [REPO / "inputs/economic_assumptions.json"] + list(C3.glob("*/run_log_full.json")) + list(C3.glob("*/study_area.csv"))
    pd.DataFrame([dict(file=str(p.relative_to(REPO)), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size) for p in sorted(cand) if p.exists()]).to_csv(S / "provenance_hashes.csv", index=False, lineterminator="\n")
    files.append(("00_SOURCES_AND_PROVENANCE/SOURCES_AND_PROOFS.md", "table of data sources and licences with blank verified-by-owner columns; attach proofs in proofs/<study area>/"))
    files.append(("00_SOURCES_AND_PROVENANCE/provenance_hashes.csv", "SHA-256 of boundary polygons, provenance files, assumptions and run logs"))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    # ------------------------------------------------------------------ 1 Damarakunta
    dm = DK / "02_FINAL_MAPS/final_maps_1_to_5"
    desc = {"map1": "satellite imagery, village boundary, existing TGRAC roads", "map2": "detected footprints and priority facilities with latitude/longitude callouts",
            "map3": "land cover, slope, cost surface C0, blocked cells", "map4": "Stage A alternatives versus the final shared network (village + settlement zoom)",
            "map5": "settlement-scale primary vs building-avoiding shared network, facilities labelled, footprint-crossing segments"}
    for m in MAPS:
        put(dm / f"{m}.png", f"01_DAMARAKUNTA_RURAL/maps/{m}.png", f"Damarakunta {m[:4]}: {desc[m[:4]]} (unchanged Stage B file)")
    put(DK / "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION/facility_verification.csv", "01_DAMARAKUNTA_RURAL/facility_tables/facility_verification.csv", "Damarakunta facility coordinates (lat/lon) and verification verdicts")
    put(DK / "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION/excluded_facilities.csv", "01_DAMARAKUNTA_RURAL/facility_tables/excluded_facilities.csv", "Damarakunta facilities excluded from planning (anganwadi)")
    put(DK / "03_RESULTS_TABLES/PRIMARY_RUN_S2_fac_C0_s25_final_x4/facility_status.csv", "01_DAMARAKUNTA_RURAL/facility_tables/facility_routing_status.csv", "Damarakunta facility routing status (x, y in EPSG:32644; route length, cost)")
    ct = DK / "03_RESULTS_TABLES/COMPARISON_TABLES"
    for n, d in (("table1_length_reduction.csv", "routing strategies: length and saving, x4 primary and x1 control"), ("table4_c1_sensitivity.csv", "segmentation (omission/addition) sensitivity"),
                 ("table6_obstacle_avoidance.csv", "building-crossing / obstacle-avoidance comparison"), ("building_crossings_summary.csv", "route crossings of other buildings")):
        put(ct / n, f"01_DAMARAKUNTA_RURAL/tables/{n}", f"Damarakunta Stage B: {d}")
    put(ct / "comparison_report.md", "01_DAMARAKUNTA_RURAL/tables/comparison_report.md", "Damarakunta Stage B comparison report")

    # ------------------------------------------------------------------ 2 Adilabad
    series = SEG / "final_maps_1_to_5"
    have_series = all((series / f"{m}.png").exists() for m in MAPS)
    if have_series:
        for m in MAPS:
            put(series / f"{m}.png", f"02_ADILABAD_URBAN/maps/{m}.png", f"Adilabad {m[:4]} (StrongDINOv2Seg footprints; Esri imagery where shown; credit: {CREDIT})")
        if (series / "adilabad_fac_route_2panel.png").exists():
            put(series / "adilabad_fac_route_2panel.png", "02_ADILABAD_URBAN/maps/adilabad_fac_route_2panel.png", "compact 2-panel figure: verified facilities and final shared network (central zone)")
    fg = SEG / "figures"
    for n, d in (("sat_map1_a", "study window on Esri imagery: boundary, roads, detected footprints by quality class, verified facilities"), ("sat_map1_b", "central zoom of the same"),
                 ("sat_map2_independent_window", "independent least-cost routes, full window"), ("sat_map2_two_stage_window", "two-stage shared network, full window"),
                 ("sat_map2_independent_zoom", "independent routes, densest cluster"), ("sat_map2_two_stage_zoom", "two-stage network, densest cluster")):
        jpg(fg / f"{n}.png", f"02_ADILABAD_URBAN/satellite_overlays/{n}.jpg", f"Adilabad {d} (JPEG copy, 2000 px wide; full-resolution PNG in 01_ADILABAD_SEGMENTATION/figures; {CREDIT})")
    put(fg / "sat_legend.png", "02_ADILABAD_URBAN/satellite_overlays/sat_legend.png", "legend strip for the satellite overlays")
    for n, d in (("map1_study_area.png", "open-footprint study area (WorldCover background)"), ("map2_network_comparison.png", "open-footprint route comparison"), ("fig3_sensitivity.png", "open-footprint sensitivity")):
        put(OPEN / "figures" / n, f"02_ADILABAD_URBAN/open_footprint_check/{n}", f"Adilabad open Overture footprints: {d}")
    put(SEG / "verified_facilities.csv", "02_ADILABAD_URBAN/facility_tables/verified_facilities_segmentation_run.csv", "Adilabad Overture place candidates with status (lat, lon, x, y) - segmentation run")
    put(OPEN / "verified_facilities.csv", "02_ADILABAD_URBAN/facility_tables/verified_facilities_open_footprint_run.csv", "same, open-footprint run")
    for n, d in (("routing_strategy_comparison.csv", "five routing strategies"), ("penalty_sensitivity.csv", "footprint-penalty sweep"), ("omission_summary.csv", "omission scenarios (summary)"),
                 ("omission_runs.csv", "omission scenarios (every run)"), ("target_definition_sensitivity.csv", "road-gap threshold sweep"), ("building_extraction_summary.csv", "instances by quality class"),
                 ("metrics_summary.json", "headline metrics"), ("run_log_full.json", "inference run log (mosaic, tiles, checkpoint SHA-256)"), ("comparison_open_vs_segmentation.csv", "open vs segmentation")):
        put(SEG / n, f"02_ADILABAD_URBAN/tables_segmentation_run/{n}", f"Adilabad segmentation run: {d}")
    for n, d in (("routing_strategy_comparison.csv", "five routing strategies"), ("penalty_sensitivity.csv", "footprint-penalty sweep"), ("omission_summary.csv", "omission scenarios"),
                 ("target_definition_sensitivity.csv", "road-gap threshold sweep"), ("building_extraction_summary.csv", "Overture footprints by quality class"), ("comparison_vs_damarakunta.csv", "open-footprint run vs Damarakunta")):
        put(OPEN / n, f"02_ADILABAD_URBAN/tables_open_footprint_run/{n}", f"Adilabad open-footprint run: {d}")

    # ------------------------------------------------------------------ 3 facility coordinate summary
    rows = []
    for tag, p in (("segmentation run", SEG / "verified_facilities.csv"), ("open-footprint run", OPEN / "verified_facilities.csv")):
        f = pd.read_csv(p)
        v = f[f.status == "VERIFIED_USED"].copy()
        key = v.groupby(["lon", "lat"]).name.transform("size")
        for _, r in v.iterrows():
            rows.append(dict(settlement="Adilabad Urban", run=tag, name=r["name"], facility_type=r.facility_type, taxonomy=r.taxonomy_primary, lat=r.lat, lon=r.lon,
                             records_at_same_coordinate=int(key[r.name] if False else ((v.lon == r.lon) & (v.lat == r.lat)).sum()), dist_to_nearest_footprint_m=r.dist_to_nearest_footprint_m))
    fv = pd.read_csv(DK / "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION/facility_verification.csv")
    for _, r in fv.iterrows():
        rows.append(dict(settlement="Damarakunta", run="Stage B", name=r["name"], facility_type=r["type"], taxonomy="", lat=r.lat, lon=r.lon, records_at_same_coordinate=1,
                         dist_to_nearest_footprint_m=r.dist_to_nearest_footprint_m))
    fac = pd.DataFrame(rows)
    (OUT / "03_COMPARISON").mkdir()
    fac.to_csv(OUT / "03_COMPARISON/facility_coordinates_all_settlements.csv", index=False, lineterminator="\n")
    files.append(("03_COMPARISON/facility_coordinates_all_settlements.csv", "verified facilities of both study areas with latitude/longitude (Adilabad: both runs; column records_at_same_coordinate flags generic shared points)"))

    # ------------------------------------------------------------------ 4 master comparison table
    cmp_ = pd.read_csv(OPEN / "comparison_vs_damarakunta.csv").set_index("metric")
    seg = seg_values(SEG, "17.75 (geoBoundaries ADM3 'Adilabad Urban')")
    sj = json.loads((SEG / "metrics_summary.json").read_text())
    n = sj["gap_targets"]
    cols = list(cmp_.columns)
    master = pd.DataFrame([dict(metric=m, damarakunta_rural=cmp_.loc[m, cols[0]] if m in cmp_.index else "n/a", adilabad_urban_segmentation=seg.get(m, "n/a"),
                                adilabad_urban_open_footprints=cmp_.loc[m, cols[1]] if m in cmp_.index else "n/a") for m in dict.fromkeys(list(cmp_.index) + list(seg))])
    master.to_csv(OUT / "03_COMPARISON/master_comparison_three_settings.csv", index=False, lineterminator="\n")
    files.append(("03_COMPARISON/master_comparison_three_settings.csv", "Damarakunta vs Adilabad (StrongDINOv2Seg footprints) vs Adilabad (open Overture footprints): every shared metric"))
    put(OPEN / "comparison_vs_damarakunta.md", "03_COMPARISON/comparison_vs_damarakunta_open_footprints.md", "narrative comparison, open-footprint run")

    # ------------------------------------------------------------------ 5 further settlements (updated Adilabad boundary, Aswaraopeta), each once its results are committed
    VILLAGES = [dict(id="adilabad_urban_updated", seg=C3 / "01_ADILABAD_UPDATED_SEGMENTATION", open=C3 / "01_ADILABAD_UPDATED", bundle="02_ADILABAD_URBAN_UPDATED", label="Adilabad Urban (Adilabad Town), updated boundary",
                      col="adilabad_updated", prov="adilabad_urban_updated_boundary", slug="adilabad_updated"),
                 dict(id="aswaraopeta", seg=C3 / "02_ASWARAOPETA_SEGMENTATION", open=C3 / "02_ASWARAOPETA", bundle="03_ASWARAOPETA_SEMI_URBAN", label="Aswaraopeta (Ashwaraopet town)", col="aswaraopeta",
                      prov="aswaraopeta_boundary", slug="aswaraopeta")]
    asw_lines = []
    for V in VILLAGES:
        have_seg, have_open = (V["seg"] / "metrics_summary.json").exists(), (V["open"] / "metrics_summary.json").exists()
        if not (have_seg or have_open):
            continue
        B = V["bundle"]
        pf = REPO / "configs/multivillage/villages" / (V["prov"] + ".provenance.json")
        prov = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
        name = prov.get("study_area_name", V["label"])
        area_text = f"{prov['area_km2']:.2f} ({prov.get('boundary_type', 'polygon file')})" if "area_km2" in prov else "polygon file"
        seg_v = seg_values(V["seg"], area_text) if have_seg else None
        open_v = seg_values(V["open"], area_text, open_run=True) if have_open else None
        for col_name, vals in ((f"{V['col']}_segmentation", seg_v), (f"{V['col']}_open_footprints", open_v)):
            if vals is None:
                continue
            master[col_name] = master.metric.map(vals).fillna("n/a")
            extra = [m for m in vals if m not in set(master.metric)]
            if extra:
                master = pd.concat([master, pd.DataFrame([{"metric": m, col_name: vals[m]} for m in extra])], ignore_index=True).fillna("n/a")
        master.to_csv(OUT / "03_COMPARISON/master_comparison_three_settings.csv", index=False, lineterminator="\n")
        for tag, d_, on in (("segmentation", V["seg"], have_seg), ("open_footprint", V["open"], have_open)):
            if not on:
                continue
            ser = d_ / "final_maps_1_to_5"
            for m in MAPS:
                if (ser / f"{m}.png").exists():
                    put(ser / f"{m}.png", f"{B}/maps/{m}.png", f"{name} {m[:4]} ({tag} footprints; Esri imagery where shown; credit: {CREDIT})")
            for extra_png in (ser.glob("*_fac_route_2panel.png") if ser.exists() else []):
                put(extra_png, f"{B}/maps/{extra_png.name}", "compact 2-panel figure: verified facilities and final shared network")
            for n_ in ("map_facility_key.csv", "network_length_cost_summary.csv"):
                if (ser / n_).exists():
                    put(ser / n_, f"{B}/maps/{n_}", "facility label key (F<id>, name, lat/lon) / route length and illustrative PMGSY cost table for the maps")
            for n_ in ("sat_map1_a", "sat_map1_b", "sat_map2_independent_window", "sat_map2_two_stage_window", "sat_map2_independent_zoom", "sat_map2_two_stage_zoom"):
                if (d_ / "figures" / f"{n_}.png").exists():
                    jpg(d_ / "figures" / f"{n_}.png", f"{B}/satellite_overlays/{n_}.jpg", f"{name} satellite overlay {n_} (JPEG copy; {CREDIT})")
            for n_ in ("routing_strategy_comparison.csv", "penalty_sensitivity.csv", "omission_summary.csv", "omission_runs.csv", "target_definition_sensitivity.csv", "building_extraction_summary.csv", "metrics_summary.json",
                       "study_area.csv", "run_log_full.json", "verified_facilities.csv", "comparison_open_vs_segmentation.csv", "RUN_STATUS.md",
                       "map_facility_key.csv", "network_length_cost_summary.csv"):
                if (d_ / n_).exists():
                    put(d_ / n_, f"{B}/tables_{tag}_run/{n_}", f"{name}, {tag} run: {n_}")
        for n_ in (pf, pf.with_name(V["prov"] + ".geojson")):
            if n_.exists():
                put(n_, f"{B}/boundary/{n_.name}", "the study-area polygon and its provenance (derived built-up settlement extent; covered mandals and localities)")
        fsrc = V["seg"] if have_seg else V["open"]
        fv_ = pd.read_csv(fsrc / "verified_facilities.csv")
        v_ = fv_[fv_.status == "VERIFIED_USED"]
        add = [dict(settlement=name, run=("segmentation run" if have_seg else "open-footprint run"), name=r["name"], facility_type=r.facility_type, taxonomy=r.taxonomy_primary, lat=r.lat, lon=r.lon,
                    records_at_same_coordinate=int(((v_.lon == r.lon) & (v_.lat == r.lat)).sum()), dist_to_nearest_footprint_m=r.dist_to_nearest_footprint_m) for _, r in v_.iterrows()]
        fac = pd.concat([fac, pd.DataFrame(add)], ignore_index=True)
        fac.to_csv(OUT / "03_COMPARISON/facility_coordinates_all_settlements.csv", index=False, lineterminator="\n")
        sa = (seg_v or open_v)
        main_d = json.loads(((V["seg"] if have_seg else V["open"]) / "metrics_summary.json").read_text())
        q_ = main_d["quality_classes"]
        cov = prov.get("covers", {})
        asw_lines += ["", f"## {name}", "",
                      f"**Study area:** {name}; {prov.get('boundary_type', '')}; {prov.get('area_km2', '?')} km². Mandals covered (2018 layer): "
                      + ", ".join(f"{m['mandal']} {m['area_km2']} km² ({m['share_of_polygon_pct']}%)" for m in cov.get("mandals_2018", [])) + ". Localities inside: " + ", ".join(cov.get("localities", [])) + ".",
                      "", f"Footprints: {main_d['footprints_total']:,} ({', '.join(f'{k} {v}' for k, v in q_.items())}); {main_d['gap_targets']} road-gap targets; {main_d['facilities_verified']} verified facilities. "
                      f"Run(s): {'segmentation ' if have_seg else ''}{'open-footprint' if have_open else ''}.", "",
                      "| metric | segmentation | open footprints |", "|---|---|---|"]
        for m in ("Independent routes: total / unique (m)", "Two-stage shared plan: unique (m)", "Saving vs independent (%)", "Roads-only shared saving (%)", "Routes crossing other footprints (two-stage)",
                  "Length inside other footprints (m)", "mu = 1 -> 4: unique length change (%)", "10% random omission: length change (%) / households unserved"):
            asw_lines.append(f"| {m} | {(seg_v or {}).get(m, 'n/a')} | {(open_v or {}).get(m, 'n/a')} |")

    sources_folder()
    # ------------------------------------------------------------------ INDEX.md
    q = sj["quality_classes"]
    lines = ["# FINAL_PROJECT_OUTPUTS: maps, facility coordinates and comparison tables for both study areas", "",
             "Generated by `python scripts/build_final_project_outputs.py` from the result files in `DELIVERABLES_DAMARAKUNTA_STAGE_B/` (read-only) and "
             "`DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/`. All numbers below are read from those files. Costs are ordinal planning units, not rupees; routes are planning alternatives, not engineered roads.", "",
             "## Study areas", "",
             "| | Damarakunta (rural) | Adilabad Urban (urban / peri-urban) |", "|---|---|---|",
             "| Boundary | TGRAC village polygon, 18.47 km² | geoBoundaries ADM3 mandal polygon, 17.75 km² |",
             "| Imagery | Esri World Imagery, 0.6 m | Esri World Imagery, 0.6 m, mosaic 7,248 × 9,590 px, 391 inference tiles |",
             f"| Footprints | StrongDINOv2Seg + OpenCV: 278 polygons, 165 inside the boundary, 163 targets | StrongDINOv2Seg + OpenCV: {sj['footprints_total']:,} instances ({q.get('PLAUSIBLE', 0):,} plausible, {q.get('REVIEW', 0):,} review, "
             f"{q.get('UNRESOLVED_MERGE', 0):,} unresolved merge, {q.get('SMALL_EXCLUDED', 0)} below 30 m²); open Overture check: 24,924 polygons |",
             f"| Targets | 163 houses + 5 facilities | {n} road-gap targets (segmentation run), 874 (open footprints); {sj['facilities_verified']} verified facilities (open run: 71) |", "",
             "## Headline metrics (two-stage shared plan, footprint penalty μ = 4)", "", "| metric | Damarakunta | Adilabad segmentation | Adilabad open footprints |", "|---|---|---|---|"]
    for m in ("Independent routes: total / unique (m)", "Two-stage shared plan: unique (m)", "Saving vs independent (%)", "Roads-only shared saving (%)", "Routes crossing other footprints (two-stage)",
              "Length inside other footprints (m)", "mu = 1 -> 4: unique length change (%)", "10% random omission: length change (%) / households unserved"):
        r = master[master.metric == m].iloc[0]
        lines.append(f"| {m} | {r.damarakunta_rural} | {r.adilabad_urban_segmentation} | {r.adilabad_urban_open_footprints} |")
    lines += asw_lines
    lines += ["", "Full table: `03_COMPARISON/master_comparison_three_settings.csv`.", "", "## Files", "", "| file | content |", "|---|---|"]
    lines += [f"| `{p}` | {d} |" for p, d in sorted(files)]
    lines += ["", "## Notes you should read before using these files", ""]
    if not have_series:
        lines += ["* **The five-map Adilabad series (map1 to map5) is not in this folder yet.** It needs the Esri mosaic, the StrongDINOv2Seg footprints and the route state, which exist only on the machine that ran "
                  "`scripts/run_adilabad_end_to_end.py` (they are git-ignored). Generate it there with `python scripts\\make_adilabad_map_series.py`, then re-run `python scripts/build_final_project_outputs.py`; "
                  "the five PNGs and the compact 2-panel figure are picked up automatically. Until then `02_ADILABAD_URBAN/satellite_overlays/` holds the satellite maps of the segmentation run.", ""]
    dupes = fac[(fac.settlement == "Adilabad Urban") & (fac.run == "segmentation run") & (fac.records_at_same_coordinate > 1)]
    lines += [f"* **Facility coordinates (Adilabad).** {len(dupes)} of the {int(((fac.settlement == 'Adilabad Urban') & (fac.run == 'segmentation run')).sum())} verified Overture records share an identical point with at least one other record "
              "(for example one point carries several schools and a hospital), which indicates a generic or locality geocode rather than a surveyed facility position. In a dense fabric the '20 m from a footprint' check is weak evidence. "
              "Callouts on the maps therefore label only records with a unique coordinate. One verified school is named 'University Of Mirpurkhas' (a Pakistani place name) at the same point as 'Dr. BR Ambedkar Open University Regional centre'; "
              "treat it as a mislabelled duplicate.",
              "* **Damarakunta map footers.** The five Damarakunta PNGs are the unchanged Stage B files. Their footers still read 'licence unresolved - review draft, do not redistribute', which is superseded by the Esri attribution used in the papers: "
              f"*{CREDIT}* (non-commercial academic use; raw tiles not redistributed). Crop or cover the footer for the thesis, or cite the attribution next to the figure.",
              "* **Footprints are automatic detections, not a census.** In Adilabad most instances are merged roofs (unresolved merge), so targets are built-up units, not counted houses.",
              "* **Satellite imagery** (Esri World Imagery) may be shown in the thesis with the credit line above; do not redistribute the tiles or the mosaic.", ""]
    (OUT / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"FINAL_PROJECT_OUTPUTS: {len(files)} files, series present: {have_series}, size {sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
