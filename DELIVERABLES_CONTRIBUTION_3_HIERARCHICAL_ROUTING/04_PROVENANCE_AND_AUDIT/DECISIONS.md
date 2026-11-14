# DECISIONS

| # | Date | Decision | Reason | Evidence | Alternative considered | Why rejected |
|---|---|---|---|---|---|---|
| 1 | 2026-09-30 | Phase 0 audit runs on the user's machine via `scripts/phase0_audit.py` | The project, checkpoint and GPU are on the user's Windows PC; the assistant's sandbox cannot see them | No files uploaded; sandbox is a separate Linux container | Assistant writes the audit from the user's description | Would be unverified; violates "audit before coding" |
| 2 | 2026-09-30 | LoveDA mIoU 53.80 / mDice 68.91 reported only as source-domain results | Checkpoint was validated on LoveDA only | Checkpoint metadata (to be confirmed by audit) | Report as project performance | Not Siddipet evidence |
| 3 | 2026-09-30 | Never use 0.55 m/pixel for Siddipet; distances only in a projected UTM CRS chosen from data coordinates | Fixed scale came from LoveDA resizing | User instruction; audit will locate the constant | Keep scale factor | Not true georeferencing |
| 4 | 2026-09-30 | TGRAC MapServer imagery treated as NOT downloadable and NOT licensed until proven | MapServer export returns rendered images; no licence stated | TGRAC Web GIS page describes services for departments/collaborators | Scrape tiles | Legal and scientific risk |
| 5 | 2026-09-30 | Sentinel-2 used only for seasonal land-cover/water support, not building segmentation | 10 m pixels cannot resolve individual rural buildings | Sensor specification | Use Sentinel-2 as main imagery | Resolution far from model's training scale |
| 6 | 2026-09-30 | Open Buildings, OSM, PMGSY, TGRAC, WorldCover labelled REFERENCE, never GROUND_TRUTH | They are model outputs or unvalidated compilations | Dataset documentation | Treat as ground truth | Inflates reported accuracy |
| 7 | 2026-09-30 | Facilities come only from external records; the size heuristic survives only as `P1_candidate`, `confirmed=false` | Building size does not identify function | User instruction | Keep heuristic as primary | Scientifically invalid |
| 8 | 2026-09-30 | Earlier `tools/` folder renamed `scripts/` | Match the agreed project structure | — | Keep both | Avoid duplicate paths |
| 9 | 2026-11-14 | Contribution 3 (hierarchical GP -> Mandal -> District routing) started on the owner's written request in chat; implemented as `src/routing/hierarchical_router.py` re-using the Stage B `Grid` search | Completion gate item U13 required written owner approval before any scale-up | Owner request of 2026-11-14 | Wait for the five-village transfer study | Level 2 uses hamlet hubs, not individual houses, so its lengths are NOT comparable with the Level-1 5,069 m; Levels 3-4 run on synthetic worlds until real boundaries/DEM/land cover are supplied |
| 10 | 2026-11-14 | DEM source: Level 1 (Stage B) used SRTM 1 arc-second (`n17_e078_1arc_v3.tif`, USGS); Levels 2-4 use Copernicus GLO-30. **Both are ~30 m**, both go through the same Stage B slope method (Sobel/8/30 m on the 30 m grid, bilinear to the target grid; `layers.slope_sobel`). The discrepancy is documented and quantified, not removed | Owner chose the downloaded, gap-free Copernicus tiles; the SRTM file Stage B used is not in the repository; Stage B scripts `prepare_damarakunta_terrain.py` / `align_damarakunta_terrain.py` show the SRTM file and the Sobel slope | `docs/results/U08_dem_comparison.json` (`python -m src.evaluation.dem_consistency`): elevation RMSE 2.3 m, bias -1.6 m, r = 0.996; slope r = 0.70 (noise on flat ground), >25 deg hard-block mask differs in 0 cells; Level 2 shared length differs by 1.0 % and ordinal cost by 2.6 %, override detour reduction identical. The SRTM in that comparison is the AWS 'skadi' product, a proxy for the USGS file | Re-run Levels 2-4 with SRTM (`--dem-source srtm --force`) | Not needed: effect <= 1 % on length; but Level 1 vs Levels 2-4 are NOT strictly the same terrain source, and the paper says so. The first Levels 2-4 run used np.gradient on the resampled grid instead of the Stage B Sobel method; that inconsistency was found and fixed in this pass (numbers in rows 11-12 are after the fix) |
| 11 | 2026-11-14 | Level 3 attaches to COLLECTOR-grade roads only (motorway..tertiary); lower classes only lower the travel cost. District results report NEW CONSTRUCTION separately from length on existing roads | First real run attached villages to 1,579 Overture segments incl. tracks (total 180 m: degenerate) and counted 344 km of existing highway as network length | `docs/results/hierarchy_real_run` (Level 3 5,913 m; Level 4 358.7 km of which 14.7 km new) | Keep all classes as goals; report total length only | Hides what would actually be built; misstates savings (22.2% total vs 25.9% on new construction) |
| 12 | 2026-11-14 | **U02 SIGNED OFF by the project owner (chat instruction, 2026-11-14): mu = 4 is the primary footprint penalty.** The sensitivity set mu in {1, 2, 4, 8, 20, 100} is always published beside it. Facility weights stay equal (1.0) | Real Damarakunta GP data: mu = 4 removes 89.0 % of route length inside footprints (109.1 m -> 12.0 m; routes crossing 6 -> 3) for +5.2 % network length (1,657.1 -> 1,743.7 m); mu = 8 adds only 4.4 points of exposure reduction for 2.9 more points of length; mu >= 20 reduces exposure no further | `docs/results/U02_penalty_sweep_gp.csv` (`python -m src.evaluation.penalty_sweep`, deterministic, re-run reproduced by `provenance_audit`); Stage B table6 (x1, x4, buffer x20/x100) agrees in direction | mu = 8 or a hard buffer | Longer network for a 4-point gain; hard blocking fails because every house point lies inside its own blocked cell (Stage B). Note: the owner's request quoted '90 % for +5.7 %', which was the first-run value; after aligning the slope method with Stage B the recomputed figures are 89.0 % and +5.2 % and these are the recorded ones |
| 13 | 2026-11-14 | U03/U04 rupee cost: implement a parameterised per-metre model (road class x terrain x land cover + structures) with the owner's Rs 75 lakh/km as the CENTRAL rate and +/-20% bounds, reported next to (never instead of) ordinal cost; real SOR/PMGSY rates replace the assumed ones before any financial claim | No project cost data exists (`inputs/economic_assumptions.json` is assumptions only) | Plan and stub below | Convert ordinal cost to rupees by a single factor | Ordinal cost mixes land-cover resistance with slope; it is not proportional to money |
| 14 | 2026-11-14 | U15 anganwadi re-inclusion only through the visual-audit decision rule (confirm <= 20 m, relocate <= 200 m, else reject) | The TGRAC point is 371 m from the nearest footprint; a wrong point would create a false facility | `inputs/EXCLUSIONS.md`, `src/validation/visual_audit_protocol.py` | Re-include on the TGRAC coordinate | Unsupported location |
| 15 | 2026-11-14 | U12 (C1 chart legend overlapping a value label) resolved by redrawing the Level 1 omission chart as `figD_level1_omission.png` (`python -m src.evaluation.plot_level1_omission`) from the recorded `table4_c1_sensitivity.csv`, with direct labels and no legend; the original defective chart is superseded and no longer used in the paper | The original figure was a defect recorded in `UNRESOLVED_ISSUES.csv` and Stage B could not be re-executed here | `paper/figures/figD_level1_omission.png`; audit checks FG-figD_* (300 dpi, identical in both folders, included and cited in `main.tex`) | Patch the original script | The original generator script is not in the repository, and the recorded table is the authoritative source |
| 16 | 2026-11-14 | A Stage-B-style deliverables package for Contribution 3 is built in a NEW folder `DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING/` (README, architecture, four 300 dpi maps with land-cover context, tables as CSV/Markdown/Excel, two charts, provenance snapshots, limitations) by `python -m src.evaluation.build_contribution3_deliverables`; `DELIVERABLES_DAMARAKUNTA_STAGE_B/` is never written to | Reviewers expect Contribution 3 to be packaged like Stage B; Stage B is the recorded Level 1 evidence | git tree hash of the Stage B folder is `4e5cedcefcfb9231074a10667e8050f4650d8766` before and after (audit check DV-stageB-untouched; `04_PROVENANCE_AND_AUDIT/STAGE_B_UNTOUCHED.txt`); audit checks the package (required files, MANIFEST.csv SHA-256, 300 dpi, README numbers) | Put the new files inside the Stage B folder | Would alter evidence that is supposed to be frozen; imagery basemaps were not used (Esri licence unresolved): land cover from ESA WorldCover gives the map context |

