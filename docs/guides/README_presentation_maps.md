# Presentation maps - Damarakunta (Markook Mandal, Siddipet)

Script: `scripts\generate_presentation_maps.py` (copy it there). It reads your project data, never edits it, and writes to
`Siddipet\Damarakunta\results\presentation_maps\` (PNG 300 dpi + PDF per figure, plus `provenance.json`).

## Run (VS Code terminal, project root `D:\Telangana_Rural_Project`)

    .venv\Scripts\python.exe scripts\generate_presentation_maps.py

Optional explicit inputs:

    .venv\Scripts\python.exe scripts\generate_presentation_maps.py ^
      --imagery "PATH\TO\imagery.tif" ^
      --audit Siddipet\Damarakunta\results\connectivity_audit_v1\ca1\connectivity_audit.gpkg ^
      --planner "PATH\TO\network_v2.gpkg" ^
      --boundary "PATH\TO\village_boundary.gpkg" ^
      --attribution "Imagery: <provider, date, licence text>"

Needs geopandas, rasterio, matplotlib, shapely (already used by the project). No new installs required.

## What the script does
1. Finds roads (`tgrac_road_network.gpkg`), facilities, the audit GPKG, the latest `network_v2.gpkg`, a boundary file and the WorldCover raster; prints every path it chose.
2. Defines the study extent from planner/audit/facility features plus 250 m padding (not from the mandal-wide road layer).
3. Scans the project for 3+ band georeferenced rasters (`.tif/.tiff/.vrt/.jp2`), reprojects on the fly to EPSG:32644, and picks the finest raster covering at least 90% of the extent. It prints all candidates with resolution and coverage.
4. Draws Figures 1-4 only when the required inputs exist; otherwise it prints `SKIP`/`STOP` with the missing input. No synthetic buildings, routes or imagery are ever created.
5. With no imagery it stops. `--fallback-worldcover` draws a DRAFT land-cover background that is labelled "NO SATELLITE IMAGERY" on the figure; do not use those for the report.

## Figure inputs
| Figure | Layers used |
|---|---|
| 01 Study-area overview | imagery; roads; facilities; audit `candidates`; boundary (only if a boundary file exists) |
| 02 Building extraction + roads | imagery; audit `candidates` (model-derived polygons, unverified); roads |
| 03 Proposed network | imagery; roads; planner `routes_network_aware` (selected), `stageA_alternatives` (dashed), `targets` |
| 04 Connectivity audit | imagery; audit `road_segments`, `routes_at_attach_tol`, `dangling_ends`, `inferred_bridges`, `candidates`, `facilities` |

## Labelling rules built in
- Routes are "planning alternatives, not verified roads"; routing costs are not money.
- Inferred bridges are "candidates requiring verification"; proximity is not proven connectivity.
- Building polygons are model-derived and unverified.
- No boundary is drawn unless a boundary file is found.

## Status at hand-off (what I could and could not verify)
- Verified: the script runs on a copy of the held road, facility and planner GeoPackages and the WorldCover raster, and writes a labelled draft for Figures 1 and 3.
- Not verified: Figures 2 and 4 and every satellite-background render. The audit GPKG, building polygons, boundary file and imagery were not available to me; I could not reach the D: drive.
- Not verified: the audit-layer column names; the script only uses geometry and layer names.

## Imagery still needed from you
The earlier audit notes an ESRI 0.6 m mosaic used for inference, with licence unverified. If that mosaic is georeferenced (GeoTIFF/VRT) the script will find it automatically. If it is only PNG/JPEG tiles, you need a world file or the original GeoTIFF. Before putting any provider imagery in a report, confirm its terms and set `--attribution` to the required text. Sentinel-2 (10 m) can give context but cannot show individual buildings or narrow roads; do not call it high-resolution.
