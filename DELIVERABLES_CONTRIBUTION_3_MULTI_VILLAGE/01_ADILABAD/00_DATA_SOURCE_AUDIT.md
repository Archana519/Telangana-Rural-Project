# Data-source audit: Adilabad (Tier 1, urban / peri-urban) - Contribution 3, village 1

Everything below was read, hashed and counted by `python -m src.multivillage.run --village adilabad_urban`. Nothing here is field-verified.
The Phase 1 / Stage B deliverables (`DELIVERABLES_DAMARAKUNTA_STAGE_B/`, git tree `4e5cedcefcfb9231074a10667e8050f4650d8766`) are read-only inputs to the comparison.

## 1. Study window

| item | value |
|---|---|
| Name | Adilabad (urban / peri-urban window) |
| Administrative unit | Adilabad Urban mandal, Adilabad district, Telangana (geoBoundaries ADM3 shape `7132399B19105201144494`) |
| Why this window | the mandal polygon is 17.75 km2, inside the requested 15-20 km2 range and close to Damarakunta (18.47 km2); it is an administrative polygon, not a hand-drawn box |
| Centroid (WGS84) | 19.68183 N, 78.52831 E |
| Bounding box, EPSG:32644 (x_min, y_min, x_max, y_max, m) | 238708.4, 2175334.5, 242937.5, 2180968.7 |
| Bounding box, WGS84 (lon_min, lat_min, lon_max, lat_max) | 78.50750, 19.65641, 78.54815, 19.70725 |
| Area | 17.75 km2 |
| Planning grid | 424 x 564 cells at 10 m; 177,533 cells inside the polygon; 0.62% of them blocked (water, slope > 25 degrees) |

Caveat: the geoBoundaries ADM3 layer is the 2018 Local Government Directory release; it may differ from the municipal limits in use today. The window therefore contains the urban core plus a rural/peri-urban fringe (about 60% of cells are not WorldCover built-up).

## 2. Input layers, direct endpoints, licences, hashes

| layer | provider | endpoint | release | licence | resolution | sha256 | rows |
|---|---|---|---|---|---|---|---|
| boundary | geoBoundaries gbOpen (wmgeolab); original source Pathways Data Pvt. Ltd. / lgdirectory.gov.in | https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3.geojson | gbOpen IND ADM3, boundary year 2018, built Dec 12, 2023 | Open Data Commons Open Database License 1.0 (geoBoundaries metadata JSON) | polygon (sub-district / mandal) | f9c38b47f2b8755a... |  |
| boundary (metadata) | geoBoundaries | https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3-metaData.json |  | ODbL 1.0 |  | 061f7c25425f86c0... |  |
| roads | Overture Maps Foundation (transportation theme; OSM-derived) | https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-10-21.0/theme=transportation/type=segment/ | 2026-10-21.0 | ODbL 1.0 (OpenStreetMap-derived); licence per the Overture Maps documentation (docs.overturemaps.org/attribution), NOT re-verified from this sandbox (host unreachable); the per-record `license` field is empty | vector, subtype=road | 795f4a2f585118e6... | 4850 |
| buildings | Overture Maps Foundation (buildings theme): OpenStreetMap + Google Open Buildings v3 polygons | https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-10-21.0/theme=buildings/type=building/ | 2026-10-21.0; source records: Google Open Buildings version 2024-04-16; OpenStreetMap update years 2018-2026 | per record: OpenStreetMap = ODbL 1.0; Google Open Buildings = CC BY 4.0 / ODbL 1.0; licence per the Overture Maps documentation (docs.overturemaps.org/attribution), NOT re-verified from this sandbox (host unreachable); the per-record `license` field is empty | vector polygons | 141a2caee60e8cb9... | 24924 |
| facilities | Overture Maps Foundation (places theme) | https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-10-21.0/theme=places/type=place/ | 2026-10-21.0 | CDLA-Permissive-2.0; licence per the Overture Maps documentation (docs.overturemaps.org/attribution), NOT re-verified from this sandbox (host unreachable); the per-record `license` field is empty | points | 7407718f9159fc0e... | 738 |
| slope | derived from the Copernicus DEM (Sobel on the 30 m DEM, bilinear to 10 m: Stage B method) | derived |  | same as the DEM | 10 m | 9422469cc75c0544... |  |

