"""Phase-1 workspace cleanup. Nothing is deleted: legacy items are MOVED to archive/<batch>/<original relative path>,
every move is logged (with SHA-256 for files) in archive/<batch>/MOVE_LOG.csv, and restore_from_archive.py reverses it.
Core Stage B scripts stay in scripts/ and are COPIED into src/<group>/ (originals are archived only in phase 2).

usage:  python src/tools/cleanup_phase1.py --dry-run     (writes the plan, moves nothing)
        python src/tools/cleanup_phase1.py --execute
"""
import csv, hashlib, os, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = "2026-10-30_phase1"
ARCH = ROOT / "archive" / BATCH
SC = ROOT / "scripts"
RES = ROOT / "Siddipet" / "Damarakunta" / "results"

# ------------------------------------------------------------------ core scripts -> src groups
CORE = {
    "preprocessing": ["save_damarakunta_boundary", "query_damarakunta_cadastral", "save_damarakunta_cadastral", "repair_damarakunta_cadastral",
                      "prepare_damarakunta_priority_facilities", "prepare_damarakunta_terrain", "clip_village_dem", "clip_worldcover",
                      "fill_slope_nodata", "reproject_worldcover", "align_damarakunta_terrain", "create_damarakunta_cost_surface",
                      "audit_damarakunta_masks", "dk_boundary_crs_compare_v1", "dk_stageA_prepare_r3"],
    "modeling": ["extract_buildings_v8", "run_tiled_inference", "run_damarakunta_inference", "mosaic_esri_damarakunta", "export_esri_damarakunta_full",
                 "prepare_damarakunta_esri_model_tiles"],
    "routing": ["plan_network_v2", "dk_stageB_run_v1_1", "dk_stageB_run_v1_2", "dk_stageB_run_v1_3"],
    "stress_test": ["dk_stageB_c1_c07", "dk_stageB_c1_compare_v2", "dk_stageB_c1_diag_facility", "dk_stageB_c1_diag_facility_costs_v2",
                    "dk_stageB_c1_footprint_eval_v1", "dk_stageB_c1_omitted_exposure_v1", "dk_stageB_c1_report_v4", "dk_stageB_c1_test_c07",
                    "dk_stageB_c1_test_footprint_eval", "dk_stageB_c2_ablation_summary_v1", "dk_stageB_compare"],
    "validation": ["dk_stageB_validate", "dk_stageB_connectivity_audit_v2", "dk_stageB_connectivity_audit_v2_tests", "dk_stageB_connectivity_diagnostic_v1",
                   "dk_stageB_chain_cell_reasons_v1", "dk_stageB_boundary_mask_diag_v1", "dk_stageB_c0002_roadcell_diag_v1",
                   "dk_stageB_road_component_boundary_diag_v1", "dk_stageB_run_repro_compare_v1", "dk_stageB_final_tables", "test_plan_network_v2"],
    "reporting": ["dk_stageB_maps_v2", "Damarakunta_Final_Map_v4_1", "Damarakunta_Settlement_Detail_Maps"],
}
ROOT_ARCHIVE = ["1", "SLOPE_LIMIT_DEG", "--layers-json", "full1_after.txt", "full1_before.txt", "run5_after.txt", "run5_before.txt", "run6_after.txt",
                "run6_before.txt", "newfunc.py", "patch_detail.py", "__pycache__", "temp_claude_review", "layers_pinned.json", "source_file_report.txt",
                "generate_damarakunta_access_routes_review.txt", "view_footprints.py", "Damarakunta_Settlement_Detail_Maps.py", "archive_cleanup",
                "strongdinov2seg_training_updated (2).py", "logs", "DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024.md",
                "DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024_v2.md", "tests"]
