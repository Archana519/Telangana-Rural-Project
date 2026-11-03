"""rebuild_deliverables.py - RECONSTRUCTS DELIVERABLES_DAMARAKUNTA_STAGE_B after the original folder was lost.

The original (155 files, never committed to git) cannot be recovered. This script rebuilds the same folder layout from:
  * live result files (reference run run_20261029_01 and the newest pipeline run in outputs/),
  * the current scripts and inputs (hashes recomputed),
  * the text of the original documents as they were displayed earlier in this working session (reconstructed, updated where the evidence has since changed).
Every document carries a RECONSTRUCTION notice. Nothing here is the original file, and no result was changed.
usage: python src/tools/rebuild_deliverables.py [--run-id run_20261030_231109]
"""
import argparse, csv, hashlib, json, shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
REF = V / "results" / "run_20261029_01" / "stageB"
PRIM = None   # set in main(): the final_x4 run of the chosen pipeline run
OUT = ROOT / "DELIVERABLES_DAMARAKUNTA_STAGE_B"
NOTICE = ("> **RECONSTRUCTION (%s).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the "
          "original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.\n\n" % datetime.now().strftime("%Y-%m-%d"))
manifest = []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def put(rel, text, md=True):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text((NOTICE if md else "") + text, encoding="utf-8")
    manifest.append((rel, "generated", ""))