## Implementation plans and stubs (decisions 12-14)

### U02 - footprint penalty (SIGNED OFF) and facility weights (provisional)
Status: **RESOLVED - owner sign-off recorded 2026-11-14 (decision 12)**; mu = 4 is the knee of the real-data trade-off.
Remaining steps: (1) ~~owner confirms mu = 4~~ done; equal facility weights remain provisional; (2) test priority weights (health 4, school 3, government 2, the planner defaults) as a sensitivity -
with an unlimited budget weights only change the selection ORDER, so expect small length differences; run `scripts/dk_stageB_run_v1_6.py` with `--weights` if exposed, otherwise via `hierarchical_router.plan_on_grid`
(node.weight); (3) add the sweep to the manuscript as a sensitivity table. Closing criterion: sweep + weights table committed and quoted with mu in every result.

### U03/U04 - rupee construction cost (not implemented; plan + stub)
Model, per metre of NEW route, all parameters in `configs/construction_cost.yaml` (to be created; every value tagged `source: ASSUMPTION` until replaced by the State Schedule of Rates / PMGSY design values):

    C_m(e) = rho_base * m_class(k) * m_terrain(s) * m_lc(l)  +  c_earthwork * V_m(s)  +  c_cd / L_cd        [Rs per metre]
    V_m(s) = B * d0 + (B**2 / 8) * tan(s)         # earthwork m3 per metre: flat formation + side-hill cut/fill wedge (approximation; verify against PMGSY cross-sections)
    m_terrain(s) = 1 + a * (min(s, 25) / 25) ** 2  # rock/hard-ground and hairpin allowance, a to be calibrated
    m_lc(l) = {tree cover: clearing multiplier, cropland: land-acquisition-free, built-up: n/a ...}
    structures: one cross-drainage work every L_cd metres, + Rs per metre of span where a route would have to cross water (currently routes never cross water: only existing roads bridge it)

