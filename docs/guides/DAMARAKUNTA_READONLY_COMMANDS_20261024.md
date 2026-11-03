# Read-only commands for you to run (from `D:\Telangana_Rural_Project`; I cannot reach your computer)
None of these changes an existing file. Items 5 creates one NEW folder (stated below). Paste the output back.

## 1. Check that the proposed output names do not already exist
```powershell
"Siddipet\Damarakunta\DAMARAKUNTA_FINAL_COMPLETION_REPORT_PROPOSED.md","DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024_v2.md","DAMARAKUNTA_COMPLETION_CHECKPOINT_20261024_v2_1.md","Siddipet\Damarakunta\reference\manual_building_labels\reference_buildings_v1.gpkg","Siddipet\Damarakunta\reference\random_windows" | ForEach-Object { "{0} -> exists={1}" -f $_, (Test-Path $_) }
Get-ChildItem *.md | ForEach-Object { "{0} | {1:N0} B | {2}" -f $_.Name,$_.Length,$_.LastWriteTime }
```
Creates nothing.

## 2. Model checkpoint size, time and SHA-256 (reads the file; does not move or change it)
```powershell
$c = "D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
Get-Item $c | ForEach-Object { "{0} | {1:N0} B | {2}" -f $_.FullName,$_.Length,$_.LastWriteTime }
Get-FileHash $c -Algorithm SHA256
```
Creates nothing (the hash may take a minute).

## 3. Inference script and environment versions
```powershell
Get-ChildItem scripts -File | Where-Object { $_.Name -match "tile|infer|predict|segment" } | ForEach-Object { "{0} | {1:N0} B | {2}" -f $_.Name,$_.Length,$_.LastWriteTime }
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip list 2>$null | Select-String -Pattern "^(torch|torchvision|numpy|rasterio|geopandas|shapely|networkx|scipy|pandas|pyproj|gdal|fiona|pyogrio|matplotlib)\s"
Get-Content Siddipet\Damarakunta\predictions\tiled_v1\run_log_full.json
```
Creates nothing. Tell me which script wrote `tiled_v1` if the names are unclear.

## 4. Facility evidence: Anganwadi record, MPPS "colocated" flag (read-only Python)
```powershell
@'
import warnings; warnings.filterwarnings("ignore")
import glob, geopandas as gpd, fiona
pd_ = __import__("pandas"); pd_.set_option("display.width",250); pd_.set_option("display.max_columns",None)
sc = gpd.read_file(r"Siddipet\Damarakunta\reference\school_compounds.gpkg")
print(sc[[c for c in ("School_Code","School_Name","Whether_Anganwadi_Colocated","Latitude","Longitude") if c in sc.columns]].to_string(index=False))
for f in sorted(glob.glob(r"Siddipet\Damarakunta\reference\*.gpkg")):
    for lyr in fiona.listlayers(f):
        if "angan" in (f+lyr).lower():
            g = gpd.read_file(f, layer=lyr)
            m = g[g.astype(str).apply(lambda r: r.str.contains("1702300|damarakunt", case=False, regex=True).any(), axis=1)]
            print("\n", f, lyr, len(g), "rows; matching rows:", len(m))
            print(m.drop(columns="geometry").T.to_string())
            print(m.geometry.to_crs(32644).apply(lambda p: (round(p.x,1), round(p.y,1))).to_string())
'@ | .\.venv\Scripts\python.exe -
```
Creates nothing. It shows what the files say about the Anganwadi and the colocated flag; it does not decide that either record is wrong.

## 5. Edge-tile overlay (approved). Creates ONE NEW folder only
First find the file names (read-only):
```powershell
Get-ChildItem Siddipet\Damarakunta\raw,Siddipet\Damarakunta\aligned,Siddipet\Damarakunta\reference -File | Where-Object { $_.Name -match "mosaic|esri|tile|road" -and $_.Extension -in ".tif",".gpkg" } | ForEach-Object { "{0} | {1:N0} B" -f $_.FullName.Replace((Get-Location).Path+"\",""),$_.Length }
```
Then, after saving `check_edge_alignment.py` into `scripts\` (new file) and filling in the names:
```powershell
.\.venv\Scripts\python.exe scripts\check_edge_alignment.py --mosaic <MOSAIC.tif> --roads <tgrac_road_network.gpkg> --tiles-glob "Siddipet\Damarakunta\raw\<esri tile pattern>*.tif" --tag edge1
```
Creates only `Siddipet\Damarakunta\results\stageD_edge_alignment\edge1\` (report txt, two CSVs, `overview.png`, four `corner_*.png`; the script refuses to reuse an existing tag). No network, no export, nothing existing is opened for writing.

### What this check can and cannot establish
- **Can:** CRS, affine transform, pixel size and rotation terms of the mosaic and each tile; whether each tile lies inside the mosaic; any non-square pixel (a sign of stretched edge tiles); a visual look at roads over image at the four corners; a coarse shift estimate per block where roads have image contrast.
- **Cannot:** prove absolute georeferencing (no independent ground control); distinguish a road-layer error from a mosaic error; say anything where roads are low-contrast (blocks flagged `LOW_CONTRAST_UNINFORMATIVE`); detect offsets under roughly 5 m. I tested it only on a synthetic raster (planted shift 6 m east, 6 m south; recovered 2-7 m / 7-10 m, so expect a coarse estimate along a line's direction). A good visual fit supports "no gross mismatch", not "correct".
