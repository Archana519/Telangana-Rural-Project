# DAMARAKUNTA_STAGE_A_INPUT_VALIDATION (proposed document, 2026-10-24)

Save as a NEW file in `D:\Telangana_Rural_Project\`. Scope: Damarakunta only. Measurements and provenance, **not accuracy claims**.
Evidence: `Siddipet\Damarakunta\results\stageA_input_validation\stageA_1` (script `validate_damarakunta_inputs.py`, read-only), plus file listings and the extra raster check pasted on 2026-10-24. Labels: **Verified** = measured or listed in your output; **Unverified** = inferred or not checked.

## 1. Rasters (Verified)
| Input (config key) | File | Grid | Valid inside polygon | Notes |
|---|---|---|---|---|
| Imagery (`raster`) | `aligned\damarakunta_esri_highres_mosaic_0p6m.tif` | EPSG:32644, 11,296 x 7,171 px, 0.6 m, uint8 RGB | 100 % | Bbox 6,777.6 x 4,302.6 m = 29.16 km2 vs polygon 18.466 km2 (ratio 1.58). 3.32 % of the bbox is all-zero (0.967 km2). That equals the corner tile that would complete the 1,800 m grid (1,377.6 x 702.6 m = 0.968 km2): 11 tiles exist, 12 are implied. The blank corner lies outside the polygon |
| `pred_classes` | path set in `configs\damarakunta.json` (not shown in the output I have) | same grid as the mosaic | 100 % | class IDs 1-7, nodata 0 |
| `building_prob` | same folder | same grid, uint8 | 100 % | channel scaling 0-255 (per `run_rural_planning_pipeline.py`) |
| `worldcover` | `aligned\damarakunta_worldcover_10m.tif` | EPSG:32644, 679 x 432, 10 m | 99.90 % | invalid inside = 178 cells (0.0964 % of 184,646) |
| `cost` | `aligned\damarakunta_cost_surface_10m.tif` | same grid, float32, nodata -9999 | 99.31 % | values 2.09-12.0; invalid inside = 1,276 cells = 178 + 224 water + 874 invalid slope (0.691 %), matching Phase B |
| DEM | `aligned\damarakunta_dem_30m.tif` | EPSG:32644, 30 m, float32 | n/a | 564.3-625.8 m (61.5 m relief); 37.3 % masked (outside boundary) |
| Slope | `aligned\damarakunta_slope_10m.tif` | 10 m, float32 | n/a | 0.02-27.7 deg; 37.38 % masked. Derived from the 30 m DEM, so 10 m slope values are interpolated |
| Prohibited mask | `aligned\damarakunta_prohibited_mask_10m.tif` | 10 m, uint8 0/1 | n/a | not a legal layer (Phase B B2); 37.49 % of cells blocked |

All rasters listed share EPSG:32644. For imagery, predictions, WorldCover and cost the bounds fully contain the village bbox (measured). For the DEM, slope and mask the CRS and masks were read, but their bounds were not compared with the polygon.

## 2. Vectors (Verified)
| Input | File | Result |
|---|---|---|
| Boundary | `study_area\damarakunta_boundary.gpkg` (layer `village_boundary`) | 1 valid Polygon, EPSG:32644. Source: TGRAC service; **not compared with an independent boundary** |
| Roads | `reference\tgrac_road_network.gpkg` | 43 MultiLineString, 0 invalid, 0 duplicates, all inside the polygon (clipped or filtered). Source TGRAC `Schools/MapServer/20`; completeness and connectivity not assessed |
| Facilities | `reference\damarakunta_priority_facilities.gpkg` (layer `priority_facilities`) | 4 Points, valid, inside the village |
| Evaluation windows | `windows` 6 polygons; `reference_buildings` **0 features**; `reference\manual_building_labels` **empty** | no building ground truth exists |

## 3. Provenance dates (Verified from file times)
TGRAC reference downloads (roads, health, anganwadi, sub-centres) 5 Oct 2026 11:41; school files 5 Oct 12:02-12:04; Esri tiles 4 Oct 2026 20:29-20:44; mosaic 4 Oct 20:53; terrain/cost/mask rasters 12 Oct 17:12-17:30; priority facilities 12 Oct 17:26. Imagery capture dates are **unknown** (not stored with the export).

## 4. Licence and source status
| Source | Status |
|---|---|
| Esri World Imagery export (mosaic, tiles) | **UNVERIFIED**; Esri terms summary limits offline use to Content Packages (see IMAGERY_EXPORT_PLAN_REVIEW.md section 2). Mosaic not modified or re-exported |
| DEM `n17_e078_1arc_v3` (SRTM-style 1 arc-second, by name) | terms not recorded in the project; to be written down by you |
| ESA WorldCover 2021 v200 | terms not recorded in the project; to be written down by you |
| TGRAC layers | state-government service; terms not checked; boundary, roads and facility accuracy unverified |
| School compound polygons | creation method **unknown** (no script found that creates them) |

## 5. Limitations that matter downstream
- The imagery has a blank corner outside the village; any model or extraction run on the full bbox sees zeros there.
- DEM is 30 m; slope at 10 m is interpolated; one target (C12) failed on a 10.349 deg cell (Phase B).
- Facility locations are unverified; the sub-centre has two TGRAC positions 235.7 m apart.
- No ground truth for buildings, so segmentation accuracy cannot be computed.

## 6. Not checked in Stage A
Independent boundary comparison; imagery native detail and capture dates; the prediction rasters were opened only for grid, validity and class IDs (no accuracy or visual check).