Full machine-readable version: `input_manifest.csv` (complete SHA-256 values, byte sizes, access time, notes).
Overture layers are read from the pinned release `2026-10-21.0` by an anonymous S3 query (the endpoint above); the hash is that of the clipped extract written to `data/villages/adilabad_urban/`, because a query result has no single file hash.
Licence status: ESA WorldCover (CC BY 4.0) and the Copernicus DEM are as stated by their providers; the geoBoundaries licence (ODbL 1.0) was read from its own metadata JSON; the Overture licences are from the Overture documentation, which could not be opened from this sandbox, so they are flagged "not re-verified". OSM-derived layers are ODbL (share-alike, attribution to OpenStreetMap contributors).
Not used: TGRAC (the Damarakunta road, facility and boundary source), Survey of India / BharatMaps, OSM Overpass / Nominatim, Zenodo and the Google Open Buildings site: none is reachable from the execution sandbox (checked), so no value was taken from them.

## 3. Facilities (schools, health, government offices)

Source: Overture `places` within 4 km of the window (107 school/health/government candidates, 83 inside the window). Overture does not say whether a school or clinic is public, so private ones are included; anganwadis and sub-centres do not exist as categories.
Verification (the Damarakunta rules): inside the window; a detected footprint within 20 m of the point; and a manual review for mis-geocoded records (several records carry Pakistani place names, e.g. "Faisalabad", "Umerkot", "Jaranwala", "Mirpurkhas", and are excluded).

| facility_type | EXCLUDED_MISGEOCODED_OR_NOT_A_FACILITY | NO_FOOTPRINT_WITHIN_20M_NOT_USED | VERIFIED_USED |
|---|---|---|---|
| government | 3 | 0 | 7 |
| health | 2 | 0 | 20 |
| school | 6 | 1 | 44 |

Result: **71 verified facilities** are used as targets in the facility phase (44 schools, 20 health, 7 government). Every candidate with coordinates, distance to the nearest footprint and the reason for any exclusion is in `verified_facilities.csv`.
Unlike the Damarakunta anganwadi (371 m from the nearest footprint), the only candidate without a footprint within 20 m was a school ("Vivekananda High School", 20.5 m: it misses the rule by 0.5 m); in a dense urban fabric the 20 m test is weak evidence because nearly every point is within 20 m of some footprint.

## 4. Building footprints: which method and why

StrongDINOv2Seg inference was **not** run for Adilabad, for three documented reasons: (i) the model weights are not in the repository and their location was never recorded (the Stage B documentation says the same: "segmentation is not re-run because the model-weight location is not recorded"); (ii) the 0.6 m Esri World Imagery used for Damarakunta has an unresolved licence for derived products and cannot be fetched from this sandbox; (iii) no open sub-metre imagery is reachable (Sentinel-2, 10 m, cannot resolve houses). The brief allows verified open footprints in that case, so the footprints are the Overture buildings layer.

| item | value |
|---|---|
| Footprint polygons in the window | 24,924 (OpenStreetMap 18,846; Google Open Buildings v3, version 2024-04-16: 6,078); every Overture record has exactly one source, so there are no duplicate polygons between the two |
| OSM edit years | mostly 2018 (the OSM building import), see `buildings.gpkg` |
| Confidence | Google polygons carry a model confidence (median 0.76); OSM polygons are human-mapped and treated as 1.0 |
| Quality classes (heuristic, not verified) | LARGE_POSSIBLE_MERGE 581, LOWCONF_EXCLUDED 512, PLAUSIBLE 16,951, REVIEW 710, SMALL_EXCLUDED 6,170 |
| House footprints (area >= 30 m2, confidence >= 0.7) | 18,242 |
| Median footprint area | 66.6 m2 (Damarakunta candidates: 235.8 m2) |
| Proxy agreement check | not applicable in the Damarakunta sense (no independent detector to compare with). Instead: 96.4% of all house points, and 79.2% of road-gap house points, fall on a WorldCover built-up cell - a land-cover consistency check, not an accuracy figure |

