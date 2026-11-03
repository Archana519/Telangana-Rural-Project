"""Final output package for the dissertation: verification, connectivity resolution, four maps, comparison tables and the thesis chapter.

    python src/run_final_package.py                    # uses the newest passing pipeline run in outputs/
    python src/run_final_package.py --run-id run_20261030_202603

Run `python src/run_pipeline.py --profile full` first (it creates the run this reads). Nothing here re-plans routes or changes the planner.
Writes: outputs/verification, outputs/connectivity, outputs/final_maps, outputs/final_comparison, outputs/final_package.
"""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenario_names as SN
SRC = ROOT / "src"


def newest_passing():
    for d in sorted((ROOT / "outputs").glob("run_*"), reverse=True):
        s = d / "RUN_SUMMARY.md"
        if s.exists() and "Status: **PASS**" in s.read_text(encoding="utf-8"):
            return d.name
    raise SystemExit("no passing pipeline run found in outputs/; run src/run_pipeline.py first")


def step(name, cmd):
    print("==", name, flush=True)
    p = subprocess.run([str(c) for c in cmd], cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print(p.stdout[-1500:], p.stderr[-2500:])
        raise SystemExit("FAILED: %s" % name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default=None)
    a = ap.parse_args()
    rid = a.run_id or newest_passing()
    sb = ROOT / "Siddipet" / "Damarakunta" / "results" / rid / "stageB"
    prim = sb / SN.PRIMARY
    avoid = sb / SN.AVOID
    O = ROOT / "outputs"
    print("run:", rid)
    import shutil
    for d in ("verification", "connectivity", "visual_audit", "final_maps", "final_comparison", "final_package"):   # always rebuilt from the chosen run: no stale files
        shutil.rmtree(O / d, ignore_errors=True)
    step("detection and facility verification", [PY, SRC / "validation" / "verify_detections.py", "--out", O / "verification"])
    step("connectivity resolution (road-line topology)", [PY, SRC / "validation" / "connectivity_resolution.py", "--run-dir", prim, "--out", O / "connectivity"])
    step("visual audit protocol (table, KML, crops)", [PY, SRC / "validation" / "visual_audit_protocol.py", "--out", O / "visual_audit"])
    step("economic and material impact (illustrative)", [PY, SRC / "reporting" / "economic_impact.py", "--stageb-root", sb, "--out", O / "final_comparison"])
    step("final maps 1-5", [PY, SRC / "reporting" / "make_final_maps.py", "--run-dir", prim, "--avoid-run-dir", avoid, "--out", O / "final_maps"])
    runs_x = [sb / n for n in (SN.PRIMARY, SN.P3)] + sorted(sb.glob(SN.AVOID_PREFIX + "*"))
    step("building crossing diagnostic", [PY, SRC / "validation" / "building_crossing_diagnostic.py", "--runs"] + runs_x + ["--out", O / "final_comparison"])
    step("comparison tables", [PY, SRC / "reporting" / "comparison_tables.py", "--stageb-root", sb, "--out", O / "final_comparison"])
    step("charts", [PY, SRC / "reporting" / "make_charts.py", "--stageb-root", sb, "--comparison", O / "final_comparison", "--out", O / "final_comparison" / "charts"])
    step("thesis chapter", [PY, SRC / "reporting" / "make_chapter.py", "--stageb-root", sb, "--run-id", rid])
    idx = ["# Final output package", "", "Built from pipeline run `%s`. Review drafts: maps containing imagery carry the imagery-licence caution." % rid, "",
           "| # | Item | Location |", "|---|---|---|",
           "| 1 | Detection and facility verification (agreement, not accuracy) | `outputs/verification/` |",
           "| 2 | Connectivity resolution on road lines (C0002) | `outputs/connectivity/` |",
           "| 3 | Map 1 imagery, boundary, roads | `outputs/final_maps/map1_imagery_boundary_roads.png` |",
           "| 6b | Map 5 village-level detail, primary versus building-avoiding network | `outputs/final_maps/map5_village_detail_shared_paths.png` |",
           "| 7c | Charts 1-5 (lengths, materials, cost, accessibility, avoidance trade-off) | `outputs/final_comparison/charts/` |",
           "| 4 | Map 2 footprints and facilities with latitude/longitude | `outputs/final_maps/map2_footprints_facilities_latlon.png` |",
           "| 5 | Map 3 terrain, cost, land cover, slope | `outputs/final_maps/map3_terrain_cost_landcover_slope.png` |",
           "| 6 | Map 4 alternatives versus final network | `outputs/final_maps/map4_alternatives_vs_network.png` |",
           "| 7 | Comparison tables incl. Table 5 economic and material impact (CSV and Markdown) | `outputs/final_comparison/` |",
           "| 7b | Visual audit protocol, Visual Grounding Table, Google Earth KML, crops | `outputs/visual_audit/` |",
           "| 8 | Thesis chapter | `outputs/final_package/THESIS_CHAPTER_RESULTS_AND_VALIDATION.md` |",
           "| - | Stage 1-5 pipeline results and per-route explanations | `outputs/%s/` |" % rid, ""]
    (O / "final_package" / "INDEX.md").write_text("\n".join(idx), encoding="utf-8")
    print("done:", O / "final_package")


if __name__ == "__main__":
    main()
