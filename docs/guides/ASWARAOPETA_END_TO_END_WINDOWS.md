# Aswaraopeta (Tier 2, semi-urban): the same end-to-end pipeline on its true boundary

The study area is the **real village / town polygon** of Aswaraopeta (Bhadradri Kothagudem district), not a clipped box and not the 622.59 km² mandal: a box would cut real
boundaries and disconnect houses and roads at the edge. geoBoundaries (cached in the repository) only has the mandal, so the polygon comes from village-level open sources
through `scripts/propose_aoi.py`. Adilabad keeps its full ADM3 polygon (17.75 km²) untouched.

Everything runs on your PC (internet, the StrongDINOv2Seg checkpoint) exactly as for Adilabad (`docs/guides/ADILABAD_END_TO_END_WINDOWS.md`); the scripts are now generic: `--village aswaraopeta`.

> Updated: `propose_aoi.py` now uses the newest OSM / Overture polygons and an edge-continuity check (candidates that cut through built-up land are flagged `CUTS_BUILTUP` and refused by `--pick`); see `docs/guides/UPDATED_BOUNDARIES_WINDOWS.md`, which also covers the updated Adilabad boundary.

## 1. Fetch and fix the true boundary (light; a few minutes)
```powershell
git pull origin main
python scripts\propose_aoi.py --village aswaraopeta
```
It queries OpenStreetMap (Overpass and Nominatim) and the Overture `divisions` theme for polygons named Aswaraopeta / Ashwaraopet, ranks them (name match, inside the mandal, plausible size) and writes
`data\villages\aswaraopeta\aoi_candidates\{candidates.geojson,preview.png}` plus a table in the terminal. Open `preview.png` and, better, the candidates in QGIS or Google Earth on the satellite image:
the polygon must contain the **whole built-up area including the outskirts**. Then fix your choice:
```powershell
python scripts\propose_aoi.py --village aswaraopeta --pick 0            # N = first column of the table
```
This writes `configs\multivillage\villages\aswaraopeta_boundary.geojson` and `aswaraopeta_boundary.provenance.json` (source, id, licence, date, SHA-256). **Commit and push both** (small files) and tell me.

If no source has a village polygon (the table is empty or only has the mandal):
* you hold a village shapefile (LGD / Census / Survey of India): `python scripts\propose_aoi.py --village aswaraopeta --sources --use-file path\to\village.shp --note "LGD village boundary, downloaded <date>"`
* otherwise the last resort is the **derived built-up settlement extent** around the town centre (ESA WorldCover class 50, gaps closed up to 60 m, linked up to 250 m, smoothed; not an administrative boundary and labelled so in the provenance):
  `python scripts\propose_aoi.py --village aswaraopeta --settlement-extent --centre LAT LON` (centre from Google Maps; with internet the Overture division point is tried first).
Tell me which route you used; the papers will state it.

## 2. Run the pipeline
```powershell
python scripts\run_village_end_to_end.py --village aswaraopeta --stage check --hash
python scripts\run_village_end_to_end.py --village aswaraopeta --stage open                  # boundary from the polygon, Overture roads / buildings / places, WorldCover, DEM, open-footprint targets
python scripts\list_facility_candidates.py --village aswaraopeta                              # review facility records; add mis-geocoded / duplicate ones to aswaraopeta_facility_exclusions.csv
python scripts\run_village_end_to_end.py --village aswaraopeta --stage esri                   # Esri tiles for the polygon's bounding box (check the tile plan with --dry-run first)
python scripts\run_village_end_to_end.py --village aswaraopeta --stage mosaic
python scripts\run_village_end_to_end.py --village aswaraopeta --stage infer --smoke
python scripts\run_village_end_to_end.py --village aswaraopeta --stage infer
python scripts\run_village_end_to_end.py --village aswaraopeta --stage extract
python scripts\run_village_end_to_end.py --village aswaraopeta --stage route --workers 4
python scripts\run_village_end_to_end.py --village aswaraopeta --stage report
python scripts\make_village_map_series.py --village aswaraopeta                               # five-map series + compact figure
```
Optional independent check with the Overture footprints (the same two-variant design as Adilabad):
```powershell
python -m src.multivillage.run --village aswaraopeta --steps extract route --workers 4
python -m src.multivillage.run --village aswaraopeta --steps report
```
Then `python scripts\build_final_project_outputs.py` adds `FINAL_PROJECT_OUTPUTS\03_ASWARAOPETA_SEMI_URBAN\` and a column in the master comparison. Commit and push
`DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE\02_ASWARAOPETA_SEGMENTATION` (and `02_ASWARAOPETA` if you ran the check), plus `FINAL_PROJECT_OUTPUTS`.

## Notes
* Same method as Adilabad: identical cost surface, planner settings, 30 m road-gap rule, penalty sweep (μ ∈ {1, 4, 20, 100}), omission seeds 1–5; only the study polygon and its footprints differ.
* Outputs of the open-footprint check go to `02_ASWARAOPETA` with the generic tables (Adilabad's open report is Adilabad-specific); the segmentation run to `02_ASWARAOPETA_SEGMENTATION`.
* If the polygon is much larger than about 25 km², `--dry-run` on the esri stage shows the tile count; the inference rate to expect is about 4 s per 560-px tile on CPU (Adilabad: 391 tiles in 1,583.5 s).
