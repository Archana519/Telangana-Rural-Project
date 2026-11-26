#!/usr/bin/env python
"""One-command demo of the whole open-data pipeline, for presentations. Runs offline from cached inputs (nothing here waits for Overpass or any other mirror).

    run_demo.bat                                  # Windows: activates .venv and runs this script
    python scripts/run_full_demo.py               # the same on any machine
    python scripts/run_full_demo.py --no-open     # do not open the output folder at the end
    python scripts/run_full_demo.py --online      # allow the Esri imagery service for windows that are not cached (default: cached imagery only)

First run on a machine without demo_cache/damarakunta_open_cache.zip (it is git-ignored): the inputs are prepared locally (needs internet once: Overture / OSM roads, WorldCover and Copernicus tiles, Esri imagery tiles;
the StrongDINOv2Seg footprints are the existing local ones) and the zip is saved, so every later run is offline and takes under a minute.

Stages (each prints its progress and takes a few seconds):
  1  Data and window load        restore the cached open-data inputs of the Damarakunta window (demo_cache/), build the study state; list the four windows
  2  Segmentation and footprints StrongDINOv2Seg footprints of the window (the stored instances of the frozen checkpoint, clipped to the window; the PyTorch inference itself is not repeated)
  3  Terrain cost surface        WorldCover + Copernicus slope cost raster, blocked cells, road-gap targets
  4  Stage A vs Stage B routing  10 m strategy comparison and the 5 m zero-crossing clearance network (independent routes, shared trunk)
  5  Metrics, tables and maps    four-window comparison table in the terminal, planning maps of every window in demo_output/
Damarakunta is computed live (damarakunta_open); Adilabad, Aswaraopeta and Alampur are read from their committed results (their segmentation states live on the owner's PC).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
PY = sys.executable
OUT = REPO / "demo_output"
CACHE_ZIP = REPO / "demo_cache" / "damarakunta_open_cache.zip"
VILLAGE = "damarakunta_open"
V8 = REPO / "data" / "villages" / "damarakunta_esri" / "results" / "v8_instances" / "buildings_v8_damarakunta.gpkg"
RESULTS = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / "00_DAMARAKUNTA_OPEN_SEGMENTATION"
STAGES = ["Data & window load", "StrongDINOv2Seg segmentation & footprint extraction", "Terrain cost surface", "Stage A vs. Stage B routing", "Metrics, comparison tables & final planning maps"]
T0 = time.time()


def say(*a):
    print(*a, flush=True)


def banner(i):
    say("\n" + "=" * 100)
    say(f" [{i}/5] {STAGES[i - 1].upper()}")
    say("=" * 100)


def run(cmd, log_name, quiet=True):
    """Run a command, keep its full output in demo_output/logs/<log_name>.log and echo only its key lines."""
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    log = OUT / "logs" / f"{log_name}.log"
    t = time.time()
    with open(log, "w", encoding="utf-8") as fh:
        r = subprocess.run([str(c) for c in cmd], cwd=REPO, stdout=fh, stderr=subprocess.STDOUT, env=os.environ, timeout=900)
    if r.returncode:
        say(f"  FAILED ({log_name}, exit code {r.returncode}); last lines of {log}:")
        say("   " + "\n   ".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]))
        sys.exit(1)
    say(f"  ok: {log_name} ({time.time() - t:.0f} s)  log: {log.relative_to(REPO)}")
    return log.read_text(encoding="utf-8", errors="replace")


def cache_files():
    d = REPO / "data" / "villages" / VILLAGE
    return [f for f in d.iterdir() if f.is_file() and f.suffix in (".gpkg", ".tif")] + [V8] + sorted((REPO / "data" / "esri_cache").glob("*.png"))


def save_cache_zip():
    """Save the inputs of the window (open-data layers, clipped StrongDINOv2Seg footprints, Esri imagery tiles) as demo_cache/damarakunta_open_cache.zip: later runs are fully offline."""
    CACHE_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CACHE_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in cache_files():
            z.write(f, f.relative_to(REPO).as_posix())
    say(f"  saved {CACHE_ZIP.relative_to(REPO)} ({CACHE_ZIP.stat().st_size / 1e6:.1f} MB): the next runs of run_demo.bat are fully offline")


def restore_cache():
    """Returns True when the cache bundle has to be (re)built at the end of the run (first run on this machine)."""
    d = REPO / "data" / "villages" / VILLAGE
    need = [d / "boundary.gpkg", d / "roads.gpkg", d / "places_4km.gpkg", d / "worldcover_10m.tif", d / "dem_30m.tif", V8]
    have_img = bool(list((REPO / "data" / "esri_cache").glob("*.png")))
    if all(p.exists() for p in need) and have_img:
        say("  cached open-data inputs present (data/villages/damarakunta_open, data/villages/damarakunta_esri, data/esri_cache)")
        if not CACHE_ZIP.exists():
            save_cache_zip()
        return False
    if CACHE_ZIP.exists():
        say(f"  restoring the cached open-data inputs from {CACHE_ZIP.relative_to(REPO)} ...")
        with zipfile.ZipFile(CACHE_ZIP) as z:
            z.extractall(REPO)
        return False
    say("  FIRST RUN on this machine: no demo_cache/damarakunta_open_cache.zip -> preparing the inputs locally (needs internet once; every later run is offline)")
    run([PY, "-m", "src.multivillage.run", "--village", VILLAGE, "--steps", "acquire", "prepare", "--skip-buildings"], "1a_acquire_open_data")      # Overture / OSM roads and places, WorldCover and Copernicus tiles (window-sized downloads, a few MB)
    run([PY, "scripts/prepare_damarakunta_open_inputs.py"], "1b_footprints")                                                                          # clip the existing StrongDINOv2Seg footprints
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-open", action="store_true", help="do not open the output folder at the end")
    ap.add_argument("--online", action="store_true", help="allow the Esri imagery service for windows that are not cached")
    a = ap.parse_args()
    if not a.online:
        os.environ["DEMO_OFFLINE"] = "1"                             # master_map.esri_png: cached imagery only, never waits for the network
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    from src.multivillage import pipeline_summary as PS

    say("=" * 100)
    say(" TELANGANA RURAL ROAD PLANNING - end-to-end demo (open data only, offline from cache)")
    say(" Damarakunta is computed live; Adilabad, Aswaraopeta and Alampur come from their committed results.")
    say("=" * 100)

    # ---------------------------------------------------------------- 1
    banner(1)
    build_cache = restore_cache()
    if build_cache and not a.online:
        os.environ.pop("DEMO_OFFLINE", None)                         # first run: fetch the Esri tiles of the maps once (25 s timeout each, maps are drawn without a basemap if unreachable)
    run([PY, "-m", "src.multivillage.run", "--village", VILLAGE, "--steps", "acquire", "prepare", "--skip-buildings"], "1_open_data_state")
    say("  windows (same open layers in every window: Esri imagery, WorldCover 10 m, Copernicus GLO-30 30 m, Overture / OSM roads):")
    for k in PS.ORDER:
        p = PS.AREAS[k]["results"] / "area_profile.csv"
        import pandas as pd
        r = pd.read_csv(p).iloc[0]
        say(f"    {PS.AREAS[k]['label']:<12s} {PS.AREAS[k]['typology']:<28s} window {r.window_km2:7.2f} km2 | roads {r.roads_km:6.1f} km | mean slope {r.slope_mean_pct:.1f} %")

    # ---------------------------------------------------------------- 2
    banner(2)
    try:
        import torch  # noqa: F401
        say("  PyTorch available: the stored footprints below come from the frozen StrongDINOv2Seg checkpoint (the demo does not repeat the hours-long tiled inference).")
    except ImportError:
        say("  PyTorch / checkpoint not needed for the demo: using the stored StrongDINOv2Seg instances of the frozen checkpoint (tiled inference is not repeated).")
    run([PY, "scripts/prepare_damarakunta_open_inputs.py"], "2_footprints")
    import geopandas as gpd
    b = gpd.read_file(V8, layer="buildings")
    q = b[b.inside_village].quality_class.value_counts().to_dict()
    say(f"  Damarakunta: {len(b)} StrongDINOv2Seg instances in the mosaic, {int(b.inside_village.sum())} inside the window  {q}")
    for k in PS.ORDER[1:]:
        m = PS.collect(k)
        say(f"  {PS.AREAS[k]['label']:<12s}: {m['buildings']:,} footprints (stored StrongDINOv2Seg results), {m['gap_targets']:,} road-gap targets, {sum(m['facilities'].values())} verified facilities")

    # ---------------------------------------------------------------- 3
    banner(3)
    log = run([PY, "-m", "src.multivillage.run", "--village", VILLAGE, "--variant", "segmentation", "--footprints", V8, "--steps", "prepare", "extract"], "3_cost_surface")
    for line in log.splitlines():
        if any(t in line.lower() for t in ("houses", "gap", "blocked", "cost")):
            say("   ", line.strip()[:150])
    import numpy as np
    import rasterio
    d = REPO / "data" / "villages" / VILLAGE
    with rasterio.open(d / "worldcover_10m.tif") as s_, rasterio.open(d / "slope_10m.tif") as t_:
        lc, sl = s_.read(1), t_.read(1).astype("float32")
    names = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up", 60: "bare / sparse", 80: "water"}
    share = {names[c]: 100.0 * float((lc == c).sum()) / lc.size for c in names if (lc == c).any()}
    say("    land cover of the window area (ESA WorldCover 10 m): " + ", ".join(f"{k} {v:.0f} %" for k, v in sorted(share.items(), key=lambda t: -t[1])[:4]))
    say(f"    slope (Copernicus GLO-30 Sobel, 10 m grid): mean {np.nanmean(sl[sl > -1]):.1f} deg, cells steeper than 25 deg are blocked, building cells get a hard 3.6 m clearance")

    # ---------------------------------------------------------------- 4
    banner(4)
    run([PY, "-m", "src.multivillage.run", "--village", VILLAGE, "--variant", "segmentation", "--footprints", V8, "--steps", "route", "--quick", "--workers", "2"], "4_route_10m")
    from src.multivillage import area_scenes as AS
    sc = AS.scene_for("damarakunta", "segmentation", log=lambda *x: None)
    st = sc.stats
    say(f"  Stage A (independent least-cost routes, 5 m grid, 3.6 m clearance): {st['indep_m'] / 1000:.2f} km")
    say(f"  Stage B (shared trunk, iterative Dijkstra):                         {st['shared_m'] / 1000:.2f} km  ({100 * (1 - st['shared_m'] / st['indep_m']):.1f} % shorter)")
    say(f"  building crossings: {sum(v['routes_crossing'] for v in st['verify'].values())}  |  routes {len(sc.shared_house) if hasattr(sc.shared_house, '__len__') else 'n/a'} house segments")

    # ---------------------------------------------------------------- 5
    banner(5)
    run([PY, "-m", "src.multivillage.run", "--village", VILLAGE, "--variant", "segmentation", "--footprints", V8, "--steps", "report", "--quick"], "5a_tables")
    maps = OUT / "planning_maps"
    run([PY, "scripts/make_village_map_series.py", "--village", VILLAGE, "--esri-service", "--out-dir", maps / "damarakunta_open_demo", "--dpi", "110"], "5b_maps")
    PS.compute_area_profile("damarakunta", log=lambda *x: None)
    for k in PS.ORDER:                                                # committed master maps of the other three windows
        src = PS.AREAS[k]["maps"] / "master_satellite_planning_map.png"
        dst = maps / f"{k}_master_satellite_planning_map.png"
        if k == "damarakunta":
            src = maps / "damarakunta_open_demo" / "master_satellite_planning_map.png"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    ms = [PS.collect(k) for k in PS.ORDER]
    (OUT / "comparison_table.tex").write_text(PS.latex_table(ms), encoding="utf-8")
    say("\n" + PS.terminal_tables(ms))
    say(f"\n  outputs: {OUT}")
    say(f"    planning_maps/   master planning map of each window (+ map series of Damarakunta in damarakunta_open_demo/)")
    say(f"    comparison_table.tex, logs/")
    say(f"  Damarakunta results updated in {RESULTS.relative_to(REPO)}")
    if build_cache:
        say("")
        save_cache_zip()
    say(f"\nDEMO COMPLETE in {time.time() - T0:.0f} s - 0 errors.")
    if not a.no_open:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(OUT))                               # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(OUT)])
            elif shutil.which("xdg-open") and os.environ.get("DISPLAY"):
                subprocess.Popen(["xdg-open", str(OUT)])
        except Exception as e:                                       # the folder is only a convenience
            say("  (could not open the folder:", e, ")")


if __name__ == "__main__":
    main()
