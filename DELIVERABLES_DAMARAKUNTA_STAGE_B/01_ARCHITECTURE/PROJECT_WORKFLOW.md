> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# Workflow as implemented (from code and run manifests)

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
