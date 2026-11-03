# DAMARAKUNTA_STAGE_A_INPUT_VALIDATION

**Document status:** Corrected working document  
**Original validation date:** 2026-10-24  
**Scope:** Damarakunta village, Siddipet, Telangana  
**Purpose:** Input measurements, provenance and limitations — **not accuracy claims**

**Evidence sources**

- Stage A: `Siddipet\Damarakunta\results\stageA_input_validation\stageA_1`, including `validate_damarakunta_inputs.py` and its read-only validation outputs.
- Additional raster checks and file listings supplied on 2026-10-24.
- Subsequent Phase B boundary diagnostic: `Siddipet\Damarakunta\results\run_20261029_01\stageB\_boundary_mask_diag_v1`.
- Boundary diagnostic script: `scripts\dk_stageB_boundary_mask_diag_v1.py`.
- Related connectivity evidence: `stageB\_c0002_roadcell_diag_v1`.

**Evidence labels**

- **Verified:** Directly measured, reproduced or listed in the available diagnostic output.
- **Unverified:** Not independently checked or not established by the available evidence.
- **Interpretation:** A reasoned explanation supported by measurements, but not an independent ground-truth finding.

## 1. Rasters (Verified)

| Input (config key) | File | Grid | Valid inside polygon | Notes |
|---|---|---|---|---|
| Imagery (`raster`) | `aligned\damarakunta_esri_highres_mosaic_0p6m.tif` | EPSG:32644; 11,296 × 7,171 px; 0.6 m; uint8 RGB | 100% | Bounding box: 6,777.6 × 4,302.6 m = 29.16 km², compared with polygon area of 18.466 km² (ratio 1.58). A reported 3.32% of the bounding box is all-zero (0.967 km²). This approximately matches the corner tile that would complete the 1,800 m grid (1,377.6 × 702.6 m = 0.968 km²): 11 tiles exist and 12 are implied. The blank corner lies outside the polygon. |
| `pred_classes` | Path configured in `configs\damarakunta.json`; exact path was not shown in the available output | Same grid as the mosaic | 100% | Class IDs 1–7; nodata 0. |
| `building_prob` | Same folder as configured prediction outputs | Same grid; uint8 | 100% | Channel scaling 0–255, according to `run_rural_planning_pipeline.py`. |
| `worldcover` | `aligned\damarakunta_worldcover_10m.tif` | EPSG:32644; 679 × 432; 10 m | 99.90% | 178 invalid cells inside the polygon (0.0964% of 184,646 cells). |
| `cost` | `aligned\damarakunta_cost_surface_10m.tif` | Same grid; float32; nodata -9999 | 99.31% | Values 2.09–12.0. There are 1,276 invalid cells inside: 178 associated with invalid WorldCover, 224 water cells and 874 cells with invalid slope. Total: 0.691% of 184,646 cells. The count matches the reported Phase B input validation. |
| DEM | `aligned\damarakunta_dem_30m.tif` | EPSG:32644; 30 m; float32 | Not applicable | Elevation range 564.3–625.8 m, giving 61.5 m of relief. Approximately 37.3% is masked outside the boundary. |
| Slope | `aligned\damarakunta_slope_10m.tif` | 10 m; float32 | Not separately quantified here | Reported range 0.02–27.7 degrees; 37.38% masked. Derived from the 30 m DEM slope, so the 10 m values are resampled/interpolated rather than independent 10 m terrain measurements. |
| Prohibited mask | `aligned\damarakunta_prohibited_mask_10m.tif` | 10 m; uint8, values 0/1 | Not separately quantified here | Reported 37.49% of the grid is blocked. This is a computational planning mask, **not a legal or land-ownership layer**. |

All listed rasters share EPSG:32644. According to the original validation, imagery, prediction rasters, WorldCover and cost bounds fully contain the village bounding box. The original checks read the CRS and masks of the DEM, slope and prohibited mask, but did not compare their bounds with the polygon.

The subsequent boundary diagnostic additionally verified the relationship between the cost, WorldCover, slope and prohibited-mask values across the entire 432 × 679 grid. Those results are documented in Section 7.

## 2. Vectors (Verified)

| Input | File | Result |
|---|---|---|
| Boundary | `study_area\damarakunta_boundary.gpkg`, layer `village_boundary` | One valid Polygon in EPSG:32644. Source: TGRAC service. **Not compared with an independent boundary.** |
| Roads | `reference\tgrac_road_network.gpkg` | 43 MultiLineString features; 0 invalid geometries and 0 duplicates in the original validation. A subsequent read-only boundary diagnostic measured 93,496.76 m of total road geometry, of which 41,789.51 m (44.70%) lies outside the study-area polygon. Twenty of the 43 features have at least one outside portion. This contradicts the earlier statement that all road features were inside the polygon (clipped or filtered). The reason for the discrepancy has not been established. Source: TGRAC `Schools/MapServer/20`. Completeness, connectivity and external road usability have not been independently assessed. |
| Facilities | `reference\damarakunta_priority_facilities.gpkg`, layer `priority_facilities` | Four valid Point features, reported inside the village. Facility positional accuracy has not been independently verified. |
| Evaluation windows and building references | `windows`; `reference_buildings`; `reference\manual_building_labels` | Six evaluation-window polygons; `reference_buildings` has 0 features and manual building labels are empty. No building ground truth was available in these inputs. |

