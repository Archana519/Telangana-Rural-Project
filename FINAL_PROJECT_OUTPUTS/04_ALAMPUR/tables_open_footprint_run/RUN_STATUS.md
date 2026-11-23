# Alampur (Alampur town, Jogulamba Gadwal district): run status

Study area: **Alampur (Alampur town)**, a *derived built-up settlement extent* (1.65 km², not an administrative boundary): Overture building footprints around the OpenStreetMap place node (15.87996 N, 78.13508 E),
clusters linked over gaps of 250 m, outline = footprints buffered +60 m / -40 m (`configs/multivillage/villages/alampur_boundary.geojson` + `.provenance.json`). OSM maps Alampur only as a point; no polygon exists in OSM, Nominatim or the Overture divisions,
and no LGD / Census polygon is available to the project. A WorldCover-based extent was tried first and discarded (thin slivers, 1.63 km², edge continuity 0.0 %). Edge-continuity check of the chosen polygon: 0.7 % of the edge with built-up land on both sides,
9.1 % of the local built-up extent outside (verdict clean). Covers: Alampur mandal (2018 layer). The district of Jogulamba Gadwal is not the study area.

Done here (sandbox): open data (Overture roads / buildings / places, WorldCover, Copernicus DEM) on the polygon; Esri 0.6 m tiles (6 tiles) and the mosaic (6,672 x 4,324 px, EPSG:32644, git-ignored);
open-footprint routing, **main strategy comparison only** (`--quick`): 3,452 open footprints (PLAUSIBLE 1780, SMALL_EXCLUDED 1306, REVIEW 214, LOWCONF_EXCLUDED 110, LARGE_POSSIBLE_MERGE 42); 370 road-gap targets, 299 routed; 1 verified facilities;
independent unique length 13.4 km, two-stage shared plan 9.9 km (saving 26.4 %); 131 routes cross footprints with the soft penalty (mu = 4).
Not done: the penalty / omission / road-gap sweeps, the whole StrongDINOv2Seg chain (the checkpoint lives on the owner's PC), the 5 m building-clearance network and the master map (they need the segmentation state).

Caveats: only 1 public facility is verified (Overture lists 3 places near Alampur, 2 outside the polygon; the Jogulamba temple town has no school / health / government place in the open data), so facility results are thin;
71 of 370 targets are unrouted (sparse mapped road layer: 368 road segments); Alampur is a small, river-edge town, so shares and lengths are not comparable one-to-one with the larger settlements.
The run log (`run_log_full.json`) is not written by the `--quick` run. PMGSY rate Rs 75 lakh/km is owner-supplied and unverified (illustrative only). `acquired_data_manifest.csv` lists every downloaded input with its SHA-256 and source.

On the PC: `python scripts\run_village_end_to_end.py --village alampur --stage infer`, then `--stage extract`, `--stage route`, `--stage report`, then `python scripts\make_village_map_series.py --village alampur`, then `python scripts\build_final_project_outputs.py`.