Parameters: `rho_base` = Rs 7,500 per metre (the owner's Rs 75 lakh/km PMGSY-based central rate; low 6,000 / high 9,000, **unverified**), `B` = 5.0 m formation width and `d0` = 0.30 m
(from `inputs/economic_assumptions.json`), class multipliers `m_class` for {village track, single-lane bituminous, intermediate lane, double lane} (assumed 0.6 / 1.0 / 1.4 / 1.9 until an SOR is supplied).

Stub (`src/economics/construction_cost.py`, to be added after the owner supplies the rate table):

```python
def cost_per_m(road_class: str, slope_deg: float, landcover: int, p: dict) -> float:
    s = min(max(slope_deg, 0.0), p["slope_limit_deg"])
    earth = p["B"] * p["d0"] + (p["B"] ** 2 / 8.0) * math.tan(math.radians(s))
    return (p["rho_base"] * p["class_mult"][road_class] * (1 + p["a"] * (s / p["slope_limit_deg"]) ** 2) * p["lc_mult"].get(landcover, 1.0)
            + p["c_earthwork"] * earth + p["c_cd"] / p["L_cd"])

def route_cost_inr(route_cells, slope, landcover, res_m, road_class, p) -> dict:   # low / central / high via p["rate_scale"] = (0.8, 1.0, 1.2)
    ...
```
Wiring: sample slope/land cover along every route (grid cell centres, as `verify_connectivity` already does), add `*_inr_lakh_{low,central,high}` columns to `evaluate_level`,
keep ordinal cost columns. Tests: monotone in slope and road class; zero for zero-length routes; rupee total for a flat 1 km single-lane route equals rho_base x 1000 x (1 + earthwork/cd terms).
Acceptance: rates traceable to a named SOR year, `source: ASSUMPTION` count = 0, outputs labelled "construction estimate" with +/-20% band. Needs from the owner: SOR/PMGSY rate table and road-class design (width, pavement).

### U15 - anganwadi node (blocked on a verified coordinate)
1. Verify with the Visual Grounding Table (`outputs/visual_audit/`, protocol in `src/validation/visual_audit_protocol.py`): confirm <= 20 m, relocate <= 200 m, else reject; record imagery date and the corrected lat/lon in `inputs/admin_utilities_intake.csv`.
2. Only then re-include (stub):
```python
def reinclude_facility(fac_gdf, facility_id, verdict):          # verdict: {"status": "CONFIRMED"|"RELOCATED"|"REJECTED", "lon":..., "lat":...}
    if verdict["status"] not in ("CONFIRMED", "RELOCATED"):
        raise ValueError("refusing to re-include an unverified or rejected facility")
    row = fac_gdf.loc[fac_gdf.facility_id == facility_id].copy()
    if verdict["status"] == "RELOCATED":
        row["geometry"] = gpd.GeoSeries([Point(verdict["lon"], verdict["lat"])], crs=4326).to_crs(fac_gdf.crs).values
    return pd.concat([fac_gdf, row.assign(facility_type="Anganwadi", priority_group=1)])        # -> damarakunta_priority_facilities_final_6.gpkg
```
3. `data_hooks.load_gp_real`: map type "Anganwadi" to kind `anganwadi`; set `exempt=True` only if the verified point is within 5 m of its own footprint edge (the sub-centre/school case); weight 1.0.
4. Re-run Stage B (S2) and Level 2; update the expected facility count (5 -> 6) in `tests/test_hierarchical_router.py::test_real_damarakunta_gp_inputs_load_and_run`, `expect_facilities` in the Stage B config and `inputs/EXCLUSIONS.md` (mark RESOLVED); do not hand-edit published results.
Closing criterion: verified coordinate on file + both runs reproduced with 6 facilities.

### U08 - DEM consistency (resolved by documentation + quantification)
The issue recorded as U08 in `UNRESOLVED_ISSUES.csv` is *why 30 m DEM cells are masked inside the village* (29 of 32 blocked interior road cells on masked DEM cells; 3 unexplained) - that remains open and needs the original SRTM clip. The separate question raised in this pass, whether Level 1 and Levels 2-4 use the same terrain source, is closed by decision 10: SRTM (Level 1) vs Copernicus (Levels 2-4), same 30 m grid and same Sobel slope method, difference quantified in `docs/results/U08_dem_comparison.json`. Closing criterion for the original U08: re-clip the SRTM tile to the polygon and compare its footprint with the masked cells.
