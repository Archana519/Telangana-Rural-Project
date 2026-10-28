#!/usr/bin/env python
"""make_first_village_report.py - build a Markdown report for the Damarakunta first-village case study.

Read-only on every project file. Every number in the tables is read from output files; nothing is typed in by hand
except the fixed limitation statements. Writes a NEW folder (refuses to overwrite):  <run-dir>\\report\\
  FIRST_VILLAGE_REPORT.md, tables\\*.csv, failed_target_diagnosis.json

Labels used:  COMPUTED (arithmetic on files) | MODEL-DERIVED (depends on model polygons / 10 m rasters)
              UNVERIFIED (source accuracy or legal status not independently checked) | LIMITATION
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name.lower() == "scripts" else HERE


def die(m):
    print("ERROR:", m); sys.exit(2)


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def rpath(p, root=ROOT):
    import os
    q = Path(str(p).replace("\\", "/")) if os.sep == "/" else Path(p)  # tolerate Windows-style paths on other systems
    return q if q.is_absolute() else root / q


def md_table(df, max_rows=60):
    import pandas as pd
    if df is None or len(df) == 0:
        return "_(no rows)_\n"
    d = df.head(max_rows).copy()
    for c in d.columns:
        d[c] = d[c].map(lambda v: "" if (isinstance(v, float) and math.isnan(v)) else (format(v, ".10g") if isinstance(v, float) else str(v)))
    head = "| " + " | ".join(map(str, d.columns)) + " |\n|" + "|".join("---" for _ in d.columns) + "|\n"
    body = "".join("| " + " | ".join(r) + " |\n" for r in d.astype(str).values.tolist())
    more = f"\n_({len(df) - max_rows} more rows in the CSV)_\n" if len(df) > max_rows else ""
    return head + body + more


def list_layers(gpkg):
    import geopandas as gpd
    try:
        return list(gpd.list_layers(gpkg)["name"])
    except AttributeError:
        import fiona
        return list(fiona.listlayers(str(gpkg)))


# ------------------------------------------------------------------ failed-target diagnosis (records + masks)
def find_target_records(tid, gpkgs):
    """Search every layer of the given GeoPackages for a column whose value equals the target id."""
    import geopandas as gpd
    hits = []
    for g in gpkgs:
        if not Path(g).exists():
            continue
        for layer in list_layers(g):
            try:
                df = gpd.read_file(g, layer=layer)
            except Exception:
                continue
            if "geometry" not in df.columns or df.geometry.isna().all():
                continue
            for col in [c for c in df.columns if c != "geometry"]:
                m = df[col].astype(str).str.strip() == str(tid)
                if m.any():
                    hits.append({"gpkg": str(g), "layer": layer, "column": col, "rows": df[m], "crs": df.crs})
    pri = lambda h: (0 if "target" in h["layer"].lower() else 1 if "cluster" in h["layer"].lower() else 2)
    return sorted(hits, key=pri)


def sample_raster(path, x, y):
    import rasterio
    with rasterio.open(path) as ds:
        r, c = ds.index(x, y)
        if r < 0 or c < 0 or r >= ds.height or c >= ds.width:
            return {"inside_grid": False, "value": None, "nodata": ds.nodata}
        v = ds.read(1, window=((r, r + 1), (c, c + 1)))[0, 0]
        return {"inside_grid": True, "value": float(v), "nodata": ds.nodata}


def nearest_free_cell_m(ref, x, y, radius_m=400):
    """Distance (m) from (x,y) to the nearest cell valid under ALL hard constraints (cost>0, not prohibited,
    slope<=limit, not water). Returns None if the rasters are not on the same grid or no valid cell is in range."""
    import rasterio
    from rasterio.windows import Window, from_bounds
    with rasterio.open(ref["cost"]) as cds:
        win = from_bounds(x - radius_m, y - radius_m, x + radius_m, y + radius_m, cds.transform).round_offsets().round_lengths()
        win = win.intersection(Window(0, 0, cds.width, cds.height))
        cost = cds.read(1, window=win).astype(float)
        wt = cds.window_transform(win)
        ok = np.isfinite(cost) & (cost > 0)
        if cds.nodata is not None:
            ok &= cost != cds.nodata
        grid = (cds.transform, cds.width, cds.height)
    for key in ("blocked", "worldcover", "slope"):
        p = ref.get(key)
        if not p:
            continue
        with rasterio.open(p) as ds:
            if (ds.transform, ds.width, ds.height) != grid:
                return None
            arr = ds.read(1, window=win).astype(float)
        if key == "blocked":
            ok &= arr <= 0
        elif key == "worldcover" and ref.get("water_class") is not None:
            ok &= arr != ref["water_class"]
        elif key == "slope" and ref.get("slope_limit") is not None:
            ok &= arr <= ref["slope_limit"]
    if not ok.any():
        return None
    rows, cols = np.indices(cost.shape)
    X, Y = wt * (cols + 0.5, rows + 0.5)
    return round(float(np.hypot(X - x, Y - y)[ok].min()), 1)


def diagnose_failed(failed, ref_summary, plan_gpkg, access_gpkg, root):
    P = ref_summary["params"]
    cons = ref_summary.get("constraints_resolved", {})
    rast = {"cost": rpath(P["cost"], root), "blocked": rpath(P["blocked"], root) if P.get("blocked") else None,
            "slope": rpath(P["slope"], root) if P.get("slope") else None, "worldcover": rpath(P["worldcover"], root) if P.get("worldcover") else None,
            "water_class": cons.get("water_class"), "slope_limit": cons.get("slope_limit_deg")}
    out = {}
    for tid, reason in failed.items():
        rec = {"planner_failure_reason": reason, "records_found": [], "tests": [], "conclusion": None}
        hits = find_target_records(tid, [plan_gpkg, access_gpkg])
        if not hits:
            rec["conclusion"] = "UNRESOLVED: no record of this target with geometry was found in the planner GeoPackage or the access GeoPackage."
            out[tid] = rec; continue
        h = hits[0]
        rec["records_found"] = [{"gpkg": x["gpkg"], "layer": x["layer"], "column": x["column"], "n_rows": int(len(x["rows"]))} for x in hits]
        rows = h["rows"].to_crs(32644) if h["crs"] is not None and h["crs"].to_epsg() != 32644 else h["rows"]
        g = rows.geometry.union_all() if hasattr(rows.geometry, "union_all") else rows.geometry.unary_union
        pts = {"centroid": g.centroid, "representative_point": g.representative_point()}
        if g.geom_type == "Point":
            pts = {"point": g}
        any_flag = []
        for nm, pt in pts.items():
            t = {"point": nm, "x": round(pt.x, 2), "y": round(pt.y, 2), "flags": []}
            c = sample_raster(rast["cost"], pt.x, pt.y); t["cost"] = c
            if not c["inside_grid"]:
                t["flags"].append("outside cost grid")
            elif c["value"] is None or not np.isfinite(c["value"]) or c["value"] <= 0 or (c["nodata"] is not None and c["value"] == c["nodata"]):
                t["flags"].append("cost invalid (nodata or <= 0)")
            if rast["blocked"]:
                b = sample_raster(rast["blocked"], pt.x, pt.y); t["prohibited"] = b
                if b["inside_grid"] and b["value"] is not None and b["value"] > 0:
                    t["flags"].append("prohibited mask > 0")
            if rast["slope"]:
                s = sample_raster(rast["slope"], pt.x, pt.y); t["slope_deg"] = s
                if s["inside_grid"] and s["value"] is not None and rast["slope_limit"] is not None and s["value"] > rast["slope_limit"]:
                    t["flags"].append(f"slope > {rast['slope_limit']} deg")
            if rast["worldcover"] and rast["water_class"] is not None:
                w = sample_raster(rast["worldcover"], pt.x, pt.y); t["worldcover"] = w
                if w["inside_grid"] and w["value"] == rast["water_class"]:
                    t["flags"].append("WorldCover water class")
            try:
                t["distance_to_nearest_cell_valid_under_all_hard_constraints_m"] = nearest_free_cell_m(rast, pt.x, pt.y)
            except Exception as ex:
                t["distance_to_nearest_valid_cell_m"] = f"not computed: {type(ex).__name__}"
            rec["tests"].append(t); any_flag.append(t["flags"])
        src = f"{h['layer']}.{h['column']} in {Path(h['gpkg']).name}"
        planner_geom = "target" in h["layer"].lower()
        if any(any_flag):
            sets = {tuple(f) for f in any_flag if f}
            rec["conclusion"] = (f"CONSISTENT WITH the planner failure reason: {sorted(sets)} at the tested point(s). Geometry source: {src}. "
                                 + ("This layer looks like the planner's own target layer." if planner_geom else
                                    "The planner's exact target cell is NOT recorded in its outputs, so this is consistency evidence, not confirmation."))
        else:
            rec["conclusion"] = (f"UNRESOLVED: none of the tested points ({', '.join(pts)}) falls in a hard-constraint cell. Geometry source: {src}. "
                                 "The planner's target cell is not recorded, so the cause cannot be determined from the files.")
        out[tid] = rec
    return out


# ---------------------------------------------------------------------------------------------- main
def main():
    import pandas as pd
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--ref-run", default="run7_regress"); ap.add_argument("--repro-run", default="fv_repro1")
    ap.add_argument("--runs-root", required=True); ap.add_argument("--experiments-dir", default=None)
    ap.add_argument("--ag-dir", default=None); ap.add_argument("--village-dir", default=str(Path("Siddipet") / "Damarakunta"))
    ap.add_argument("--out-dir", default=None)
    a = ap.parse_args()
    run_dir, runs_root, village = Path(a.run_dir), Path(a.runs_root), rpath(a.village_dir)
    out = Path(a.out_dir) if a.out_dir else run_dir / "report"
    if out.exists():
        die(f"{out} exists; refusing to overwrite")
    ref_dir, rep_dir = runs_root / a.ref_run, runs_root / a.repro_run
    for d in (ref_dir, rep_dir):
        if not (d / "summary.json").exists():
            die(f"missing {d / 'summary.json'}")
    (out / "tables").mkdir(parents=True)
    ref, rep = jload(ref_dir / "summary.json"), jload(rep_dir / "summary.json")
    L = []
    w = L.append
    caveat = rep.get("caveat", "")
    w("# First-village case study: Damarakunta, Markook Mandal, Siddipet, Telangana\n")
    w("> **Status banner.** All routes are **unverified planning alternatives** computed from model-derived building polygons and a 10 m cost raster. "
      "They are not verified roads, not legally approved, not construction-ready, and not field-validated. "
      "Routing cost values are **routing cost units, not money**. Weights are ordinal design parameters.\n")
    w(f"Planner caveat (from `summary.json`): _{caveat}_\n")

    # 1 run identity & reproducibility
    w("## 1. Runs and reproducibility  `COMPUTED`\n")
    w(f"- Reference run: `{a.ref_run}`  \n- Reproduced run: `{a.repro_run}` (same parameters, rerun)  \n- Planner: `{rep.get('version')}`, CRS {rep.get('village_crs')}\n")
    rc_p = run_dir / "repro_check.json"
    if rc_p.exists():
        rc = jload(rc_p)
        w(f"**Reproducibility check result: {rc.get('overall')}**  \n_{rc.get('note', rc.get('error', ''))}_\n")
        w(md_table(pd.DataFrame(rc.get("checks", []))))
    else:
        w("_repro_check.json not found: reproducibility result unavailable._\n")

    # 2 inputs
    w("## 2. Input inventory and provenance\n")
    lg = jload(run_dir / "run_log.json") if (run_dir / "run_log.json").exists() else {}
    inp = pd.DataFrame(lg.get("inputs", []))
    if len(inp):
        inp["sha256"] = inp.get("sha256", pd.Series(dtype=str)).astype(str).str[:16] + "..."
        inp.to_csv(out / "tables" / "inputs.csv", index=False)
        w("`COMPUTED` (SHA-256 prefixes; full hashes in `run_log.json`)\n"); w(md_table(inp[[c for c in ("param", "path", "bytes", "sha256", "exists") if c in inp.columns]]))
    prov = [("Imagery (ESRI 0.6 m mosaic)", "UNVERIFIED", "No licence/terms file found; use rights not established (cf. DECISIONS #4 for TGRAC)."),
            ("Building polygons (v8 semantic-mask candidates)", "MODEL-DERIVED", "Output of a semantic model (StrongDINOv2Seg); blobs, some merged; class mapping unverified."),
            ("Road network (TGRAC)", "UNVERIFIED", "External reference layer; accuracy not independently checked."),
            ("Facilities (school compounds, TGRAC health, TGRAC anganwadi)", "UNVERIFIED", "From named source files; planner flags the sub-centre and anganwadi as UNVERIFIED_FLAGGED."),
            ("Cost surface / WorldCover / slope / prohibited mask (10 m)", "MODEL-DERIVED", "Derived rasters; weights are design parameters."),
            ("Google Open Buildings v3", "REFERENCE ONLY", "Model output, not ground truth; not used by the planner in this run.")]
    w("\n" + md_table(pd.DataFrame(prov, columns=["Layer", "Label", "Note"])))

    # 3 planner results
    w("## 3. Planner results (reproduced run)  `COMPUTED` on `MODEL-DERIVED` inputs\n")
    pc = pd.read_csv(rep_dir / "plan_comparison.csv"); pc.to_csv(out / "tables" / "plan_comparison.csv", index=False)
    w(md_table(pc))
    w("_Straight-line plan: routes marked infeasible cross hard constraints and must not be counted as served._\n")
    tt = pd.read_csv(rep_dir / "target_table.csv"); tt.to_csv(out / "tables" / "target_table.csv", index=False)
    w("### Target table\n"); w(md_table(tt))
    c2 = rep.get("c2_check", {})
    w("### Network-attachment (C2) check\n")
    w(f"- Targets attached to another selected route: {c2.get('targets_attached_to_other_selected_routes')}  \n"
      f"- Targets whose route differs from the independent plan: {c2.get('targets_with_route_different_from_independent')}  \n"
      f"- Unique length reduction: {c2.get('unique_len_reduction_m')} m ({c2.get('unique_len_reduction_pct')} %)  \n"
      f"- Re-routes changed: {c2.get('reroutes_changed')}\n")
    w("_This is the effect on THIS target set only; the number of changed routes is stated above, not extrapolated._\n")
    dc = rep.get("data_check", {})
    w("### Data check recorded by the planner\n")
    w(f"- Cost raster invalid share: {dc.get('cost_raster', {}).get('invalid_share')}  \n- Cells over slope limit with valid cost: {dc.get('slope', {}).get('forbidden_cells_with_valid_cost')}  \n"
      f"- Road cells: {dc.get('road_cells')}  \n- Targets: {dc.get('targets')}\n")

    # 4 failed targets
    w("## 4. Failed targets  `COMPUTED` from records and masks\n")
    failed = rep.get("failed_targets", {})
    if failed:
        P = rep["params"]
        try:
            diag = diagnose_failed(failed, rep, rep_dir / "network_v2.gpkg", rpath(P["access_gpkg"]), ROOT)
        except Exception as ex:
            diag = {t: {"planner_failure_reason": r, "records_found": [], "tests": [],
                        "conclusion": f"UNRESOLVED: the diagnosis could not run ({type(ex).__name__}: {ex})"} for t, r in failed.items()}
        (out / "failed_target_diagnosis.json").write_text(json.dumps(diag, indent=2, default=str), encoding="utf-8")
        for tid, d in diag.items():
            w(f"### {tid}\n- Planner reason: `{d['planner_failure_reason']}`  \n- Records found: {d['records_found'] or 'none'}  \n- **Finding:** {d['conclusion']}\n")
            if d["tests"]:
                rows = [{"point": t["point"], "x": t["x"], "y": t["y"], "flags": "; ".join(t["flags"]) or "none",
                         "slope_deg": (t.get("slope_deg") or {}).get("value"), "worldcover": (t.get("worldcover") or {}).get("value"),
                         "prohibited": (t.get("prohibited") or {}).get("value"),
                         "dist_to_valid_cell_m": t.get("distance_to_nearest_cell_valid_under_all_hard_constraints_m")} for t in d["tests"]]
                w(md_table(pd.DataFrame(rows)))
    else:
        w("No failed targets recorded.\n")

    # 5 access gain
    w("## 5. Access gain recomputed for the same runs  `COMPUTED` (proximity, auxiliary)\n")
    agd = Path(a.ag_dir) if a.ag_dir else None
    if agd and (agd / "access_gain_summary.csv").exists():
        ag = pd.read_csv(agd / "access_gain_summary.csv"); ag.to_csv(out / "tables" / "access_gain_summary_all.csv", index=False)
        sel = ag
        if "scenario" in ag.columns and "run" in ag.columns:
            sel = ag[ag["scenario"].astype(str).str.contains("network_aware")]
            if "building_set" in ag.columns:
                sel = sel[sel["building_set"].isin(["all_candidate_polygons", "gap_cluster_polygons", "polygon_gap_flag_true", "settlement_interior_screening"])]
        sel.to_csv(out / "tables" / "access_gain_selected.csv", index=False)
        w(f"_Source: `{agd}`. Runs included: {sorted(ag['run'].unique()) if 'run' in ag.columns else 'see CSV'}. "
          "The statistic is a distance to a road or proposed route; it is NOT proof of physical or legal access._\n")
        w(md_table(sel))
        if "run" in ag.columns and {a.ref_run, a.repro_run} <= set(ag["run"]):
            k = [c for c in ag.columns if c not in ("run",)]
            A = ag[ag.run == a.ref_run][k].reset_index(drop=True).astype(str); B = ag[ag.run == a.repro_run][k].reset_index(drop=True).astype(str)
            w(f"**Access-gain agreement between reference and reproduced run:** {'identical' if A.equals(B) else 'DIFFERENT'} ({len(A)} vs {len(B)} rows).\n")
        fa = agd / "facility_access_gain.csv"
        if fa.exists():
            fdf = pd.read_csv(fa); fdf.to_csv(out / "tables" / "facility_access_gain.csv", index=False)
            w("### Facilities\n"); w(md_table(fdf))
    else:
        w("**Access-gain figures are unavailable** (the access-gain stage did not produce `access_gain_summary.csv`; see `logs\\`).\n")

    # 6 existing experiments
    w("## 6. Earlier C1/C2 experiments (read only, NOT recomputed here)\n")
    ed = Path(a.experiments_dir) if a.experiments_dir else None
    if ed and ed.exists():
        w(f"_Source folder `{ed}` (files as produced earlier). C1 perturbations are synthetic and labelled so._\n")
        for fn in ("c1_summary.csv", "c2_scenarios.csv", "c2_ablation.csv"):
            if (ed / fn).exists():
                d = pd.read_csv(ed / fn); d.to_csv(out / "tables" / ("experiments_" + fn), index=False)
                w(f"### {fn}\n"); w(md_table(d))
    else:
        w("_Experiments folder not found._\n")

    # 7 counts and limits
    w("## 7. Building-count context  `COMPUTED`\n")
    ctx = []
    try:
        import geopandas as gpd
        bp = rpath(rep["params"]["buildings"]); bl = rep["params"].get("buildings_layer") or None
        b = gpd.read_file(bp, layer=bl) if bl else gpd.read_file(bp)
        ctx.append(("v8 candidate polygons in the layer", len(b)))
        if "inside_village" in b.columns:
            ctx.append(("of which inside_village is true", int(b["inside_village"].astype(str).str.lower().isin(["true", "1"]).sum())))
        if "quality_class" in b.columns:
            for k_, v_ in b["quality_class"].value_counts().items():
                ctx.append((f"v8 quality_class = {k_}", int(v_)))
        ag_all = None
        if agd and (agd / "access_gain_summary.csv").exists() and "building_set" in ag.columns:
            r_ = ag[ag.building_set == "all_candidate_polygons"]
            if len(r_):
                ctx.append(("polygons in the access analysis (all_candidate_polygons)", int(r_["n_polygons"].iloc[0])))
    except Exception as ex:
        ctx.append(("v8 layer could not be read", f"{type(ex).__name__}"))
    gp = village / "results" / "google_open_buildings" / "provenance.json"
    if gp.exists():
        g = jload(gp); ctx.append(("Google Open Buildings v3 polygons in the study area (reference only)", g.get("feature_count")))
    w(md_table(pd.DataFrame(ctx, columns=["Quantity", "Value"])))
    w("\n## 8. Limitations and unverified items\n")
    for s in [
        "The planner's access analysis uses the polygons listed above. That count is **not** the confirmed number of buildings in the village; "
        "model polygons can merge or miss roofs, and `est_roofs` is a proxy, not a house count.",
        "Google Open Buildings footprints are **reference data, not ground truth**, and were not used by the planner in this run.",
        "Routing costs are **routing cost units**, not monetary construction costs. No monetary estimate is made.",
        "A building or facility being within 50 m of a road or proposed route is a **proximity statistic**, not proof of access, passability or legal access.",
        "Facility source files (school compounds, TGRAC health, TGRAC anganwadi) are **not independently verified**; the sub-centre and anganwadi are flagged unverified by the planner.",
        "The **imagery licence is unverified**.",
        "No field validation, construction readiness, land ownership, road width or passability is claimed.",
        "The segmentation checkpoint was validated on LoveDA only; its class mapping for this village is unverified.",
        "Whether Google footprints are displaced relative to the imagery is **unresolved** (study parked).",
        "The straight-line baseline ignores hard constraints; its infeasible routes are not served targets.",
        "Results describe this target set in this village only; no generalisation to other villages is made.",
    ]:
        w(f"- `LIMITATION` {s}")
    w("\n## 9. How to reproduce\n")
    w("```\n.venv\\Scripts\\python.exe scripts\\run_first_village.py --dry-run\n.venv\\Scripts\\python.exe scripts\\run_first_village.py\n```\n"
      f"Run log, commands, exit codes and SHA-256 hashes: `{run_dir / 'run_log.json'}`\n")
    (out / "FIRST_VILLAGE_REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print("report written:", out / "FIRST_VILLAGE_REPORT.md")


if __name__ == "__main__":
    main()