Consequence: footprints include non-residential buildings (no use type exists), so "house" means "building footprint of at least 30 m2" and the road-gap set contains some large structures (e.g. long barrack-like blocks visible on the maps).

## 5. How the Stage B workflow was applied, and every deviation

| Stage B step | Damarakunta | Adilabad (this run) | deviation |
|---|---|---|---|
| 1 boundary, roads, facilities | TGRAC village polygon, TGRAC roads and facilities | geoBoundaries mandal polygon, Overture roads (OSM) and places | different sources (TGRAC unreachable) |
| 2 land cover, DEM, slope | WorldCover 10 m; ~30 m DEM (SRTM-type, source unrecorded); Sobel slope | WorldCover 10 m; Copernicus GLO-30 30 m; Sobel slope (same method) | DEM product (documented RMSE 2.3 m between the two over Damarakunta) |
| 3 buildings | StrongDINOv2Seg + OpenCV instance extraction, 163 targets | open footprints (OSM + Google) | method (see section 4) |
| 4 cost surface | WorldCover resistance + slope term, slope > 25 degrees blocked, footprint penalty mu = 4 on cells whose centre lies inside a footprint | identical recipe and parameters (`configs/multivillage/common.yaml`) | none |
| 5 planner | `scripts/plan_network_v2.py` | the same file, imported unchanged; K = 3, passes = 2, snap 30 m, search limit 1,500 m, attach tolerance 15 m | none |
| targets | every candidate inside the boundary (163; 48 within 10 m of a road) | only buildings farther than 30 m from a road (874 of 18,242) | **dense fabric**: 75% of footprints are within 14 m of a road, and the planner's cost grows with the square of the number of targets (874 targets: about 6 minutes per plan; the full 2,190 houses > 20 m: reported in section 6). 30 m is the planner's own snap distance |
| facility phase | 5 facilities planned first, separately | 71 verified facilities planned in a separate phase | more facilities |
| sensitivity | mu = 1, 4 and buffered 20, 100, 1000; random and size-based omissions | mu = 1, 4, 20, 100 (plain), buffered 20 and 100; 10% and 20% random omission x 5 seeds, smallest 10% / 25% | seeds are 1-5 (Stage B's seeds are not recorded) |

## 6. Results at a glance

Two-stage shared plan: 34,359 m of new corridor for 873 of 874 road-gap houses, 26.0% less unique length than independent least-cost routes (Damarakunta: 24.9%). The full comparison with the four baselines is in `routing_strategy_comparison.csv`, the Damarakunta side-by-side in `comparison_vs_damarakunta.md`.

Sensitivity of the headline saving to the target definition (houses farther than D metres from an existing road; D = 30 m is the primary run):

| min_dist_to_road_m | house_targets | routed | unique_len_m | independent_unique_len_m | saving_vs_independent_pct | routes_crossing | len_in_footprints_m | failed | unique_len_per_house_m |
|---|---|---|---|---|---|---|---|---|---|
| 20.0 | 2,190.0 | 2,189.0 | 65,204.4 | 83,525.9 | 21.9 | 815.0 | 4,543.9 | 1.0 | 29.8 |
| 30.0 | 874.0 | 873.0 | 34,358.8 | 46,419.2 | 26.0 | 332.0 | 2,041.1 | 1.0 | 39.3 |
| 50.0 | 296.0 | 296.0 | 15,880.9 | 22,519.7 | 29.5 | 126.0 | 809.9 | 0.0 | 53.7 |

## 7. Limitations specific to this run

* The study window is an administrative mandal polygon, not a revenue-village boundary; Overture/OSM roads and buildings are open crowd-sourced layers of unverified completeness (the OSM buildings are mostly from the 2018 import).
* Targets are building footprints of any use; schools, clinics and offices are not separated from houses in the road-gap set.
* The facility list comes from a commercial-places layer with visible geocoding errors; only a manual review separates the obvious ones, and private/public status is unknown.
* Costs are ordinal units, not rupees; routes are planning alternatives, not engineered roads; no field validation exists.
* The omission scenarios are synthetic removals of open footprints, not measured detection errors, and the footprints are not StrongDINOv2Seg output, so these results show how the Stage B planner behaves on a different building source, not how the segmenter would perform in Adilabad.
