"""Result collection and tables for the four study areas (terminal tables, `--compare-all`, the paper's `paper_comparison_table.tex`).

Every number is READ from files that the pipeline already wrote (nothing is typed in); a value that is not available on this machine is `None` and shows as n/a in the terminal and as
`\\pending{...}` in LaTeX, so the table fills itself when the pipeline is re-run and `--compare-all` regenerates the snippet.

Sources per area (relative to the repository root):
    area profile        <results>/area_profile.csv                       (window area, existing road length, terrain slope; written by `compute_area_profile`)
    segmentation model  inputs/segmentation_validation_loveda.json       (LoveDA validation of the checkpoint; model-level, the same for every area)
    footprints, targets <seg results>/metrics_summary.json               (Damarakunta: Stage B files)
    facilities          configs/multivillage/villages/<id>_verified_facilities.csv   (rows with use_in_analysis = True)
    10 m soft penalty   <seg results>/routing_strategy_comparison.csv    (Damarakunta: FINAL_PROJECT_OUTPUTS/01_DAMARAKUNTA_RURAL/tables/table1_length_reduction.csv, x4 primary)
    5 m clearance       <maps>/clearance_verification.csv               (Stage A = independent routes, Stage B = shared network; building crossings)
Costs are km x the owner-supplied, unverified PMGSY-based rate in inputs/economic_assumptions.json (Rs 75 lakh/km central): illustrative, not an engineering estimate.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
C3 = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE"
FPO = REPO / "FINAL_PROJECT_OUTPUTS"
CATS = ["School", "College", "Hospital", "Government Office", "Anganwadi"]
CRS = "EPSG:32644"

# key -> everything the runner and the tables need (config id, folders, labels)
AREAS = {
    "damarakunta": dict(key="damarakunta", label="Damarakunta", config="damarakunta_open", slug="damarakunta", district="Siddipet", typology="Rural", bundle="01_DAMARAKUNTA_RURAL_OPEN",
                        results=C3 / "00_DAMARAKUNTA_OPEN_SEGMENTATION", seg=C3 / "00_DAMARAKUNTA_OPEN_SEGMENTATION", maps=C3 / "00_DAMARAKUNTA_OPEN_SEGMENTATION" / "final_maps_1_to_5"),
    "adilabad": dict(key="adilabad", label="Adilabad", config="adilabad_urban_updated", slug="adilabad_updated", district="Adilabad", typology="Urban / semi-urban", bundle="02_ADILABAD_URBAN_UPDATED",
                     results=C3 / "01_ADILABAD_UPDATED_SEGMENTATION", seg=C3 / "01_ADILABAD_UPDATED_SEGMENTATION", maps=C3 / "01_ADILABAD_UPDATED_SEGMENTATION" / "final_maps_1_to_5"),
    "aswaraopeta": dict(key="aswaraopeta", label="Aswaraopeta", config="aswaraopeta", slug="aswaraopeta", district="Bhadradri Kothagudem", typology="Semi-urban / tribal fringe", bundle="03_ASWARAOPETA_SEMI_URBAN",
                        results=C3 / "02_ASWARAOPETA_SEGMENTATION", seg=C3 / "02_ASWARAOPETA_SEGMENTATION", maps=C3 / "02_ASWARAOPETA_SEGMENTATION" / "final_maps_1_to_5"),
    "alampur": dict(key="alampur", label="Alampur", config="alampur", slug="alampur", district="Jogulamba Gadwal", typology="Heritage / semi-urban", bundle="04_ALAMPUR",
                    results=C3 / "03_ALAMPUR_SEGMENTATION", seg=C3 / "03_ALAMPUR_SEGMENTATION", maps=C3 / "03_ALAMPUR_SEGMENTATION" / "final_maps_1_to_5"),
}
ORDER = ["damarakunta", "adilabad", "aswaraopeta", "alampur"]


def rate_lakh_per_km() -> tuple:
    a = json.loads((REPO / "inputs/economic_assumptions.json").read_text(encoding="utf-8"))["rate_lakh_per_km"]
    return a["low"], a["central"], a["high"]


def _read(path: Path):
    return pd.read_csv(path) if Path(path).exists() else None


def loveda() -> dict | None:
    f = REPO / "inputs" / "segmentation_validation_loveda.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


# ------------------------------------------------------------------------------------------------ terrain / profile
def slope_percent_stats(slope_deg: np.ndarray, mask: np.ndarray) -> tuple:
    """Mean and maximum PERCENT slope inside the polygon: p = 100 tan(S) per cell (S = slope in degrees from the Sobel DEM gradient)."""
    s = slope_deg[mask & np.isfinite(slope_deg)]
    if not len(s):
        return None, None
    p = 100.0 * np.tan(np.radians(s.astype("float64")))
    return float(p.mean()), float(p.max())


def compute_area_profile(key: str, log=print) -> dict | None:
    """Window area, existing road length and terrain slope of one area from the local (git-ignored) data; writes <results>/area_profile.csv. None if the data are not on this machine."""
    import geopandas as gpd
    import rasterio
    from rasterio.features import rasterize

    a = AREAS[key]
    if False:                                          # Damarakunta now follows the open-data route like the other windows
        root = REPO / "Siddipet" / "Damarakunta"
        cell = gpd.read_file(root / "study_area/damarakunta_boundary.gpkg").to_crs(CRS).geometry.union_all()
        roads = gpd.read_file(root / "reference/tgrac_road_network.gpkg").to_crs(CRS).geometry.intersection(cell)
        slope_f = root / "aligned" / "damarakunta_slope_10m.tif"
        if slope_f.exists():
            with rasterio.open(slope_f) as s:
                sl, T = s.read(1).astype("float32"), s.transform
                sl[sl == s.nodata] = np.nan if s.nodata is not None else sl[sl == s.nodata]
        else:
            sl, T = _damarakunta_slope_rebuilt(cell)
    else:
        d = REPO / "data" / "villages" / a["config"]
        if not (d / "boundary.gpkg").exists() or not (d / "slope_10m.tif").exists():
            log(f"  area profile: data/villages/{a['config']} not on this machine -> profile not recomputed")
            return None
        cell = gpd.read_file(d / "boundary.gpkg").to_crs(CRS).geometry.union_all()
        roads = gpd.read_file(d / "roads.gpkg").to_crs(CRS).geometry.intersection(cell)
        with rasterio.open(d / "slope_10m.tif") as s:
            sl, T = s.read(1).astype("float32"), s.transform
            if s.nodata is not None:
                sl[sl == s.nodata] = np.nan
    inside = rasterize([(cell, 1)], out_shape=sl.shape, transform=T, fill=0, all_touched=False, dtype="uint8").astype(bool)
    mean_p, max_p = slope_percent_stats(sl, inside)
    prof = dict(area=key, window_km2=round(cell.area / 1e6, 3), roads_km=round(float(roads.length.sum()) / 1000, 3), slope_mean_pct=None if mean_p is None else round(mean_p, 2),
                slope_max_pct=None if max_p is None else round(max_p, 2), slope_mean_deg=round(float(np.nanmean(sl[inside])), 2), source="Copernicus GLO-30 DEM, Sobel slope on the 10 m grid, cells inside the study polygon")
    a["results"].mkdir(parents=True, exist_ok=True)
    pd.DataFrame([prof]).to_csv(a["results"] / "area_profile.csv", index=False, lineterminator="\n")
    log(f"  area profile -> {a['results'].relative_to(REPO)}/area_profile.csv: {prof['window_km2']} km2, roads {prof['roads_km']} km, slope mean {prof['slope_mean_pct']} % / max {prof['slope_max_pct']} %")
    return prof


def _damarakunta_slope_rebuilt(cell):
    """Slope for Damarakunta from the committed open DEM (Siddipet/Damarakunta/aligned_open), same recipe as the other areas (used when the Stage B aligned slope raster is not on this machine)."""
    import shutil
    import tempfile

    import rasterio
    from src.utils import data_downloader_helper as dl
    from . import acquire as A, prepare as P
    tmp = Path(tempfile.mkdtemp(prefix="dk_slope_"))
    root = REPO / "Siddipet" / "Damarakunta" / "aligned_open"
    b10, T, shape = P.grid_for_cell(cell, 10.0)
    dl.warp_to_grid([str(root / "worldcover_10m.tif")], b10, CRS, 10.0, tmp / "worldcover_10m.tif", "nearest", "uint8", 0)
    b30 = dl.aligned_bounds(b10, 30.0, buffer_m=60.0)
    dl.warp_to_grid([str(root / "dem_30m.tif")], b30, CRS, 30.0, tmp / "dem_30m.tif", "bilinear", "float32", -9999.0)
    prep = P.prepare_rasters(A.load_cfg("adilabad_urban"), cell, tmp, log=lambda *x: None)
    sl, T = prep["slope"], prep["transform"]
    shutil.rmtree(tmp, ignore_errors=True)
    return sl, T


# ------------------------------------------------------------------------------------------------ one area
def facility_counts(key: str) -> dict | None:
    a = AREAS[key]
    cid = a["config"] or "damarakunta"
    t = _read(REPO / "configs" / "multivillage" / "villages" / f"{cid}_verified_facilities.csv")
    if t is None:
        return None
    if "use_in_analysis" in t:
        t = t[t.use_in_analysis.astype(str).str.lower() == "true"]
    return {c: int((t.category == c).sum()) for c in CATS}


def collect(key: str) -> dict:
    """All table values of one area (None where a source file is missing)."""
    a = AREAS[key]
    m = dict(key=key, label=a["label"], district=a["district"], typology=a["typology"])
    prof = _read(a["results"] / "area_profile.csv")
    p = prof.iloc[0].to_dict() if prof is not None else {}
    m.update(window_km2=p.get("window_km2"), roads_km=p.get("roads_km"), slope_mean_pct=p.get("slope_mean_pct"), slope_max_pct=p.get("slope_max_pct"))
    lv = loveda()
    m["seg"] = lv
    # footprints and targets
    if True:
        ms = a["seg"] / "metrics_summary.json"
        if ms.exists():
            j = json.loads(ms.read_text(encoding="utf-8"))
            m["buildings"], m["gap_targets"] = j["footprints_total"], j["gap_targets"]
        rs = _read(a["seg"] / "routing_strategy_comparison.csv")
        if rs is not None:
            ind = rs[rs.strategy == "Independent least-cost routes"].iloc[0]
            two = rs[rs.strategy == "Two-stage shared plan"].iloc[0]
            m["soft_indep_m"], m["soft_shared_m"] = float(ind.unique_len_m), float(two.unique_len_m)
            m["soft_cross_routes"], m["soft_cross_m"] = int(two.routes_crossing_other_footprints), float(two.length_inside_other_footprints_m)
    # facilities
    m["facilities"] = facility_counts(key)
    # 5 m clearance network (Stage A = independent, Stage B = shared)
    cv = _read(a["maps"] / "clearance_verification.csv")
    if cv is not None:
        c = cv.iloc[0]
        indep = float(c["independent_m"]) if "independent_m" in c else None
        shared = float(c["shared_m"]) if "shared_m" in c else None
        if indep is None:                                                                  # maps output of make_village_map_series: lengths are in network_length_cost_summary.csv
            n = _read(a["maps"] / "network_length_cost_summary.csv")
            if n is not None:
                indep = float(n[n.network.str.startswith("CLEARANCE: alternative independent")].length_m.iloc[0])
                shared = float(n[n.network.str.startswith("CLEARANCE: proposed shared two-stage network, house")].length_m.iloc[0])
        m.update(stageA_m=indep, stageB_m=shared, routed=int(c["house_routed"]), targets_clear=int(c["house_targets"]),
                 crossings=int(c["house_indep_routes_crossing"]) + int(c["house_shared_routes_crossing"]), crossing_m=float(c["house_indep_length_inside_other_footprints_m"]) + float(c["house_shared_length_inside_other_footprints_m"]),
                 grid_m=float(c["grid_m"]), clearance_m=float(c["clearance_m"]))
        if indep and shared:
            m["saving_pct"] = 100.0 * (1.0 - shared / indep)
            m["cost_lakh"] = shared / 1000.0 * rate_lakh_per_km()[1]
    return m


# ------------------------------------------------------------------------------------------------ formatting
def f(x, nd=1, comma=True, suffix=""):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return (f"{x:,.{nd}f}" if comma else f"{x:.{nd}f}") + suffix


def boxed(title: str, header: list, rows: list) -> str:
    """Unicode bordered table. rows: lists of strings; a row [''] * n is not special; a row starting with '§' is a section line."""
    cols = len(header)
    sect = [r for r in rows if r and str(r[0]).startswith("§")]
    body = [r for r in rows if r not in sect]
    w = [max(len(str(x)) for x in [header[i]] + [r[i] for r in body]) for i in range(cols)]
    need = max([len(title)] + [len(r[0]) - 1 for r in sect]) + 4
    if sum(w) + 3 * (cols - 1) + 4 < need:
        w[0] += need - (sum(w) + 3 * (cols - 1) + 4)                         # widen the first column so the title always fits inside the frame
    total = sum(w) + 3 * (cols - 1) + 4
    top, mid, bot = "╔" + "═" * (total - 2) + "╗", "╠" + "═" * (total - 2) + "╣", "╚" + "═" * (total - 2) + "╝"

    def line(vals):
        return "║ " + " │ ".join(str(v).ljust(w[i]) if i == 0 else str(v).rjust(w[i]) for i, v in enumerate(vals)) + " ║"
    out = [top, "║ " + title.ljust(total - 4) + " ║", mid, line(header), mid]
    for r in rows:
        if r in sect:
            out.append("║ " + r[0][1:].strip().upper().ljust(total - 4) + " ║")
        else:
            out.append(line(r))
    out.append(bot)
    return "\n".join(out)


def terminal_tables(metrics: list) -> str:
    """Three tables for one or several areas (columns = areas)."""
    lo, ce, hi = rate_lakh_per_km()
    labels = [m["label"] for m in metrics]
    lv = metrics[0].get("seg")
    t1 = [["Overall pixel accuracy OA (%)"] + [f(lv and lv["pixel_accuracy_pct"]) for m in metrics],
          ["Precision, macro (%)"] + [f(lv and lv["precision_macro_pct"]) for m in metrics],
          ["Recall, macro (%)"] + [f(lv and lv["recall_macro_pct"]) for m in metrics],
          ["F1-score = mean Dice (%)"] + [f(lv and lv["dice_mean_pct"]) for m in metrics],
          ["mIoU (%)"] + [f(lv and lv["miou_pct"]) for m in metrics],
          ["Extracted building footprints"] + [f(m.get("buildings"), 0) for m in metrics]]
    fac = lambda m, c: f(m["facilities"][c], 0) if m.get("facilities") else "n/a"
    t2 = [["Window area (km2)"] + [f(m.get("window_km2"), 2) for m in metrics],
          ["Existing road length (km)"] + [f(m.get("roads_km"), 1) for m in metrics],
          ["Extracted buildings"] + [f(m.get("buildings"), 0) for m in metrics],
          ["Road-gap target buildings (>30 m from a road)"] + [f(m.get("gap_targets"), 0) for m in metrics],
          ["Routed buildings (5 m clearance network)"] + [f(m.get("routed"), 0) for m in metrics]] + \
         [[f"Verified facilities: {c}"] + [fac(m, c) for m in metrics] for c in CATS] + \
         [["Verified facilities: total"] + [f(sum(m["facilities"].values()), 0) if m.get("facilities") else "n/a" for m in metrics]]
    t3 = [["Stage A independent, unique length (km)"] + [f(m.get("stageA_m") and m["stageA_m"] / 1000, 2) for m in metrics],
          ["Stage B shared trunk, unique length (km)"] + [f(m.get("stageB_m") and m["stageB_m"] / 1000, 2) for m in metrics],
          ["Corridor length saving (%)"] + [f(m.get("saving_pct"), 1) for m in metrics],
          ["Building crossings, 5 m clearance (routes)"] + [f(m.get("crossings"), 0) for m in metrics],
          ["Building crossings, 10 m soft penalty mu=4 (routes)"] + [f(m.get("soft_cross_routes"), 0) for m in metrics],
          ["Mean / max terrain slope (%)"] + [f"{f(m.get('slope_mean_pct'))} / {f(m.get('slope_max_pct'))}" for m in metrics],
          [f"PMGSY-benchmarked cost (INR lakh, Rs {ce:g} lakh/km)"] + [f(m.get("cost_lakh"), 0) for m in metrics]]
    hdr = ["metric"] + labels
    return "\n\n".join([boxed("1. SEGMENTATION AND EXTRACTION (LoveDA validation; one checkpoint)", hdr, t1),
                        boxed("2. FACILITY AND BUILDING COVERAGE", hdr, t2),
                        boxed(f"3. STAGE A vs STAGE B ROUTING; PMGSY-BENCHMARKED COST (Rs {lo:g}-{hi:g} lakh/km)", hdr, t3)])


# ------------------------------------------------------------------------------------------------ LaTeX
def tex_cell(x, nd=1, comma=True, pct=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return r"\pending{n/a}"
    s = f"{x:,.{nd}f}".replace(",", "{,}") if comma else f"{x:.{nd}f}"
    return s


def latex_table(metrics: list) -> str:
    """`paper_comparison_table.tex`: one booktabs table, rows = metrics grouped in four blocks, columns = the four areas. Needs \\pending{} defined in the preamble."""
    lo, ce, hi = rate_lakh_per_km()
    ms = {m["key"]: m for m in metrics}
    cols = [ms[k] for k in ORDER if k in ms]
    lv = cols[0].get("seg")
    fac = lambda m, c: tex_cell(m["facilities"][c], 0) if m.get("facilities") else r"\pending{n/a}"
    rows = []

    def add(name, vals):
        rows.append(name + " & " + " & ".join(vals) + r" \\")
    sec = lambda t: rows.append(r"\midrule" + "\n" + r"\multicolumn{5}{@{}l}{\textit{" + t + r"}}\\")
    sec("Study area profile")
    add("District", [m["district"] for m in cols])
    add("Typology", [m["typology"] for m in cols])
    add(r"Window area (km$^2$)", [tex_cell(m.get("window_km2"), 2) for m in cols])
    add("Existing road length (km)", [tex_cell(m.get("roads_km"), 1) for m in cols])
    sec(r"Segmentation and extraction (model metrics: LoveDA validation, one checkpoint for all areas)")
    for name, k in (("Overall accuracy (\\%)", "pixel_accuracy_pct"), ("Precision, macro (\\%)", "precision_macro_pct"), ("Recall, macro (\\%)", "recall_macro_pct"), ("F1-score = mean Dice (\\%)", "dice_mean_pct"), ("mIoU (\\%)", "miou_pct")):
        v = tex_cell(lv[k], 1) if lv else r"\pending{n/a}"
        rows.append(name + r" & \multicolumn{4}{c}{" + v + r"} \\")
    add("Extracted building footprints", [tex_cell(m.get("buildings"), 0) for m in cols])
    sec("Verified public infrastructure (audited, on building footprints)")
    for c in CATS:
        add(c if c != "Government Office" else "Government office", [fac(m, c) for m in cols])
    add("Total verified facilities", [tex_cell(sum(m["facilities"].values()), 0) if m.get("facilities") else r"\pending{n/a}" for m in cols])
    sec(r"Stage A vs.\ Stage B routing (5\,m zero-crossing clearance) and PMGSY-benchmarked cost")
    add("Road-gap target buildings", [tex_cell(m.get("gap_targets"), 0) for m in cols])
    add("Routed buildings", [tex_cell(m.get("routed"), 0) for m in cols])
    add("Stage A independent length (km)", [tex_cell(m.get("stageA_m") and m["stageA_m"] / 1000, 2) for m in cols])
    add("Stage B shared-trunk length (km)", [tex_cell(m.get("stageB_m") and m["stageB_m"] / 1000, 2) for m in cols])
    add(r"Corridor length saving (\%)", [tex_cell(m.get("saving_pct"), 1) for m in cols])
    add("Building crossings (routes)", [tex_cell(m.get("crossings"), 0) for m in cols])
    add(r"Mean terrain slope (\%)", [tex_cell(m.get("slope_mean_pct"), 1) for m in cols])
    add(r"PMGSY-benchmarked cost (INR lakh)", [tex_cell(m.get("cost_lakh"), 0) for m in cols])
    head = " & ".join(["Metric"] + [m["label"] for m in cols]) + r" \\"
    return ("% generated by scripts/run_village_pipeline.py --compare-all (do not edit by hand); \\pending{...} marks a value not yet computed on the machine that generated this file\n"
            "\\begin{tabular}{@{}l" + "r" * len(cols) + "@{}}\n\\toprule\n" + head + "\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n"
            f"% PMGSY-benchmarked cost = unique Stage B length (km) x Rs {ce:g} lakh/km (sensitivity range {lo:g}-{hi:g})\n")
