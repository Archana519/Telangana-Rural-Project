# Damarakunta input metadata (single source of inputs)

The pipeline reads these inputs and no others. They stay where they are under `Siddipet/Damarakunta/`; `run_pipeline.py` checks each file's SHA-256 against the hashes recorded in the reference run `run_20261029_01` before it does anything, so a changed or swapped file stops the run. Facts below were checked on 2026-10-29/30 against `docs/DAMARAKUNTA_STAGE_A_INPUT_VALIDATION.md`, `COMPLETION_GATE.md` and the files themselves. "Unresolved" means no evidence was found; it does not mean the item is fine.

| Role | File (under `Siddipet/Damarakunta/`) | Content | Source | Date / currentness | Licence / constraints |
|---|---|---|---|---|---|
| Imagery | `aligned/damarakunta_esri_highres_mosaic_0p6m.tif` | 11,296 x 7,171 px, 3 bands, 8-bit, 0.6 m, EPSG:32644 | Esri World Imagery, 11 MapServer export requests on 4 Oct 2026 | Capture date 29 Apr 2026 at the one point sampled with the Esri identify service (Vantor, 60 cm layer; `reference/external/esri_world_imagery_identify.json`); dates elsewhere in the mosaic are not recorded | **Unresolved.** The project's notes record Esri terms that appear to restrict bulk tile export. The enquiry draft (`docs/DAMARAKUNTA_IMAGERY_LICENCE_ENQUIRY_DRAFT.md`) has not been sent. Do not redistribute the imagery or figures that contain it. |
| Boundary | `study_area/damarakunta_boundary.gpkg` | 1 polygon, 365 vertices, 18.466 km2 | TGRAC Administrative Information System MapServer layer 27 (Village = DAMARAKUNTA, Mandal = MARKOOK, District = SIDDIPET) | Downloaded 2026-10; live service not re-queried; equals the stored response (IoU 1.0) | Licence not stated; authority and currentness not verified; no independent boundary comparison |
| Roads | `reference/tgrac_road_network.gpkg` | 43 line features, 93,496.76 m; 44.70% of the length lies outside the village polygon | TGRAC (Schools MapServer layer 20, as recorded) | Downloaded 5 Oct 2026; **currentness unknown** | Licence not stated; completeness and connectivity unverified |
| Facilities | `reference/damarakunta_priority_facilities.gpkg` (hash-pinned, 4 points: 2 schools, 1 sub-centre, 1 anganwadi); the deliverables use `reference/derived/damarakunta_priority_facilities_excl_1702300.gpkg` (3 points; anganwadi excluded, see `inputs/EXCLUSIONS.md`) | TGRAC school, health and anganwadi layers | Downloaded 5 Oct 2026 | Identity and coordinates unverified; the sub-centre has two TGRAC records 235.7 m apart |
| Building candidates | `results/v8_instances/buildings_v8_full.gpkg` | 278 model-derived polygons (135 plausible, 59 review, 84 unresolved merge) | Project extraction `extract_buildings_v8.py` from the imagery | Derived 2026-10 | Inherits the imagery licence question; status AUTO_DETECTED_UNVERIFIED; no reference buildings exist |
| Land cover | `aligned/damarakunta_worldcover_10m.tif` | 679 x 432 cells, 10 m | ESA WorldCover; project notes record 2021 v200 | Version not stored in the raster | CC BY 4.0 per project notes (not re-checked) |
| Terrain | `aligned/damarakunta_slope_10m.tif` (from `damarakunta_dem_30m.tif`) | Slope on the 10 m grid, interpolated from a 30 m DEM | File name `n17_e078_1arc_v3` suggests an SRTM-type product; **source not recorded** | Unknown | Unresolved |
| Cost surface | `aligned/damarakunta_cost_surface_10m.tif`, `damarakunta_prohibited_mask_10m.tif` | Ordinal cost 2.09 to 12.0; mask | Derived by `create_damarakunta_cost_surface.py` | Built 12 Oct 2026 | Ordinal units, not rupees; the mask is a computational exclusion, not a legal restriction |
| Cadastral / compounds | `reference/damarakunta_cadastral_valid.gpkg`, `school_compounds_utm44n.gpkg` | 794 parcels; 2 compounds | TGRAC; compound creation method unknown | Downloaded 5 Oct 2026 | Used only for exposure flags, not ownership or access |

Use constraints that apply to every output: routes are planning alternatives (`UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD`), not roads; no field validation, legal access, drainage, width or money cost is claimed; the Damarakunta completion gate is not approved, and C3 (other villages) has not started.

Rejected as inputs: anything in `archive/` (earlier route versions, validation folders, the Google Open Buildings test, Sentinel-2 and appearance tests).

## Road layer clipped to the village boundary (31 October 2026)

`Siddipet/Damarakunta/reference/derived/tgrac_road_network_clipped.gpkg` is `gpd.clip()` of `reference/tgrac_road_network.gpkg` to `study_area/damarakunta_boundary.gpkg` (`src/preprocessing/clip_roads.py`, figures in `inputs/road_clip_report.csv`): 93,496.76 m in 43 lines, 41,789.51 m (44.70%) outside and removed, 51,707.25 m in 50 parts inside. The final scenarios route on the clipped layer (`dk_stageB_run_v1_5.py --roads-file`); the original file is untouched and the two verified baseline runs still use it.

Slope and land-cover gaps inside the boundary (961 and 178 cells) come from the coarse 30 m DEM and land-cover source. They are not interpolated; the planner treats them as invalid cells.

## Sub-centre local penalty override (2 November 2026)

For `HEALTH_8734223673` (Sub Centre, Damarakunta, 17.70820 N, 78.75382 E) the final scenarios run with `dk_stageB_run_v1_6.py --facility-exempt HEALTH_8734223673:20`: the footprints handed to the planner are cut by a 20 m circle around the point, so the building penalty does not apply there. The point lies 1.8 m from a 1,194 m2 unresolved-merge footprint and the penalty made its route detour round it. Tested 10, 20 and 30 m; 20 m changes no other route (0 of 163 house routes differ). Crossing statistics still use the original footprints. The planner cannot attach a facility to house routes (facilities are planned first), so the route still ends on the road.
