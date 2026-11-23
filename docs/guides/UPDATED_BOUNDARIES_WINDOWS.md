# Current, uncut boundaries for Adilabad and Aswaraopeta (`scripts/propose_aoi.py`)

Both study areas must be the **full, uncut true boundary** of the town / village and must be **current** (not the 2018 geoBoundaries mandal layer). The pipeline never crops or boxes a boundary; it uses the polygon
exactly as fixed with `propose_aoi.py --pick`. Papers are not touched by this work.

## Why Adilabad needs a new boundary
The frozen Adilabad run uses the 2018 geoBoundaries ADM3 polygon "Adilabad Urban" (17.75 km²). The edge-continuity check shows it cuts through continuous built-up land:
built-up on both sides (30 m in / 30 m out) along 14.8 % (2.6 km) of its boundary and 20.9 % (2.44 km²) of the local built-up extent outside it, mainly south of the town.
That run, `01_ADILABAD*` and everything built on it stay **frozen and unchanged**; the updated boundary is a separate village id, `adilabad_urban_updated`, with its own folders:
data `data/villages/adilabad_urban_updated`, work `data/villages/adilabad_updated_esri`, results `01_ADILABAD_UPDATED[_SEGMENTATION]`.

## The fetcher
```powershell
git pull origin main
python scripts\propose_aoi.py --village adilabad_urban        # candidates for the updated Adilabad boundary (searched in the mandal bbox + 5 km)
python scripts\propose_aoi.py --village aswaraopeta           # candidates for Aswaraopeta
```
* Sources (current): OpenStreetMap (Overpass, Nominatim) and the newest Overture release (`divisions`); the release used is recorded (`--overture-release X` pins one). Your own polygon (LGD / Census / municipal
  boundary) goes in with `--use-file path --note "source, date"`; LGD and Census have no open API. Fallback: `--settlement-extent --centre LAT LON` (derived from built-up land; labelled as derived).
* The 2018 geoBoundaries polygon appears as a **reference row** (never pickable) so you can compare.
* Each candidate gets the **edge-continuity check** on ESA WorldCover: `edge_both_pct` (share of its boundary with built-up land on both sides), `outside_pct` / `outside_km2` (share / area of the local built-up extent
  outside the polygon). More than 5 % or 10 % respectively is flagged `CUTS_BUILTUP`; the ranking prefers the cleanest boundary and `--pick` refuses flagged candidates unless you add `--accept-cut`.
* Review `data\villages\<id>\aoi_candidates\preview.png` and the polygon on the Esri imagery: the whole built-up area, including the outskirts, must be inside, and no neighbouring settlement should be swallowed
  (a huge candidate is flagged too large).
* Fix the choice: `python scripts\propose_aoi.py --village adilabad_urban --pick N` (writes `configs\multivillage\villages\adilabad_urban_updated_boundary.geojson` + `.provenance.json`; for Aswaraopeta
  `aswaraopeta_boundary.geojson`). Commit and push both files.

## Running a village on its fixed boundary
```powershell
python scripts\run_village_end_to_end.py --village adilabad_urban_updated --stage check --hash
python scripts\run_village_end_to_end.py --village adilabad_urban_updated --stage open
python scripts\list_facility_candidates.py --village adilabad_urban_updated      # review facility records, add exclusions
python scripts\run_village_end_to_end.py --village adilabad_urban_updated --stage esri --dry-run   # the new bounding box is larger: check the tile plan, then run esri, mosaic, infer, extract, route, report
python scripts\make_village_map_series.py --village adilabad_urban_updated
```
(the same with `--village aswaraopeta`). A larger Adilabad box means new Esri tiles and a new inference run; nothing from the 2018-based run is reused. When results exist I extend
`scripts\build_final_project_outputs.py` for the updated Adilabad folder (`02_ADILABAD_URBAN_UPDATED`) and compare it with the frozen run.