### Road-layer boundary measurement

The subsequent diagnostic calculated road geometry outside the study-area polygon using per-feature `geometry.difference(polygon)` in EPSG:32644. The dissolved-union measurement returned the same outside length.

| Measurement | Result |
|---|---:|
| Total TGRAC road geometry | 93,496.76 m |
| Road geometry outside polygon | 41,789.51 m |
| Outside proportion | 44.70% |
| Features with any outside portion | 20 of 43 |
| Farthest outside vertex from polygon | 9,885.16 m |

These are geometric measurements. They do not establish whether external road segments are physically usable, legally accessible or correctly represented in the source data.

## 3. Provenance Dates (Verified from File Times)

| Data | Reported file times |
|---|---|
| TGRAC reference downloads (roads, health, anganwadi and sub-centres) | 5 October 2026, 11:41 |
| School files | 5 October 2026, 12:02–12:04 |
| Esri imagery tiles | 4 October 2026, 20:29–20:44 |
| Imagery mosaic | 4 October 2026, 20:53 |
| Terrain, cost and mask rasters | 12 October 2026, 17:12–17:30 |
| Priority facilities | 12 October 2026, 17:26 |

Imagery capture dates are **unknown**; they were not stored with the available export. File modification times are provenance clues and do not establish when the source imagery was captured or when the underlying features were surveyed.

## 4. Licence and Source Status

| Source | Status |
|---|---|
| Esri World Imagery export (mosaic and tiles) | **Unverified.** The project's `IMAGERY_EXPORT_PLAN_REVIEW.md`, Section 2, records a terms summary concerning offline use and Content Packages. The mosaic has not been modified or re-exported as part of this validation. Confirm the applicable licence and terms before publication or redistribution. |
| DEM `n17_e078_1arc_v3` | The filename suggests SRTM-style 1 arc-second data, but the exact source, licence and applicable terms have not been recorded in the project evidence presented here. |
| ESA WorldCover 2021 v200 | Licence and applicable terms have not been recorded in the project evidence presented here. |
| TGRAC layers | State-government service. Applicable use and redistribution terms have not been checked. Boundary accuracy, road completeness and facility accuracy are unverified. |
| School compound polygons | Creation method is unknown; no creation script was found in the reviewed project materials. |

These statuses describe the evidence available in the project; they are not legal determinations.

## 5. Limitations That Matter Downstream

- **Imagery coverage:** The mosaic has a blank corner outside the village polygon. Processing the entire raster bounding box without applying the study-area mask may expose a model or extraction stage to all-zero pixels.
- **Terrain resolution:** The DEM is 30 m, and slope values on the 10 m grid are resampled/interpolated. The 10 m grid spacing should not be interpreted as 10 m terrain-source resolution.
- **Terrain-related routing failure:** One target, C12, reportedly failed on a cell with a slope of 10.349 degrees in the Phase B results. This is a reported planning outcome, not an independent terrain-accuracy assessment.
- **Facility locations:** Facility positions have not been independently verified. The sub-centre has two TGRAC positions 235.7 m apart.
- **Building ground truth:** No building reference features or manual building labels were available in the reported inputs, so segmentation accuracy cannot be calculated from these materials.
- **Road-layer extent:** The later boundary diagnostic found that 44.70% of the measured TGRAC road geometry lies outside the study-area polygon. The cause of the discrepancy with the original description has not been established.
- **Boundary uncertainty:** The study-area polygon has not been compared against an independent boundary source. The correctness of the boundary therefore remains unverified.
- **External roads:** Road geometry outside the polygon has not been independently checked for real-world existence, usability, access rights or physical passability.
- **Planning mask semantics:** The prohibited mask reflects computational exclusions in the cost-surface generation process. It must not be interpreted as evidence of legal restrictions, ownership or rights of way.

## 6. Not Checked in Stage A

The original Stage A validation did not establish:

- Whether the study-area boundary agrees with an independent administrative or surveyed boundary.
- The imagery's native detail, source capture dates or independent imagery accuracy.
- Prediction-raster accuracy or visual quality. The reported prediction checks were limited to grid, validity and class IDs.
- Whether TGRAC road geometry is complete, physically usable or connected in the real world.
- Whether road geometry outside the polygon is valid for the intended planning domain.
- Whether the school compound polygons were generated consistently or independently verified.
- Whether facility coordinates reflect their actual entrances or usable access points.
- Whether any proposed route is legally accessible, physically passable or suitable for construction.

The later boundary diagnostic provides additional measurements, but it does not resolve these outstanding validation questions.

## 7. Subsequent Boundary Diagnostic and C0002 Connectivity Limitation (Phase B)