RES_KEEP = {"run_20261029_01", "individual_house_network_v1", "individual_house_routing_v1", "v8_instances", "final_output_validation_v4_1",
            "final_output_validation_v4_1_cartography", "final_output_validation_v4_1_cartography_e4", "final_output_validation_v4_1_cartography_partial_run1",
            "final_output_validation_v4_1.zip", "stageA_input_validation", "stageA2_provenance_alignment", "independent_verification_audit_draft1",
            "project_inventory_phase1", "verification_chips_draft1", "damarakunta_verification_chips.zip"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(execute):
    core_files = {}
    for grp, names in CORE.items():
        for n in names:
            p = SC / (n + ".py")
            if not p.exists():
                print("WARNING core script missing:", n)
                continue
            core_files[p.name] = grp
    # closure: any script mentioned (by file name) inside a kept script stays
    all_py = {p.name: p for p in SC.glob("*.py")}
    changed = True
    while changed:
        changed = False
        for name in list(core_files):
            txt = all_py[name].read_text(encoding="utf-8", errors="ignore")
            for other in all_py:
                if other not in core_files and re.search(r"(?<![A-Za-z0-9_])" + re.escape(other[:-3]) + r"(?![A-Za-z0-9_])", txt):
                    core_files[other] = "dependency"
                    print("closure keeps", other, "(mentioned by", name + ")")
                    changed = True
    plan = []   # (kind, src, dst, reason)
    for it in sorted(SC.iterdir()):
        if it.name in core_files:
            continue
        if it.name in ("damarakunta.json",):   # config next to scripts, referenced by pipeline
            continue
        plan.append(("move", it, ARCH / it.relative_to(ROOT), "legacy script/support file (not in verified Stage B chain)"))
    for n in ROOT_ARCHIVE:
        p = ROOT / n
        if p.exists() or p.is_symlink():
            plan.append(("move", p, ARCH / n, "root clutter / superseded"))
    for it in sorted(RES.iterdir()):
        if it.name not in RES_KEEP:
            plan.append(("move", it, ARCH / it.relative_to(ROOT), "legacy result (not referenced by run_20261029_01 manifests)"))
    for p in ROOT.glob("*.py"):      # stray root scripts not already listed
        if p.name not in ROOT_ARCHIVE:
            plan.append(("move", p, ARCH / p.name, "stray root script"))

    ARCH.mkdir(parents=True, exist_ok=True)
    with open(ARCH / "PLAN.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["action", "source", "destination", "reason"])
        for k, s, d, r in plan: w.writerow([k, s.relative_to(ROOT), d.relative_to(ROOT), r])
        for name, grp in sorted(core_files.items()): w.writerow(["copy", "scripts/" + name, "src/%s/%s" % (grp if grp != "dependency" else "legacy_dependencies", name), "core"])
    print("planned moves:", len(plan), "| core copies:", len(core_files))
    if not execute:
        return
    log = open(ARCH / "MOVE_LOG.csv", "w", newline="", encoding="utf-8"); lw = csv.writer(log)
    lw.writerow(["original", "archived", "type", "sha256_if_file"])
    for k, s, d, r in plan:
        d.parent.mkdir(parents=True, exist_ok=True)
        isdir = s.is_dir()
        digest = "" if isdir else sha(s)
        shutil.move(str(s), str(d))
        lw.writerow([s.relative_to(ROOT), d.relative_to(ROOT), "dir" if isdir else "file", digest])
    log.close()
    for name, grp in core_files.items():
        tgt = ROOT / "src" / (grp if grp != "dependency" else "legacy_dependencies")
        tgt.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SC / name, tgt / name)
    # the training script lives at the root name with " (2)"; copy it under a clean name
    tr = ARCH / "strongdinov2seg_training_updated (2).py"
    if tr.exists():
        (ROOT / "src" / "modeling").mkdir(parents=True, exist_ok=True)
        shutil.copy2(tr, ROOT / "src" / "modeling" / "strongdinov2seg_training_updated.py")
    print("done")


if __name__ == "__main__":
    main("--execute" in sys.argv)
