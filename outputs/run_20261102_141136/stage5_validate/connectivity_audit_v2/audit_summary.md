# Stage B connectivity / GIS audit v2 (read-only)

Generated 2026-11-02 14:45 by `dk_stageB_connectivity_audit_v2.py`. No route was regenerated and no input file was modified (sha256 of 19 inputs identical before and after: YES).

Model connectivity on a planning grid only. Nothing here establishes legal access, ownership, passability or a field-verified junction.

## Rule and tolerances

- Strict touch tolerance 0.01 m: the planner draws the last vertex ON the declared network (nearest point), so a correct link has distance ~0.
- Planner tolerance `attach_tol_m` is read from each run's `config_stageB.json`; a link within it but not touching is reported INFO, beyond it FAIL.
- Length tolerance 0.01 m for geometry vs `len_m` (both metres in EPSG:32644); 0.02 m for edges + connectors (start snap exported to 0.01 m).
- House-phase routes labelled ROAD are checked against the planner's declared combined network (road line UNION facility routes); G09 reports separately when the label (end cell is a road cell) and the snapped geometry (a facility route) differ.
- Off-main attachments: G04 keeps the planner's raster definition of the main component (FAIL); G10 adds source road-line component evidence (INFO) and does not prove the rasterisation cause.
- A target counts as geometrically connected only if every link of its attach chain is TOUCH/WITHIN_TOL, there is no cycle or dangling parent, and the chain ends on a road; crossings are never counted as connections.

## Status counts per scenario

| scenario | FAIL | INFO | PASS |
|---|---|---|---|
| S2_fac_C0_s25_final_x1 | 2 | 8 | 25 |
| S2_fac_C0_s25_final_x4 | 2 | 8 | 25 |

## Checks

### S2_fac_C0_s25_final_x4

| check_id | status | check | detail |
|---|---|---|---|
| I01 | PASS | run directory and required files exist | 9 required files present |
| I02 | INFO | attach tolerance (planner attach_tol_m) | attach_tol_m=15.0, snap_m=30.0 |
| I03 | PASS | road file hash equals the hash recorded when the run was made | recorded=3fa25aa8f2ac339c506c486a7b2cda7e9596c2a133b3dca8140c653c1db3db01; now=3fa25aa8f2ac339c506c486a7b2cda7e9596c2a133b3dca8140c653c1db3db01 |
| I04:routes_network_houses | PASS | layer routes_network_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:routes_network_facilities | PASS | layer routes_network_facilities: CRS EPSG:32644, no null/empty/invalid geometry | n=5 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:routes_roads_only_houses | PASS | layer routes_roads_only_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:routes_independent_houses | PASS | layer routes_independent_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:routes_independent_facilities | PASS | layer routes_independent_facilities: CRS EPSG:32644, no null/empty/invalid geometry | n=5 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:routes_straight_line_houses | INFO | layer routes_straight_line_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=7 (baseline/alternative layer, not part of the network plan) |
| I04:routes_length_only_houses | PASS | layer routes_length_only_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:targets_houses | PASS | layer targets_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:targets_facilities | PASS | layer targets_facilities: CRS EPSG:32644, no null/empty/invalid geometry | n=5 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:stageA_alternatives_houses | PASS | layer stageA_alternatives_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=316 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:road_cells_main_component | PASS | layer road_cells_main_component: CRS EPSG:32644, no null/empty/invalid geometry | n=1 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| C01:house | PASS | house target coverage: scenario = status = route layer = connectivity = target points, no duplicates, none failed | scenario=163 status=163 routes=163 connectivity=163 target_points=163 failed=0 duplicates=0 |
| C01:facility | PASS | facility target coverage: scenario = status = route layer = connectivity = target points, no duplicates, none failed | scenario=5 status=5 routes=5 connectivity=5 target_points=5 failed=0 duplicates=0 |
| C02 | PASS | route cand_id equals scenario_targets cand_id for the same target_id (houses) | mismatches=0 of 163 |
| P01:house | FAIL | planner evidence (house): local endpoint fields AND wider-network fields all true, no hard violations | n=163; true-counts {'reaches_main_road_component': 162, 'planner_connected_to_roads': 163, 'cell_graph_connected': 163, 'planner_ok_local': 163, 'endpoint_ok': 163}; hard_violations>0: 0; chain_terminal {'ROAD': 163}; attach_class {'ROAD': 95, 'HOUSE_ROUTE': 62, 'FACILITY_ROUTE': 6}. Local (planner_ok_local, endpoint_ok) differ from wider-network (reaches_main_road_component, planner_connected_to_roads, cell_graph_connected) evidence. |
| P01:facility | PASS | planner evidence (facility): local endpoint fields AND wider-network fields all true, no hard violations | n=5; true-counts {'reaches_main_road_component': 5, 'planner_connected_to_roads': 5, 'cell_graph_connected': 5, 'planner_ok_local': 5, 'endpoint_ok': 5}; hard_violations>0: 0; chain_terminal {'ROAD': 5}; attach_class {'ROAD': 4, 'FACILITY_ROUTE': 1}. Local (planner_ok_local, endpoint_ok) differ from wider-network (reaches_main_road_component, planner_connected_to_roads, cell_graph_connected) evidence. |
| P02 | PASS | target_status.csv and connectivity_checks.csv agree (houses) | mismatches per field: {'reaches_main_road_component': 0, 'attach_class': 0, 'chain_depth': 0, 'end_snap_m': 0}; rows compared=163 |
| G01 | PASS | route starts at its target point (<=0.01 m) | PASS=168 |
| G02 | PASS | route end lies on declared network (touch <= 0.01 m; planner tolerance 15.0 m) | PASS=168 |
| G03 | PASS | every attach chain is geometrically unbroken and ends on ROAD (no cycle / dangling parent) | PASS=168 |
| G09 | INFO | label vs snapped geometry for house routes labelled ROAD (INFO = label says road cell, drawn end snapped to a facility route) | INFO=2; PASS=93 |
| G10 | INFO | off-main attachments: source road-line connectivity vs raster road-cell connectivity (INFO only, explanatory) | INFO=1 |
| G04 | FAIL | chain terminal lies on the planner's main road component and agrees with reaches_main_road_component | FAIL=1; PASS=167 |
| G05 | PASS | route groups: all routes belong to one connected group containing the road network | groups=1; groups not containing ROAD=0; routes in them=0 |
| G06 | PASS | proposed routes are labelled as planning proxies and are held in layers separate from the existing roads | distinct status values: ['UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD'] |
| G07 | INFO | share of proposed route length lying within 1 m of existing roads (should be small; routes attach to roads, not trace them) | 137.10 m of 5318.35 m (2.58%) |
| G08:0.01 | INFO | independent connected components of the source road lines at joining tolerance 0.01 m | components=14; largest=44760.8 m of 51707.3 m; planner road_components.csv lists 12 cell components (is_main=1). Informational: planner components are raster cells, not line topology. |
| G08:10 | INFO | independent connected components of the source road lines at joining tolerance 10 m | components=10; largest=48848.1 m of 51707.3 m; planner road_components.csv lists 12 cell components (is_main=1). Informational: planner components are raster cells, not line topology. |
| L01 | PASS | geometry length equals stored len_m (/diff/ <= 0.01 m; EPSG:32644 metres) | PASS=168 |
| L02 | PASS | stored len_m equals status CSV length (/diff/ <= 0.01 m) | PASS=168 |
| L04 | PASS | routes without route_edges rows: len_m equals start snap + end snap (zero grid edges; /diff/ <= 0.02 m) | PASS=37 |
| L03 | INFO | stored len_m equals grid-edge sum + connectors (/diff/ <= 0.02 m; facilities NOT_VERIFIABLE because the facility start-connector length is not exported separately) | NOT_VERIFIABLE=42; PASS=126 |

