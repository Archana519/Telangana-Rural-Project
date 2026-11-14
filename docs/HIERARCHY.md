# Hierarchical routing (Contribution 3): GP -> Mandal -> District

Level 1 (village, Damarakunta) is the completed Stage B pipeline. This adds three coarser tiers that reuse its search engine
(`scripts/plan_network_v2.py::Grid`, 8-connected Dijkstra, no diagonal corner-cutting, hard/soft constraints).

| Level | Module entry point | Nodes routed | Grid | Network rule |
|---|---|---|---|---|
| 2 Gram Panchayat | `build_gp_problem` | hamlet hubs (houses clustered at 150 m) + school / sub-centre / panchayat-office points | 10 m | shared lazy-greedy attachment to existing roads; footprint penalty x4 with **local override** (20 m) around exempt amenities |
| 3 Mandal | `build_mandal_problem` | GP hubs, mandal HQ, PHCs, markets | 30 m | same rule; slope, water (blocked) and forest resistance; existing roads discounted (x0.25) and passable as bridges = road snapping |
| 4 District | `build_district_problem` | mandal HQs, district HQ (root) | 250 m coarse, 30 m fine | coarse shared plan -> graph contraction into chains -> fine refinement in corridor windows |

## Formulation
`c(x) = [c_lc(class(x)) + g(slope(x))] * m(x)`, `m(x) = 1 + (mu-1) 1[footprint] (1 - 1[within r_f of an exempt facility])`.
Land-cost table, slope term and the 25 deg hard limit are in `configs/hierarchy_levels.yaml` and mirror
`scripts/create_damarakunta_cost_surface.py`. Costs are ordinal units, not rupees.
Shared network: the least-cost path of a node to *existing roads union already selected routes*; the node with the smallest
cost/weight is added first (lazy evaluation is exact because marginal costs only fall as the network grows). Heuristic, no optimality claim.

## Memory at district scale
Only the coarse grid (about 57k cells for 60 x 60 km at 250 m) and **one fine window at a time** are in memory. A coarse path is cut
into segments of at most `segment_m`; each is re-routed at `fine_resolution_m` inside a `corridor_m` buffer; a window larger than
`max_fine_cells` is coarsened instead of failing (`fine_degraded` in the metadata). Fine windows are aligned to one global lattice so
neighbouring segments meet on the same cell. If a window has no fine path the coarse segment is kept and flagged `coarse_fallback`.

## Run
```bash
python -m src.routing.run_hierarchy --levels 2 3 4 --data auto --out outputs/hierarchy   # real where files exist, else synthetic
python -m src.routing.run_hierarchy --data synthetic                                       # everything synthetic
python -m pytest tests -q
```
Outputs per level: `<level>_routes.gpkg` (routes_shared, routes_independent, nodes), `_summary.json`, `_metrics.csv`,
`_override.csv` (route with vs without the local override), `_omission.csv` (random omission of units, 3 seeds x 10/20 %), plus
`hierarchy_summary.csv/json` and `data_inventory.json`. Every file records whether it came from real or synthetic inputs.

## What is real and what is not
* Level 2 on Damarakunta uses the repository's real boundary, clipped TGRAC roads, 5 facilities, v8 building footprints and the 163 Stage B
  house targets. The WorldCover/DEM rasters are git-ignored `*.tif`: without them it falls back to a **flat** cost surface and no slope term
  (flagged in the output). Hamlet-hub lengths are not comparable with the Level-1 house-by-house numbers.
* Levels 3 and 4 have no real inputs in the repository yet and run on the seeded synthetic worlds in `src/routing/synthetic_world.py`.
  Their numbers demonstrate that the machinery works; they say nothing about Siddipet.

## Inputs needed for full-scale Siddipet runs (paths are set in `configs/hierarchy_levels.yaml`)
| Level | File(s) | Requirements |
|---|---|---|
| 2 (any GP) | boundary, roads, facilities, buildings, house targets, `*_worldcover_10m.tif`, DEM | EPSG:32644 or any CRS with a defined projection |
| 3 | `Siddipet/_mandal/{markook_boundary,gram_panchayats,roads,facilities}.gpkg`, WorldCover, DEM | GP polygons (optional `houses`, `gp_name`); facilities with `facility_type` containing "Mandal HQ", "PHC"/"Primary Health", "market"; roads NH/SH/MDR/PMGSY or OSM |
| 4 | `Siddipet/_district/{siddipet_boundary,mandals,roads,terminals}.gpkg`, WorldCover, DEM | terminals: points with `kind` (`district_hq` once, `mandal_hq`) and optional `weight` |
