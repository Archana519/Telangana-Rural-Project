# Google Open Buildings v3 test (Damarakunta)

Status: script written and its code path tested only on synthetic data. It has NOT been run on your
data, nothing was downloaded, and no output has been visually checked.

## Setup (once, project root, VS Code terminal)
    .venv\Scripts\python.exe -m pip install s2sphere requests pandas
Put `google_open_buildings_test.py` in `D:\Telangana_Rural_Project\scripts\` (view_footprints.py must stay in the project root).

## Run (no sign-in needed; official public tiles)
Boundary auto-search is by file name inside the village folder. Check what it finds, or pass your boundary:
    .venv\Scripts\python.exe scripts\google_open_buildings_test.py --boundary <path\to\boundary.gpkg>
No boundary file? Small test area only (around the 58 candidates, NOT the village):
    .venv\Scripts\python.exe scripts\google_open_buildings_test.py --use-candidate-extent

Note: the tile method streams the whole S2 level-4 CSV tile (large, probably hundreds of MB) and keeps only
rows inside your bbox. It is one regional tile, not the global dataset. Nothing is cached on disk.

## Earth Engine alternative (downloads only the study area)
Needs a Google account with Earth Engine access and a Cloud project:
    .venv\Scripts\python.exe -m pip install earthengine-api
    .venv\Scripts\earthengine.exe authenticate
    .venv\Scripts\python.exe scripts\google_open_buildings_test.py --source ee --ee-project YOUR_PROJECT --boundary <file>

## Outputs: Siddipet\Damarakunta\results\google_open_buildings\
google_open_buildings_v3.gpkg (layer google_buildings, raster CRS, keeps confidence, area_in_meters, full_plus_code),
gob_overlay.png, gob_closeup.png, gob_comparison_closeup.png, provenance.json.
The script refuses to overwrite; use --out-dir for another run.

## Licence / attribution
Google Open Buildings v3 is released under CC BY 4.0 and ODbL v1.0 per the dataset page. Confirm at
https://sites.research.google/open-buildings/ before publishing; attribute as "Google Open Buildings v3".

## Limits
Google polygons are model-derived, not verified buildings, and their source imagery date differs from yours.
Comparison numbers are descriptive overlap, not accuracy. Judge roof shape by eye.