def cp(src, rel):
    src = Path(src)
    if not src.exists():
        return
    dst = OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
        for f in dst.rglob("*"):
            if f.is_file():
                manifest.append((str(f.relative_to(OUT)).replace("\\", "/"), "copied", str(src)))
    else:
        shutil.copy2(src, dst)
        manifest.append((rel, "copied", str(src)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="run_20261030_231109")
    a = ap.parse_args()
    if OUT.exists():
        raise SystemExit("%s exists; refusing to overwrite" % OUT)
    global PRIM
    new = ROOT / "outputs" / a.run_id
    NEWSB = V / "results" / a.run_id / "stageB"
    PRIM = NEWSB / "S2_fac_C0_s25_final_x4"
    P3R = NEWSB / "S2_fac_C0_s25_final_x1"
    ev = json.load(open(PRIM / "evaluation_summary.json", encoding="utf-8"))
    ev3 = json.load(open(P3R / "evaluation_summary.json", encoding="utf-8"))

    # ---------------------------------------------------------------- copies of live results
    for f in ("evaluation_summary.json", "selection_summary.csv", "route_edges.csv", "route_alternatives.csv", "shared_edge_accounting.csv", "shared_edge_per_target.csv",
              "connectivity_checks.csv", "road_components.csv", "target_status.csv", "scenario_targets.csv", "facility_status.csv", "impact_flags.csv", "baselines.csv", "evaluation_by_stratum.csv", "config_stageB.json"):
        cp(PRIM / f, "03_RESULTS_TABLES/PRIMARY_RUN_S2_fac_C0_s25_final_x4/" + f)
    cp(REF / "_c1_report_v4", "03_RESULTS_TABLES/C1_SEGMENTATION_SENSITIVITY")
    cp(REF / "_final_main", "03_RESULTS_TABLES/UNCERTAINTY")
    cp(REF / "_c2_abl_v1", "03_RESULTS_TABLES/C2_ROUTE_SELECTION_ABLATION")
    cp(NEWSB / "_connectivity_audit_v2", "03_RESULTS_TABLES/CONNECTIVITY/connectivity_audit_v2")
    cp(ROOT / "outputs" / "connectivity", "03_RESULTS_TABLES/CONNECTIVITY/line_topology_resolution")
    cp(ROOT / "outputs" / "final_comparison", "03_RESULTS_TABLES/COMPARISON_TABLES")
    cp(ROOT / "outputs" / "final_comparison" / "charts", "03_RESULTS_TABLES/CHARTS")
    cp(ROOT / "outputs" / "verification", "04_VALIDATION/DETECTION_AND_FACILITY_VERIFICATION")
    cp(ROOT / "outputs" / "visual_audit", "04_VALIDATION/VISUAL_AUDIT_KIT")
    cp(ROOT / "outputs" / "final_package" / "THESIS_CHAPTER_RESULTS_AND_VALIDATION.md", "00_START_HERE/THESIS_CHAPTER_RESULTS_AND_VALIDATION.md")
    cp(ROOT / "inputs" / "EXCLUSIONS.md", "00_START_HERE/EXCLUSIONS.md")
    cp(ROOT / "inputs" / "ADMIN_UTILITIES.md", "00_START_HERE/ADMIN_UTILITIES.md")
    cp(ROOT / "inputs" / "admin_utilities_intake.csv", "00_START_HERE/admin_utilities_intake.csv")
    cp(NEWSB / "_validation_main", "04_VALIDATION/MAIN_RUN/validation_main")
    cp(PRIM / "acceptance_tests.csv", "04_VALIDATION/MAIN_RUN/acceptance_tests_primary.csv")
    cp(P3R / "acceptance_tests.csv", "04_VALIDATION/MAIN_RUN/acceptance_tests_P3.csv")
    cp(REF / "_c1_report_v4" / "report_validation.csv", "04_VALIDATION/C1/report_validation.csv")
    cp(REF / "_c2_abl_v1" / "c2_ablation_validation.csv", "04_VALIDATION/C2/c2_ablation_validation.csv")
    for f in ("inputs_manifest_stageB.csv", "outputs_manifest.csv"):
        cp(PRIM / f, "04_VALIDATION/INPUT_OUTPUT_MANIFESTS/" + f)
    cp(V / "results" / "run_20261029_01" / "stageA" / "inputs_manifest.csv", "04_VALIDATION/INPUT_OUTPUT_MANIFESTS/stageA_inputs_manifest.csv")
    cp(V / "results" / "run_20261029_01" / "stageA" / "stageA_checks.txt", "04_VALIDATION/INPUT_OUTPUT_MANIFESTS/stageA_checks.txt")
    cp(ROOT / "docs" / "DAMARAKUNTA_STAGE_A_INPUT_VALIDATION.md", "04_VALIDATION/INPUT_OUTPUT_MANIFESTS/DAMARAKUNTA_STAGE_A_INPUT_VALIDATION.md")
    # diagnostics, C1, C2 and the reference-run copies below come from the verified 4-facility baseline run and are not scrubbed (inputs/EXCLUSIONS.md)
    cp(REF / "_boundary_mask_diag_v1", "05_DIAGNOSTICS/BOUNDARY_AND_ROADS/boundary_mask_diag_v1")
    cp(REF / "_chain_cell_reasons_v1", "05_DIAGNOSTICS/CHAIN_CELL_REASONS")
    cp(NEWSB / "_connectivity_audit_v2" / "connectivity_exceptions.csv", "05_DIAGNOSTICS/CONNECTIVITY_EXCEPTIONS/connectivity_exceptions.csv")
    cp(REF / "_road_component_boundary_diag_v1", "05_DIAGNOSTICS/ROAD_COMPONENTS/road_component_boundary_diag_v1")
    cp(REF / "_c0002_roadcell_diag_v1", "05_DIAGNOSTICS/ROAD_COMPONENTS/c0002_roadcell_diag_v1")
    if (ROOT / "outputs" / "final_maps").exists():
        cp(ROOT / "outputs" / "final_maps", "02_FINAL_MAPS/final_maps_1_to_5")
    arch_png = ROOT / "Phase1_Report_CBIT_Format" / "assets" / "fig_arch_v2.png"
    cp(arch_png, "01_ARCHITECTURE/ARCHITECTURE_DIAGRAM.png")
    cp(ROOT / "Phase1_Report_CBIT_Format" / "assets" / "fig_flow_v2.png", "01_ARCHITECTURE/WORKFLOW_DIAGRAM.png")
    keep = ["align_damarakunta_terrain", "audit_damarakunta_masks", "create_damarakunta_cost_surface", "dk_boundary_crs_compare_v1", "dk_stageA_prepare_r3", "dk_stageB_boundary_mask_diag_v1",
            "dk_stageB_c0002_roadcell_diag_v1", "dk_stageB_c1_report_v4", "dk_stageB_c2_ablation_summary_v1", "dk_stageB_chain_cell_reasons_v1", "dk_stageB_connectivity_audit_v2",
            "dk_stageB_connectivity_audit_v2_tests", "dk_stageB_connectivity_diagnostic_v1", "dk_stageB_final_tables", "dk_stageB_maps_v2", "dk_stageB_road_component_boundary_diag_v1",
            "dk_stageB_run_repro_compare_v1", "dk_stageB_run_v1_1", "dk_stageB_run_v1_2", "dk_stageB_run_v1_3", "dk_stageB_run_v1_4", "dk_stageB_run_v1_5", "dk_stageB_run_v1_6", "dk_stageB_validate", "plan_network_v2", "test_plan_network_v2"]
    rows = []
    for k in keep:
        p = ROOT / "scripts" / (k + ".py")
        if p.exists():
            cp(p, "06_REPRODUCIBILITY/scripts_snapshot/" + p.name)
            rows.append((p.name, sha(p)))
    with open(OUT / "06_REPRODUCIBILITY" / "SCRIPT_HASHES.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["script", "sha256_current"]); w.writerows(rows)
    man = list(csv.DictReader(open(PRIM / "inputs_manifest_stageB.csv", encoding="utf-8")))
    with open(OUT / "06_REPRODUCIBILITY" / "INPUT_HASHES.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["role", "path", "sha256_in_reference_manifest", "sha256_now", "equal"])
        for r in man:
            p = Path(r["path"])
            now = sha(p) if p.exists() else "MISSING"
            w.writerow([r["role"], r["path"], r["sha256"], now, now == r["sha256"]])

    # map file check
    import pymupdf
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with open(OUT / "02_FINAL_MAPS" / "MAP_FILE_CHECK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["file", "kind", "pixels", "dpi", "pages", "valid", "page_size"])
        for p in sorted((OUT / "02_FINAL_MAPS").rglob("*")):
            rel = str(p.relative_to(OUT)).replace("\\", "/")
            if p.suffix.lower() == ".png":
                im = Image.open(p)
                w.writerow([rel, "PNG", "%dx%d" % im.size, im.info.get("dpi", ""), "", "readable", ""])
            elif p.suffix.lower() == ".pdf":
                d = pymupdf.open(p)
                w.writerow([rel, "PDF", "", "", len(d), "readable", "%g x %g pts" % (d[0].rect.width, d[0].rect.height)])

    # results index (read from the evaluation summaries)
    ri = [("final x4 (5 facilities): house unique length (m)", ev["houses_primary"]["unique_len_m"], "PRIMARY_RUN/evaluation_summary.json"),
          ("final x4 (5 facilities): facility unique length (m)", ev["facilities_primary"]["unique_len_m"], "PRIMARY_RUN/evaluation_summary.json"),
          ("final x4 (5 facilities): combined unique length (m)", ev["combined_primary"]["unique_len_m"], "PRIMARY_RUN/evaluation_summary.json"),
          ("final x4 (5 facilities): combined unique ordinal cost", ev["combined_primary"]["unique_cost"], "PRIMARY_RUN/evaluation_summary.json"),
          ("final x4 (5 facilities): independent baseline house unique length (m)", ev["houses_independent_baseline"]["unique_len_m"], "PRIMARY_RUN/evaluation_summary.json"),
          ("final x4 (5 facilities): roads-only reference house unique length (m)", ev["houses_roads_only_reference"]["unique_len_m"], "PRIMARY_RUN/evaluation_summary.json"),
          ("final x1 (5 facilities): house unique length (m)", ev3["houses_primary"]["unique_len_m"], "S2_fac_C0_s25_final_x1/evaluation_summary.json"),
          ("final x1 (5 facilities): facility unique length (m)", ev3["facilities_primary"]["unique_len_m"], "S2_fac_C0_s25_final_x1/evaluation_summary.json"),
          ("final x1 (5 facilities): combined unique ordinal cost", ev3["combined_primary"]["unique_cost"], "S2_fac_C0_s25_final_x1/evaluation_summary.json"),
          ("targets reaching the main road component (raster) / routed", "%d / %d" % (ev["connectivity"]["reach_main_component"], ev["connectivity"]["routed_total"]), "PRIMARY_RUN/connectivity_checks.csv")]
    (OUT / "00_START_HERE").mkdir(parents=True, exist_ok=True)
    with open(OUT / "00_START_HERE" / "RESULTS_INDEX.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["metric", "value", "source"]); w.writerows(ri)
    manifest.append(("00_START_HERE/RESULTS_INDEX.csv", "generated", ""))

    # ---------------------------------------------------------------- reconstructed documents
    put("00_START_HERE/README_PROJECT_OVERVIEW.md", """# Damarakunta Stage B: deliverables package (reconstruction)

Case study: GIS and remote-sensing based smart-village road planning, Damarakunta, Markook mandal, Siddipet, Telangana.
Planning results on a 10 m grid (EPSG:32644). Routes are unverified planning alternatives, not roads. Costs are ordinal planning units, not rupees.
No field validation, legal access, ownership, drainage, road width or construction cost is established. The completion gate is **not approved** and C3 (five other villages) has **not started**.

| Folder | Content |
|---|---|
| 00_START_HERE | this file, `COMPLETION_GATE.md`, `EXECUTION_STATUS.md`, `RESULTS_INDEX.csv`, `GENERATED_FILES.csv`, `COPY_MANIFEST.csv` |
| 01_ARCHITECTURE | architecture and workflow diagrams, data and process flow |
| 02_FINAL_MAPS | the five final maps, `MAP_FILE_CHECK.csv` |
| 03_RESULTS_TABLES | primary (final x4) tables, comparison tables, charts 1-5, connectivity, and the verified-baseline C1, C2 and uncertainty tables |
| 04_VALIDATION | acceptance tests, validator results, manifests, detection and facility verification, visual audit kit |
| 05_DIAGNOSTICS | boundary, road-component and chain-cell diagnostics |
| 06_REPRODUCIBILITY | commands, input and script hashes, script snapshot, P3 reproduction note |
| 07_LIMITATIONS_AND_OPEN_ISSUES | limitations and unresolved issues, `METHODOLOGICAL_LIMITATIONS_AND_FUTURE_SCOPE.md` (data terms, field validation, C3) |
| 08_SOURCE_REFERENCES | data sources and licence status |

The final scenarios exclude the anganwadi (`00_START_HERE/EXCLUSIONS.md`); the verified 4-facility baseline run is kept only as reproduction evidence (C1, C2, uncertainty and diagnostics below come from it and are not scrubbed).

Run everything again with `python src/run_pipeline.py --profile full` and `python src/run_final_package.py` (see `CLEANUP_PHASE1_REPORT.md` in `docs/`).
""")
    put("00_START_HERE/EXECUTION_STATUS.md", """# Execution status

| Stage | Status | Evidence |
|---|---|---|
| 1 Detect (building candidates, facilities) | Reused input, verified by hash; detections unverified | `inputs/METADATA.md`, `outputs/verification/` |
| 2 Model terrain (10 m grid, cost surface) | Verified input | `04_VALIDATION/INPUT_OUTPUT_MANIFESTS/` |
| 3 Plan (Stage A alternatives, Stage B selection) | Run and reproduced exactly in fresh runs (27 reference runs, 405 metrics identical) | `outputs/run_*/RUN_SUMMARY.md` |
| 4 Stress-test (C1 omit/add, C2 ablation) | Run; C1 perturbations are synthetic | `03_RESULTS_TABLES/` |
| 5 Validate and report | Run; connectivity audit v2 lists house C0002 as a failure, the acceptance validator as information | `03_RESULTS_TABLES/CONNECTIVITY/`, `04_VALIDATION/` |
| Building-avoiding scenario (runner v1.4) | Run; crossings reduced, not eliminated (counts in table6_obstacle_avoidance.csv) | `outputs/final_comparison/table6_obstacle_avoidance.csv` |
| Visual audit of facilities | Protocol and table prepared; observation columns empty | `outputs/visual_audit/` |
| C3 transfer | Not started; blocked on written approval of the gate | `COMPLETION_GATE.md` |
""")
    put("00_START_HERE/COMPLETION_GATE.md", """# Completion gate: Damarakunta

Status values: PASS, PARTIAL, NOT VERIFIED, NOT IMPLEMENTED. No approval is implied; the five additional villages are NOT started.

| Requirement | Current evidence | Status | Remaining work | Source / experiment needed |
|---|---|---|---|---|
| House connectivity | 163/163 routed, 0 failed; audit v2: 2 FAIL per scenario (P01:house and G04) both from house C0002, which attaches to a 5-cell road component (151.55 m from the main cells in the audit, 155.24 m in the road-cell diagnostic); on the TGRAC road lines the same road is connected (outputs/connectivity); C0076 is an INFO label/snap mismatch | PARTIAL | Decide how the boundary-truncation limitation is reported; physical road not verified | `05_DIAGNOSTICS/CONNECTIVITY_EXCEPTIONS` |
| Facility connectivity | 5/5 facilities in the final layer routed and connected (2 schools, 1 sub-centre, 2 Gram Panchayat HQ points); the anganwadi (unsupported coordinate) was excluded at the project owner's request | PASS (model connectivity only) for the 5 facilities | A verified anganwadi location; facility identities are not field-verified | `facility_status.csv`, `EXCLUSIONS.md` |
| Segmentation-error sensitivity (C1) | primary and P3 omission scenarios, footprint exposure, 5-seed omit/add runs | PARTIAL | scenarios are synthetic, not measured false-negative rates | real segmentation error rates if claimed |
| Route-selection ablation (C2) | K x passes ablation, control identical, R01-R03 PASS | PASS for the stated ablation | K1/K3 pairwise geometry identity not established; no global-optimality claim; no run switches shared-edge accounting off | optional geometry comparison |
| Multi-criteria route selection | planner selects by weight / marginal cost; provisional equal facility weights; cost = land cover + slope | PARTIAL | A formal multi-criteria scheme (criteria, weights and their source) is not implemented or approved | decision on criteria; code change only after approval |
| Road width | no width parameter or output in planner or runner | NOT IMPLEMENTED | Needs source data and a design decision | requirement owner decision |
| Monetary construction cost | costs are ordinal units, NOT INR; an assumption-driven illustrative estimate exists in outputs/final_comparison (Table 5) and is not project data | NOT IMPLEMENTED | Needs a cost basis and approval | cost source |
| Additional-village transfer (C3) | none run; multi-village testing is extended future work | NOT IMPLEMENTED | Wait for written approval of this gate | five more villages |
| Imagery and TGRAC data licences | unresolved: Esri mosaic built from export requests (not Content Packages), enquiry draft not sent; TGRAC terms not found; attribution wording in Section 13.1 | NOT VERIFIED | Licence enquiry/answer; no imagery redistributed | `docs/DAMARAKUNTA_IMAGERY_LICENCE_ENQUIRY_DRAFT.md` |
| TGRAC data source and currentness | boundary copy equals stored response (IoU 1.0); live service not re-queried; licence not stated | NOT VERIFIED | Query date/version record; independent boundary comparison | TGRAC |
| Field validation, legal access, physical passability | none; routes are GIS/DEM simulations and ground truthing is designated for future phases | NOT IMPLEMENTED | Field work or authoritative records | `07_LIMITATIONS_AND_OPEN_ISSUES/METHODOLOGICAL_LIMITATIONS_AND_FUTURE_SCOPE.md` |
| P3 baseline reproduction | the P3 run is regenerated in every pipeline run and its lengths and costs match the reference exactly (3 fresh runs); route-level geometry comparison was done for the primary run only | PARTIAL | Run `dk_stageB_run_repro_compare_v1.py` for P3 | `06_REPRODUCIBILITY/P3_BASELINE_REPRODUCTION` |
| Building-footprint avoidance | active in the final network: buffer 7.1 m, penalty x100; fewer house routes cross another footprint at the price of a longer network (table6_obstacle_avoidance.csv); hard block failed (163/163 targets). Routes do NOT completely skirt buildings | PARTIAL | Remaining crossings occur where a target starts among touching buildings | `table6_obstacle_avoidance.csv` |
| Anganwadi exclusion | excluded from planning layers, CSVs and maps (derived layer; original input untouched) | OPEN (needs a verified location) | Verified coordinate, then re-include | `inputs/EXCLUSIONS.md` |
| Administrative utilities | 2 Gram Panchayat HQ points (TGRAC layer 10) included, each on or within 1 m of a detected footprint; MeeSeva and Directorate of ESD centres NOT located (no source in 162 TGRAC services or OpenStreetMap) | PARTIAL | Coordinates and source for MeeSeva and ESD; confirm the Panchayat building | `inputs/ADMIN_UTILITIES.md`, `inputs/admin_utilities_intake.csv` |
| Visual audit of facilities | protocol and Visual Grounding Table prepared (5 facilities) | NOT VERIFIED | Fill the observation columns in Google Earth | `outputs/visual_audit/` |

Approval: this gate is **not approved**. Written approval from the project owner is required before any further village is started.
""")
    put("01_ARCHITECTURE/DATA_AND_PROCESS_FLOW.md", """# Data and process flow (files)

| Stage | Script | Reads | Writes |
|---|---|---|---|
| Boundary | `save_damarakunta_boundary.py` | raw TGRAC JSON (EPSG:32644 declared) | `study_area/damarakunta_boundary.gpkg` (`village_boundary`) |
| Grid | `align_damarakunta_terrain.py` | boundary, WorldCover clip, DEM clip | `aligned/*_worldcover_10m.tif`, `*_dem_30m.tif`, `*_slope_30m.tif`, `*_slope_10m.tif` |
| Cost | `create_damarakunta_cost_surface.py` | WorldCover 10 m, slope 10 m | `*_cost_surface_10m.tif`, `*_prohibited_mask_10m.tif` |
| Stage A | `dk_stageA_prepare_r3.py` | v8 buildings, footprints, roads, v1 house network | `stageA/` tables, manifests |
| Stage B | `dk_stageB_run_v1_1/2/3/4.py`, `plan_network_v2.py` | Stage A, rasters, roads, facilities, cadastral | one run folder per scenario under `stageB/` |
| C1 | `dk_stageB_c1_*` scripts | run folders | `_c1_*` folders |
| C2 | `dk_stageB_c2_ablation_summary_v1.py` | run folders | `_c2_abl_v1` |
| Audits and diagnostics | `dk_stageB_connectivity_*`, `*_diag_v1`, `dk_boundary_crs_compare_v1.py` | run folders and inputs | `_connectivity_*`, `_c0002_*`, `_boundary_*`, `_road_component_*`, `_chain_cell_*` |
| Final package | `src/run_final_package.py` and its steps | pipeline run | `outputs/verification`, `connectivity`, `final_maps`, `final_comparison`, `final_package`, `visual_audit` |

Every Stage B run folder records `inputs_manifest_stageB.csv` (role, path, bytes, SHA-256, including the runner script), `config_stageB.json` and `outputs_manifest.csv`.
`01_ARCHITECTURE/ARCHITECTURE_DIAGRAM.png` and `WORKFLOW_DIAGRAM.png` are the nine-stage diagrams drawn for the Phase-I report, replacing the original draft overview.
""")
    put("01_ARCHITECTURE/PROJECT_WORKFLOW.md", """# Workflow as implemented (from code and run manifests)

```
Imagery (licence unresolved) -> building candidate extraction (extract_buildings_v8.py)
        -> buildings_v8_full.gpkg (278 candidates) -> footprint classes PLAUSIBLE / REVIEW / UNRESOLVED_MERGE (165 footprints inside the boundary)

TGRAC boundary (save_damarakunta_boundary.py)  --> 10 m planning grid 432 x 679, EPSG:32644 (align_damarakunta_terrain.py)
ESA WorldCover clip + ~30 m DEM clip            --> WorldCover 10 m, slope 10 m (bilinear from 30 m)
                                                --> cost surface + prohibited mask (create_damarakunta_cost_surface.py)
TGRAC roads (43 features), facilities, cadastral (reference layers)

Stage A: dk_stageA_prepare_r3.py -> candidates_master.csv, S1 default IDs (101), merged IDs (62), S2 = 163 houses, manifests, checks

Stage B: dk_stageB_run_v1_x.py + plan_network_v2.py
   facility phase -> house phase (K=3 alternatives, greedy select by weight/marginal cost, shared-edge credit, 2 leaf-reroute passes)
   comparison baselines: independent least-cost, straight-line, length-only, roads-only reference
   outputs: routes.gpkg (11 layers), route_edges.csv, selection_summary.csv, evaluation_summary.json, connectivity_checks.csv, road_components.csv, manifests, checks
   v1.4 option --avoid-buildings buffer: footprints buffered 7.1 m with a large penalty (planner unchanged)

Experiments: C1 (omission / addition scenarios, primary x4 and P3), C2 (K x passes ablation)
Validation: per-run acceptance tests, C1 report validation, connectivity audit v2, diagnostics (boundary, road components, chain cells)
Maps and package: dk_stageB_maps_v2.py, src/reporting/*, src/run_final_package.py
```

Not implemented: road width, monetary cost from project data, a formal multi-criteria scheme, a second village. The single end-to-end command is `python src/run_pipeline.py`; detection and terrain building are verified inputs and are not re-run by it.
""")
    put("06_REPRODUCIBILITY/COMMANDS_AND_PARAMETERS.md", """# Commands and parameters

Python 3.10.0; numpy 2.2.6, pandas 2.3.3, geopandas 1.1.4, shapely 2.1.2, rasterio 1.4.4, fiona 1.10.1 (from `config_stageB.json`).

## Runs (parameters taken from each run's `config_stageB.json`)
Common: scenario S2, facilities on, cost scenario C0, slope limit 25, building quality `PLAUSIBLE,REVIEW,UNRESOLVED_MERGE`, snap 30 m, max search 1500 m, attach tolerance 15 m, K=3, corridor 20 m with multipliers 3.0 and 8.0, max overlap 0.8, passes 2, corner cut forbid.

| Run | Runner | Differing arguments |
|---|---|---|
| `S2_fac_C0_s25_v11` (primary baseline) | v1.1 | `--building-mult 4.0 --label v11` |
| `S2_fac_C0_s25_P3_none` | v1.2 | `--building-mult 1.0 --label P3_none` |
| `S2_fac_C0_s25_K3_P2`, `K1_P0`, `K1_P2`, `K3_P0` (C2) | v1.3 | `--k`, `--passes` |
| `..._omitsmall25`, `omitsmall10`, `omitmerge` and `_P3_none` variants | v1.3 | `--perturb omit_small --small-pct 25` etc. |
| `..._omit10/20`, `..._add10/20` seeds 20261029-33 | v1.3 | `--perturb omit|add --perturb-frac --perturb-seed` |
| `..._avoid_buf20/100/1000` (building-avoiding scenario) | v1.4 | `--building-mult 20|100|1000 --avoid-buildings buffer --label avoid_buf<m>` |

The original run command lines were not logged; the pipeline (`src/run_pipeline.py`) now writes them to `outputs/run_<timestamp>/pipeline.log`.

## Whole pipeline
```bash
python src/run_pipeline.py --profile full
python src/run_final_package.py
```
## Diagnostics (as run)
```powershell
$B = "D:\\Telangana_Rural_Project\\Siddipet\\Damarakunta\\results\\run_20261029_01\\stageB"
python scripts\\dk_stageB_boundary_mask_diag_v1.py --stageb-root $B
python scripts\\dk_boundary_crs_compare_v1.py
python scripts\\dk_stageB_road_component_boundary_diag_v1.py --stageb-root $B
python scripts\\dk_stageB_chain_cell_reasons_v1.py --stageb-root $B
```
Each refuses to overwrite its output folder and hashes inputs before and after. Hashes: `SCRIPT_HASHES.csv`, `INPUT_HASHES.csv` (recomputed in this reconstruction).
""")
    put("06_REPRODUCIBILITY/P3_BASELINE_REPRODUCTION/README_RUN_THIS.md", """# P3 baseline reproduction

Original run: `stageB/S2_fac_C0_s25_P3_none` (runner `dk_stageB_run v1.2`). Recorded result: 163 houses, house unique length 4761.726 m, combined unique ordinal cost 21560.633.

**Status (reconstruction): PARTIAL.** Every pipeline run regenerates the P3 run and its lengths and costs match the reference exactly (checked in three fresh runs). A route-level geometry comparison (`dk_stageB_run_repro_compare_v1.py`) was done for the primary run only. To complete it:

```bash
python scripts/dk_stageB_run_repro_compare_v1.py --original <reference stageB>/S2_fac_C0_s25_P3_none --repro <new stageB>/S2_fac_C0_s25_P3_none --out <new stageB>/_compare_P3
```
""")
    sys_path = str(ROOT / "src" / "reporting")
    import sys as _s
    _s.path.insert(0, sys_path)
    import limitations_text
    put("07_LIMITATIONS_AND_OPEN_ISSUES/METHODOLOGICAL_LIMITATIONS_AND_FUTURE_SCOPE.md", "# Methodological Limitations and Future Scope\n\n" + limitations_text.TEXT.split("\n", 1)[1])
    put("07_LIMITATIONS_AND_OPEN_ISSUES/LIMITATIONS.md", """# Limitations

## Claims not made
No field validation, legal road access, ownership confirmation, physical passability, construction savings, or real-world accessibility improvement. Costs are ordinal model units, not rupees. Evidence is on a 10 m planning grid.

## From the run configuration
- Building candidates are model detections, unverified. Routes are planning alternatives, not roads.
- Slope is a bilinear resample of a slope computed from a ~30 m DEM; it is not true 10 m terrain.
- TGRAC reference roads may be incomplete; only road cells inside the valid village grid are planner goals.
- Parcel counts are crossings of parcel units, not ownership or legal access.
- Facility identities and coordinates are not field-verified. The anganwadi was excluded from the deliverables because its coordinate lies 371 m from the nearest detected footprint (inputs/EXCLUSIONS.md).
- Imagery source/date/licence, model-weight location and TGRAC data licence are unresolved.

## C1 / C2
- Omission and addition scenarios are synthetic and deterministic (seeded), not measured segmentation false-negative rates. A shorter network with fewer routed targets is not greater efficiency; compare length per routed target.
- Shared-edge credit counts only identical grid edges; the planner is not globally optimal.
- K1/K3 summaries match at each pass setting but pairwise geometry identity is not established.

## Boundary-related connectivity limitation
Of 1,564 road-line-covered cells with invalid cost and prohibited-mask value 1, 1,532 (98.0%) have centres outside the study polygon; 32 are inside, within 23.3 m of it. 41,789.51 m of 93,496.76 m (44.70%) of TGRAC road geometry, in 20 of 43 features, lies outside the polygon.
House C0002 attaches to component 10 (5 cells, 155.24 m from the main cells in the road-cell diagnostic). This is documented as a boundary-truncation limitation of the planning domain; no cell was made passable, no routing was done outside the polygon, and the planner is not shown to be defective. On the TGRAC lines the same road is connected to the main network (about 630 m along the lines, 385 m of it outside the polygon).

## Building avoidance
Hard blocking of footprint cells fails (every house point lies inside its own blocked cell). The buffer scenario keeps some house routes crossing another footprint, most of them only within the first 20 m of the route (table6_obstacle_avoidance.csv).

## Boundary
The saved boundary equals the stored raw TGRAC response exactly (EPSG:32644, IoU 1.0). Authority and currentness of the TGRAC polygon were not verified; the cadastral union covers 97.81% of the boundary, a cross-check only.

## Figures
The C1 bar chart (`fig1_length_and_per_routed.png`) had its legend overlapping a value label. No figure is declared publication-ready.
""")
    issues = [("U01", "P3 baseline reproduction: route-level geometry comparison not run (lengths and costs reproduce)", "PARTIAL", "Run the comparison for P3", "06_REPRODUCIBILITY/P3_BASELINE_REPRODUCTION"),
              ("U02", "Research parameters (x4 penalty, class set, equal facility weights) not confirmed as final", "PROVISIONAL", "Owner decision", "config_stageB.json"),
              ("U03", "Road width not implemented", "NOT IMPLEMENTED", "Requirement owner decision and data", "COMPLETION_GATE.md"),
              ("U04", "Monetary construction cost not implemented from project data (an illustrative assumption-based estimate exists)", "NOT IMPLEMENTED", "Cost basis and approval", "COMPLETION_GATE.md"),
              ("U05", "Formal multi-criteria route selection not implemented/approved", "PARTIAL", "Criteria and weights", "COMPLETION_GATE.md"),
              ("U06", "Imagery licence unresolved", "NOT VERIFIED", "Licence answer; enquiry draft not yet sent", "docs/DAMARAKUNTA_IMAGERY_LICENCE_ENQUIRY_DRAFT.md"),
              ("U07", "TGRAC boundary/road authority, currentness and licence", "NOT VERIFIED", "Query date record; independent comparison", "05_DIAGNOSTICS/BOUNDARY_AND_ROADS"),
              ("U08", "Why 30 m DEM cells are masked at some inside cells (29 of 32 interior blocked road cells fall on masked DEM cells; 3 unexplained)", "UNRESOLVED", "Inspect DEM clip footprint vs polygon", "05_DIAGNOSTICS/CHAIN_CELL_REASONS"),
              ("U09", "Road components C3, C4, C7, C8, C9: no line chain to main within grid extent", "UNRESOLVED", "Optional: test beyond the bounding box", "05_DIAGNOSTICS/ROAD_COMPONENTS"),
              ("U10", "Older phase22-24 and ranking scripts not audited", "NOT VERIFIED", "Code audit if used in the dissertation", "scripts/ (legacy copies in archive)"),
              ("U11", "14 planner tests and 31 audit tests not re-run in this pass", "PROVISIONAL", "Re-run only if scripts change", "test_plan_network_v2.py"),
              ("U12", "C1 chart legend overlaps a value label (original chart)", "DEFECT", "Regenerate as a new versioned figure", "03_RESULTS_TABLES/C1_SEGMENTATION_SENSITIVITY/figures"),
              ("U13", "No second village; C3 not assessed", "NOT IMPLEMENTED", "Await written gate approval", "COMPLETION_GATE.md"),
              ("U14", "No field validation, legal access or physical passability evidence", "NOT IMPLEMENTED", "Out of current scope", "LIMITATIONS.md"),
              ("U15", "Anganwadi excluded at the owner's request (coordinate 371 m from the nearest footprint, 126 m from the nearest Open Buildings polygon)", "OPEN", "Verify the location (registry or Google Earth), then re-include", "inputs/EXCLUSIONS.md"),
              ("U16", "Detection accuracy unknown: no reference buildings; agreement with Open Buildings 72%, REVIEW class 44%", "UNRESOLVED", "Label a village subset", "outputs/verification"),
              ("U17", "House routes still crossing another footprint in the building-avoiding final network (see table6_obstacle_avoidance.csv)", "BOUNDED", "Needs building-level geometry or a finer grid", "outputs/final_comparison/table6_obstacle_avoidance.csv"),
              ("U18", "Visual Grounding Table observation columns empty", "NOT STARTED", "Fill in Google Earth Pro", "outputs/visual_audit"),
              ("U19", "Original DELIVERABLES folder lost; this folder is a reconstruction", "NOTED", "Commit the folder to git", "00_START_HERE/README_PROJECT_OVERVIEW.md")]
    p = OUT / "07_LIMITATIONS_AND_OPEN_ISSUES" / "UNRESOLVED_ISSUES.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id", "issue", "status", "next_action", "where"]); w.writerows(issues)
    manifest.append(("07_LIMITATIONS_AND_OPEN_ISSUES/UNRESOLVED_ISSUES.csv", "generated", ""))
    put("08_SOURCE_REFERENCES/DATA_SOURCES_AND_LICENSES.md", """# Data sources and licences (as recorded in the project; not re-verified)

| Dataset | Source | Licence status |
|---|---|---|
| Village boundary | TGRAC `AdministrativeInfoSystem_Folder/Administrative_Information_System/MapServer/27` (Village=DAMARAKUNTA, Mandal=MARKOOK, District=SIDDIPET); stored response declares EPSG:32644 | Not stated; not verified |
| Road network | TGRAC `SchoolGIS_Folder/Schools/MapServer/20` | Not stated; completeness/currentness unverified |
| Facilities / schools / health | TGRAC layers (school, health; the anganwadi record is excluded, see EXCLUSIONS.md) | Not stated |
| Land cover | ESA WorldCover 2021 v200 (10 m); version not stored in the raster | CC BY 4.0 (per project notes) |
| DEM | clipped file `damarakunta_dem_30m.tif`; file name `n17_e078_1arc_v3` suggests an SRTM-type product; source not recorded | Not verified |
| Imagery | Esri World Imagery 0.6 m mosaic (built 4 Oct 2026 from 11 `MapServer/export` requests); capture date 29 Apr 2026 at one sampled point (Esri identify result), elsewhere not recorded | Esri licence unresolved; the enquiry draft has NOT been sent; do not redistribute |
| Building candidates | `results/v8_instances/buildings_v8_full.gpkg` (model-derived) | Derived from imagery of unresolved licence |
| Cadastral | `reference/damarakunta_cadastral*.gpkg` (794 parcels) | Source and licence not re-checked |
| Google Open Buildings v3 (verification reference) | `reference/external/google_open_buildings_v3.gpkg` (1,537 polygons in the boundary) | CC BY 4.0 / ODbL per Google; not re-checked |
| LoveDA benchmark | Zenodo 10.5281/zenodo.5706578; arXiv 2110.08733 | CC BY 4.0 per the Zenodo record |

See also `inputs/METADATA.md`.
""")

    # manifests
    with open(OUT / "00_START_HERE" / "COPY_MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["file", "how", "source"]); w.writerows(manifest)
    with open(OUT / "00_START_HERE" / "GENERATED_FILES.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["file", "bytes", "sha256"])
        for p in sorted(OUT.rglob("*")):
            if p.is_file() and p.name not in ("GENERATED_FILES.csv",):
                w.writerow([str(p.relative_to(OUT)).replace("\\", "/"), p.stat().st_size, sha(p)])
    n = sum(1 for p in OUT.rglob("*") if p.is_file())
    print("rebuilt", OUT, n, "files,", round(sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