### S2_fac_C0_s25_final_x1

| check_id | status | check | detail |
|---|---|---|---|
| I01 | PASS | run directory and required files exist | 9 required files present |
| I02 | INFO | attach tolerance (planner attach_tol_m) | attach_tol_m=15.0, snap_m=30.0 |
| I03 | PASS | road file hash equals the hash recorded when the run was made | recorded=3fa25aa8f2ac339c506c486a7b2cda7e9596c2a133b3dca8140c653c1db3db01; now=3fa25aa8f2ac339c506c486a7b2cda7e9596c2a133b3dca8140c653c1db3db01 |
| I04:routes_network_houses | PASS | layer routes_network_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:routes_network_facilities | PASS | layer routes_network_facilities: CRS EPSG:32644, no null/empty/invalid geometry | n=5 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:routes_roads_only_houses | PASS | layer routes_roads_only_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:routes_independent_houses | PASS | layer routes_independent_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:routes_independent_facilities | PASS | layer routes_independent_facilities: CRS EPSG:32644, no null/empty/invalid geometry | n=5 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:routes_straight_line_houses | INFO | layer routes_straight_line_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=7 (baseline/alternative layer, not part of the network plan) |
| I04:routes_length_only_houses | PASS | layer routes_length_only_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:targets_houses | PASS | layer targets_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=163 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:targets_facilities | PASS | layer targets_facilities: CRS EPSG:32644, no null/empty/invalid geometry | n=5 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| I04:stageA_alternatives_houses | PASS | layer stageA_alternatives_houses: CRS EPSG:32644, no null/empty/invalid geometry | n=314 crs=EPSG:32644 null=0 empty=0 invalid=0 (baseline/alternative layer, not part of the network plan) |
| I04:road_cells_main_component | PASS | layer road_cells_main_component: CRS EPSG:32644, no null/empty/invalid geometry | n=1 crs=EPSG:32644 null=0 empty=0 invalid=0 |
| C01:house | PASS | house target coverage: scenario = status = route layer = connectivity = target points, no duplicates, none failed | scenario=163 status=163 routes=163 connectivity=163 target_points=163 failed=0 duplicates=0 |
| C01:facility | PASS | facility target coverage: scenario = status = route layer = connectivity = target points, no duplicates, none failed | scenario=5 status=5 routes=5 connectivity=5 target_points=5 failed=0 duplicates=0 |
| C02 | PASS | route cand_id equals scenario_targets cand_id for the same target_id (houses) | mismatches=0 of 163 |
| P01:house | FAIL | planner evidence (house): local endpoint fields AND wider-network fields all true, no hard violations | n=163; true-counts {'reaches_main_road_component': 162, 'planner_connected_to_roads': 163, 'cell_graph_connected': 163, 'planner_ok_local': 163, 'endpoint_ok': 163}; hard_violations>0: 0; chain_terminal {'ROAD': 163}; attach_class {'ROAD': 92, 'HOUSE_ROUTE': 66, 'FACILITY_ROUTE': 5}. Local (planner_ok_local, endpoint_ok) differ from wider-network (reaches_main_road_component, planner_connected_to_roads, cell_graph_connected) evidence. |
| P01:facility | PASS | planner evidence (facility): local endpoint fields AND wider-network fields all true, no hard violations | n=5; true-counts {'reaches_main_road_component': 5, 'planner_connected_to_roads': 5, 'cell_graph_connected': 5, 'planner_ok_local': 5, 'endpoint_ok': 5}; hard_violations>0: 0; chain_terminal {'ROAD': 5}; attach_class {'ROAD': 4, 'FACILITY_ROUTE': 1}. Local (planner_ok_local, endpoint_ok) differ from wider-network (reaches_main_road_component, planner_connected_to_roads, cell_graph_connected) evidence. |
| P02 | PASS | target_status.csv and connectivity_checks.csv agree (houses) | mismatches per field: {'reaches_main_road_component': 0, 'attach_class': 0, 'chain_depth': 0, 'end_snap_m': 0}; rows compared=163 |
| G01 | PASS | route starts at its target point (<=0.01 m) | PASS=168 |
| G02 | PASS | route end lies on declared network (touch <= 0.01 m; planner tolerance 15.0 m) | PASS=168 |
| G03 | PASS | every attach chain is geometrically unbroken and ends on ROAD (no cycle / dangling parent) | PASS=168 |
| G09 | INFO | label vs snapped geometry for house routes labelled ROAD (INFO = label says road cell, drawn end snapped to a facility route) | INFO=2; PASS=90 |
| G10 | INFO | off-main attachments: source road-line connectivity vs raster road-cell connectivity (INFO only, explanatory) | INFO=1 |
| G04 | FAIL | chain terminal lies on the planner's main road component and agrees with reaches_main_road_component | FAIL=1; PASS=167 |
| G05 | PASS | route groups: all routes belong to one connected group containing the road network | groups=1; groups not containing ROAD=0; routes in them=0 |
| G06 | PASS | proposed routes are labelled as planning proxies and are held in layers separate from the existing roads | distinct status values: ['UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD'] |
| G07 | INFO | share of proposed route length lying within 1 m of existing roads (should be small; routes attach to roads, not trace them) | 135.83 m of 4940.66 m (2.75%) |
| G08:0.01 | INFO | independent connected components of the source road lines at joining tolerance 0.01 m | components=14; largest=44760.8 m of 51707.3 m; planner road_components.csv lists 12 cell components (is_main=1). Informational: planner components are raster cells, not line topology. |
| G08:10 | INFO | independent connected components of the source road lines at joining tolerance 10 m | components=10; largest=48848.1 m of 51707.3 m; planner road_components.csv lists 12 cell components (is_main=1). Informational: planner components are raster cells, not line topology. |
| L01 | PASS | geometry length equals stored len_m (/diff/ <= 0.01 m; EPSG:32644 metres) | PASS=168 |
| L02 | PASS | stored len_m equals status CSV length (/diff/ <= 0.01 m) | PASS=168 |
| L04 | PASS | routes without route_edges rows: len_m equals start snap + end snap (zero grid edges; /diff/ <= 0.02 m) | PASS=37 |
| L03 | INFO | stored len_m equals grid-edge sum + connectors (/diff/ <= 0.02 m; facilities NOT_VERIFIABLE because the facility start-connector length is not exported separately) | NOT_VERIFIABLE=42; PASS=126 |

## Exceptions

92 non-PASS item rows are listed in `connectivity_exceptions.csv` (INFO, FAIL and NOT_VERIFIABLE).

Internal consistency checks (statuses valid, summary fail counts equal item rows, inputs unchanged): PASS.