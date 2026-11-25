#!/usr/bin/env python
"""One command, one study area: the whole pipeline from data to maps and tables, then a summary printed in the terminal.

    python scripts/run_village_pipeline.py --area alampur --workers 4          # damarakunta | adilabad | aswaraopeta | alampur
    python scripts/run_village_pipeline.py --area aswaraopeta --force          # redo stages whose outputs already exist
    python scripts/run_village_pipeline.py --area adilabad --dry-run           # print the plan, run nothing
    python scripts/run_village_pipeline.py --area alampur --stages 5 6         # only some stages
    python scripts/run_village_pipeline.py --compare-all                       # 4-area table from the finished results + paper_eris/paper_comparison_table.tex

It wraps the verified modules (nothing is re-implemented here):
  Stage 1  data and tiles       scripts/run_village_end_to_end.py --stage open | esri | mosaic   (study polygon, Overture / OSM roads, ESA WorldCover, Copernicus DEM, Esri 0.6 m mosaic); cached unless --force
  Stage 2  segmentation         run_village_end_to_end.py --stage infer   StrongDINOv2Seg, tile 560, stride 420, margin 70 -> pred_classes_full.tif, building_prob_full.tif   (cached unless --force)
  Stage 3  footprints           run_village_end_to_end.py --stage extract   scripts/extract_buildings_v8.py (distance transform, h-maxima, marker-controlled flooding, neck ratio 0.65)
  Stage 4  facilities           audited table configs/multivillage/villages/<id>_verified_facilities.csv (scripts/audit_facilities.py; rows with use_in_analysis = True); the audit runs only if the table is missing or --refresh-audit
  Stage 5  routing              10 m cost surface with the soft footprint penalty (run_village_end_to_end.py --stage route) and the 5 m zero-crossing clearance network
                                (src/multivillage/clearance.py: 3.6 m clearance, Stage A independent routes, Stage B shared network; computed by --stage report)
  Stage 6  maps and tables      --stage report (tables, sat_map panels, master map), scripts/make_village_map_series.py (map1-map5, master_satellite_planning_map.png), scripts/build_final_project_outputs.py
Damarakunta (Stage B) is frozen: stages 1-3 only VERIFY the existing inputs and results (nothing in DELIVERABLES_DAMARAKUNTA_STAGE_B/ is written); stage 5 runs scripts/make_damarakunta_master_map.py.
Stage 2 needs PyTorch and the checkpoint (your PC); without them the stage stops with a clear message unless predictions already exist.
The summary tables are read from the result files; the PMGSY cost is illustrative (km x the owner-supplied, unverified rate in inputs/economic_assumptions.json).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from src.multivillage import pipeline_summary as PS      # noqa: E402

PY = sys.executable
E2E = str(REPO / "scripts" / "run_village_end_to_end.py")
STAGE_NAMES = {1: "data and tile acquisition / verification", 2: "semantic segmentation (StrongDINOv2Seg)", 3: "building footprint extraction", 4: "verified facility table",
               5: "cost surface and zero-crossing clearance routing (Stage A / Stage B)", 6: "maps, figures, summary export"}


def say(*a):
    print(*a, flush=True)


def run(cmd: list, dry: bool, what: str) -> int:
    say(f"  $ {' '.join(str(c) for c in cmd)}")
    if dry:
        return 0
    r = subprocess.run([str(c) for c in cmd], cwd=REPO)
    if r.returncode:
        sys.exit(f"STOPPED: {what} failed (exit code {r.returncode}); fix it and re-run, finished stages are skipped.")
    return 0


class Run:
    def __init__(self, a):
        self.a = a
        self.area = PS.AREAS[a.area]
        self.cid = self.area["config"]
        self.slug = self.area["slug"]
        self.work = REPO / "data" / "villages" / f"{self.slug}_esri" if self.cid else None
        self.data = REPO / "data" / "villages" / self.cid if self.cid else None
        self.frozen = self.cid is None

    def e2e(self, stage: str, extra: list | None = None):
        cmd = [PY, E2E, "--village", self.cid, "--stage", stage, "--workers", self.a.workers]
        if self.a.force:
            cmd.append("--force")
        if self.a.quick and stage in ("route", "report"):
            cmd.append("--quick")
        return cmd + (extra or [])


def stage1(r: Run):
    a = r.a
    if r.frozen:
        root = REPO / "Siddipet" / "Damarakunta"
        need = [root / "study_area/damarakunta_boundary.gpkg", root / "reference/tgrac_road_network.gpkg", root / "results/v8_instances/buildings_v8_full.gpkg", root / "aligned_open/worldcover_10m.tif", root / "aligned_open/dem_30m.tif"]
        for p in need:
            say(f"  {'OK     ' if p.exists() else 'MISSING'} {p.relative_to(REPO)}")
        mos = root / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
        say(f"  {'OK     ' if mos.exists() else 'absent '} {mos.relative_to(REPO)}  (PC only; without it the master map has a grey background)")
        return
    if not (r.data / "state.pkl").exists() or a.force:
        run(r.e2e("open", ["--from-cache"] if not a.force else []), a.dry_run, "open-data stage")
    else:
        say("  open data cached (data/villages/%s/state.pkl) -> skip" % r.cid)
    if not any((r.work / "esri_tiles").glob("*.tif")) or a.force:
        run(r.e2e("esri"), a.dry_run, "Esri tile download")
    else:
        say("  Esri tiles cached -> skip")
    mos = r.work / "aligned" / f"{r.slug}_esri_highres_mosaic_0p6m.tif"
    if not mos.exists() or a.force:
        run(r.e2e("mosaic"), a.dry_run, "mosaic")
    else:
        say(f"  mosaic cached ({mos.name}) -> skip")
    if not a.dry_run:
        PS.compute_area_profile(a.area, log=say)


def stage2(r: Run):
    a = r.a
    if r.frozen:
        say("  Damarakunta: the Stage B segmentation (tiled_v1 predictions) is frozen -> nothing to run")
        return
    cls = r.work / "predictions" / "pred_classes_full.tif"
    if cls.exists() and not a.force:
        say(f"  predictions cached ({cls.name}, building_prob_full.tif) -> skip")
        return
    say("  tiled inference: tile 560, stride 420, margin 70 (needs PyTorch and best_model.pth on this machine)")
    run(r.e2e("infer", ["--device", a.device]), a.dry_run, "segmentation inference (PyTorch + checkpoint required)")


def stage3(r: Run):
    a = r.a
    if r.frozen:
        say("  Damarakunta: v8 footprints are frozen (Siddipet/Damarakunta/results/v8_instances/buildings_v8_full.gpkg) -> nothing to run")
        return
    v8 = r.work / "results" / "v8_instances" / f"buildings_v8_{r.slug}.gpkg"
    if v8.exists() and not a.force:
        say(f"  footprints cached ({v8.name}) -> skip")
        return
    run(r.e2e("extract"), a.dry_run, "footprint extraction")


def stage4(r: Run):
    a = r.a
    cid = r.cid or "damarakunta"
    f = REPO / "configs" / "multivillage" / "villages" / f"{cid}_verified_facilities.csv"
    if a.refresh_audit or not f.exists():
        run([PY, REPO / "scripts" / "audit_facilities.py", "--village", cid], a.dry_run, "facility audit")
    counts = PS.facility_counts(a.area)
    say(f"  audited facility table {f.relative_to(REPO)}: " + (", ".join(f"{k} {v}" for k, v in counts.items()) + f" (total {sum(counts.values())}; use_in_analysis = True)" if counts else "not found"))


def stage5(r: Run):
    a = r.a
    if r.frozen:
        run([PY, REPO / "scripts" / "make_damarakunta_master_map.py"], a.dry_run, "Damarakunta clearance routing + master map")
        return
    run(r.e2e("route"), a.dry_run, "10 m routing on the segmentation footprints (extract + route)")
    say("  the 5 m clearance network (Stage A / Stage B, 3.6 m footprint clearance) is planned in stage 6 by --stage report (cached; re-planned when targets or facilities change)")


def stage6(r: Run):
    a = r.a
    if not r.frozen:
        run(r.e2e("report"), a.dry_run, "report stage (tables, satellite panels, clearance network, master map)")
        run([PY, REPO / "scripts" / "make_village_map_series.py", "--village", r.cid], a.dry_run, "map series")
    run([PY, REPO / "scripts" / "build_final_project_outputs.py"], a.dry_run, "FINAL_PROJECT_OUTPUTS builder")


STAGES = {1: stage1, 2: stage2, 3: stage3, 4: stage4, 5: stage5, 6: stage6}


def compare_all(write_tex: bool = True, refresh_profile: bool = False):
    ms = []
    for k in PS.ORDER:
        if refresh_profile or not (PS.AREAS[k]["results"] / "area_profile.csv").exists():
            try:
                PS.compute_area_profile(k, log=lambda *x: None)
            except Exception as e:                                           # data not on this machine
                say(f"  (profile of {k} not recomputed: {type(e).__name__})")
        ms.append(PS.collect(k))
    say("\n" + PS.terminal_tables(ms))
    out = REPO / "paper_eris" / "paper_comparison_table.tex"
    if write_tex:
        out.write_text(PS.latex_table(ms), encoding="utf-8")
        say(f"\nwrote {out.relative_to(REPO)} ({sum(1 for m in ms for v in m.values() if v is None)} missing values shown as \\pending{{n/a}})")
    return ms


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", choices=PS.ORDER, help="study area")
    ap.add_argument("--workers", default="4", help="parallel planner jobs (10 m route stage)")
    ap.add_argument("--force", action="store_true", help="redo stages whose outputs are cached")
    ap.add_argument("--quick", dest="quick", action="store_true", default=True, help="10 m routing: main strategy comparison only (default)")
    ap.add_argument("--full-sweeps", dest="quick", action="store_false", help="also run the penalty / omission / target-definition sweeps (hours)")
    ap.add_argument("--stages", nargs="+", type=int, choices=sorted(STAGES), help="run only these stages (default 1-6)")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--refresh-audit", action="store_true", help="stage 4: re-run scripts/audit_facilities.py even if the verified table exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the commands, run nothing")
    ap.add_argument("--compare-all", action="store_true", help="print the 4-area comparison and write paper_eris/paper_comparison_table.tex")
    ap.add_argument("--no-summary", action="store_true", help="do not print the summary tables at the end")
    a = ap.parse_args()
    if a.compare_all:
        compare_all(refresh_profile=a.force)
        return
    if not a.area:
        ap.error("--area is required (or use --compare-all)")
    r = Run(a)
    t0 = time.time()
    say(f"AREA {r.area['label']} ({r.area['typology']}, {r.area['district']}){'  [Stage B frozen]' if r.frozen else ''}")
    for n in (a.stages or sorted(STAGES)):
        say(f"\n=== Stage {n}: {STAGE_NAMES[n]} ===")
        STAGES[n](r)
    if a.dry_run:
        say("\n(dry run: nothing was executed)")
        return
    say(f"\nfinished in {time.time() - t0:.0f} s")
    if not a.no_summary:
        say("\n" + PS.terminal_tables([PS.collect(a.area)]))
        say("\nCompare all four areas: python scripts/run_village_pipeline.py --compare-all")


if __name__ == "__main__":
    main()