**Evidence location:** `Siddipet\Damarakunta\results\run_20261029_01\stageB\_boundary_mask_diag_v1`

**Diagnostic script:** `scripts\dk_stageB_boundary_mask_diag_v1.py`

This section records a subsequent read-only diagnostic; its measurements were not part of the original Stage A validation.

### 7.1 Validation and reproducibility

The diagnostic's reconstruction gate passed. The rebuilt results matched the recorded counts and component sizes, and the relevant cost, WorldCover and road input hashes matched the Stage B manifest. The diagnostic reported 11 input files hashed before and after, with no input changes detected.

| Validation check | Reproduced result |
|---|---:|
| Road-line-covered grid cells | 8,061 |
| Road cells dropped as impassable | 1,567 |
| Cells with invalid cost and prohibited mask greater than zero | 1,564 |
| Cells in the recorded blocked connection chain | 36 |
| Recorded road-component sizes | Matched |

### 7.2 Relationship between the polygon and blocked cells

Of the 1,564 road-line-covered cells with both invalid cost and a prohibited-mask value greater than zero:

- 1,532 cells (98.0%) had centres outside the study-area polygon.
- These outside cell centres were a median 254.2 m from the boundary, with a reported range of 0.1–1,709.6 m.
- The remaining 32 cells were inside the polygon, all within 23.3 m of its boundary. Their median distance to the boundary was 4.1 m.

The 36 cells in the minimum blocked chain associated with C0002's isolated attachment component were distributed as follows:

- 33 cells outside the polygon.
- Three cells inside the polygon, each within 8.4 m of the boundary.

The diagnostic also found that none of the 6,494 passable road-line-covered cells had centres outside the polygon. This is consistent with the raster-generation and cost-validity rules used by the planning grid.

### 7.3 Raster-generation mechanism

The diagnostic reproduced the documented processing rules across the full 432 × 679 grid:

- All 108,682 cells whose centres were outside the polygon had invalid WorldCover, invalid slope, invalid cost and prohibited-mask value 1.
- Within the polygon, 178 cells had invalid WorldCover, 961 had invalid slope, and 1,276 had prohibited-mask value 1.
- The cost-surface generation code sets cost to NaN and prohibited mask to 1 under the same land-cover/slope validity condition. These two layers therefore reflect the same computational exclusion rule by construction; the prohibited mask is not an independent assessment of legal restrictions.

The measurements support boundary-related blocking as the main explanation for the 1,564 affected road cells. They do not establish that the polygon itself is incorrect.

### 7.4 Interior cells and DEM nodata

Of the 32 affected cells whose centres were inside the polygon:

- 29 fell on a masked 30 m DEM cell.
- Three had a valid DEM cell and finite slope.
- WorldCover was finite for 21 of the 32 cells.

The diagnostic did not separately establish the cause of the invalid cost/prohibited status for the remaining three cells. Therefore, the DEM edge mask accounts for most of the affected interior cells, but the available measurements do not fully explain all 32.

### 7.5 C0002's isolated road component

The connectivity diagnostic identified C0002's attachment component as a separate component containing five road cells. The nearest main-component cell was 155.24 m away centre-to-centre.

The minimum blocked chain linking this isolated component to the main component contains 36 road-line-covered cells, of which 33 lie outside the study-area polygon and three lie inside near the boundary. The results indicate that the isolated component is primarily associated with road geometry crossing outside the current planning domain before re-entering it.

This is an interpretation of the planning-grid evidence. The diagnostic did not establish whether the external road segments are real, physically usable or legally accessible. It also did not independently verify the study-area boundary or demonstrate a defect in the routing algorithm.

### 7.6 Road geometry near the boundary

The diagnostic measured the following TGRAC road lengths inside the polygon and within the specified distances of its boundary:

| Distance from boundary | Road length inside polygon |
|---|---:|
| Within 10 m | 430.71 m |
| Within 30 m | 1,427.30 m |
| Within 60 m | 3,196.49 m |

These values describe road geometry in boundary buffers; they do not indicate road quality, usability or accessibility.

### 7.7 Interpretation and restrictions

The findings support documenting C0002's isolated component as a **boundary-truncation limitation of the current planning domain**. The evidence also corrects the earlier description of the TGRAC road layer: substantial road geometry lies outside the study-area polygon.

No blocked cell was made passable, and no routing was performed outside the polygon as part of this diagnostic. The results are planning-grid measurements only. They do not establish legal access, ownership, physical passability, construction suitability, or a demonstrated defect in the planner.

Before changing the boundary, masks, cost surface or routing behaviour, the boundary and external road geometry would need independent review. Until then, preserve the current diagnostic results and treat the cause of the discrepancy between the original road-layer description and the measured geometry as unresolved.

---

**Document maintenance note:** Section 1 records the original Stage A raster checks; Section 2 incorporates the later road-geometry measurement; Section 7 preserves the subsequent Phase B diagnostic as a separately dated body of evidence. Keep these evidence scopes distinct when using this document in a report or dissertation.