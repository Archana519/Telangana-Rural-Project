# Roof Digitizer (no QGIS)

A local, browser-based tool for tracing reference roofs on the Damarakunta mosaic. It runs on your own
computer (127.0.0.1 only), reads the imagery and the AI candidates read-only, and writes your traces to
the `reference_buildings` layer of `digitize_windows.gpkg` **only when you press Commit**.

Everything is in `D:\Telangana_Rural_Project\digitizer\`.

## 1. First-time setup (Command Prompt, project venv)

```
cd /d D:\Telangana_Rural_Project\digitizer
..\.venv\Scripts\activate
python -c "import rasterio, geopandas, shapely, numpy, pandas, PIL; print('all dependencies present')"
```

If that prints `all dependencies present` you need to install **nothing** (your venv already has them).
Only if it reports a missing module: `pip install -r requirements.txt`.

Then, still in `digitizer\`:

```
python app.py --selfcheck
python verify_integrity.py --init
```

* `--selfcheck` is read-only: it prints the raster CRS/resolution, the layers and window IDs it found,
  the candidate count, and a pixel-to-map round-trip error per window (should be ~0).
* `verify_integrity.py --init` records SHA-256 fingerprints of the mosaic, the candidate GeoPackage, the
  V4 routes, WorldCover/cost rasters and the `windows` layer. **Run it before you trace anything.**

## 2. Start tracing

```
cd /d D:\Telangana_Rural_Project\digitizer
python app.py
```

Your browser opens at `http://127.0.0.1:8765/`. Press Ctrl+C in the Command Prompt to stop it.

| Action | How |
|---|---|
| Pan / zoom | Pan tool (1) or hold Space and drag; mouse wheel zooms at the cursor |
| Trace a roof | Tool "Trace roof" (2). Click each corner. Close with **Enter**, a double-click, or by clicking the yellow first vertex |
| Fix a mistake while drawing | **Backspace** removes the last vertex; **Esc** cancels the polygon |
| Mark an uncertain roof | tick **unsure** (or press U) *before* finishing the polygon, or select a saved polygon and press "Toggle unsure". Saved as `note = unsure` |
| Delete / correct | "Undo last saved", or Select tool (4) -> click polygon -> Delete. To correct a polygon, delete it and redraw |
| AI overlay | tick "AI candidates" (or press C). It is only a visual aid and is never treated as ground truth |
| Brightness / contrast | sliders in the top bar (display only; the raster is not altered) |

Rules built in: a roof needs >= 3 vertices and >= 2 m²; self-intersecting polygons are rejected with a message
and nothing is saved; `window_id` is filled in automatically from the selected window.

### W1_CORE (partial tracing)

1. Trace the roofs in one corner you can finish.
2. Choose "Traced extent" (3) and draw one polygon around exactly that corner (saved as
   `note = TRACED_EXTENT`; it is **not** counted as a roof).
3. Tick "window complete". The tool will not let a CORE window be marked complete without a traced extent.
   (If you really traced the whole window, use "Whole window = extent".)

### W6_FARMNEG

If you see no roofs, trace nothing and just tick "window complete". Zero roofs is a valid result.

## 3. Saving and resuming

* **Autosave:** every polygon is written immediately to `reference\digitizer_draft.json` (previous copy kept as
  `.prev`). Close the browser, stop the server, reboot: reopen with `python app.py` and everything is back.
* **Commit** ("Review & commit..."): the dialog shows exactly what will be written (new polygons per window,
  removals, windows marked complete, warnings) and blocks on any error. Only after you confirm:
  1. a backup is copied to `reference\digitizer_backups\` (plus a one-time
     `digitize_windows.ORIGINAL_before_digitizer.gpkg`);
  2. a temporary copy of the GeoPackage is made and **only** the `reference_buildings` layer is rewritten in it;
  3. the copy is verified (SQLite integrity, same layer list, `windows` layer byte-identical, row count, CRS
     EPSG:32644, geometry validity, every geometry equal to what was drawn);
  4. the copy atomically replaces the original, and is re-verified; on any mismatch the backup is restored.
* Already-saved polygons are preserved exactly. Deleting one needs an explicit confirmation and takes effect at
  the next commit (it shows as grey/dashed until then, and can be restored).
* Each commit also writes `reference\window_status.json` (which windows you marked complete) and appends a line
  to `reference\digitizer_commit_log.jsonl`.
* If a commit says the GeoPackage is in use, close QGIS or any other program that has it open and commit again.
  Nothing was changed and your draft is intact.
* A `uid` column is added to `reference_buildings` (stable feature ID; prevents duplicates). `window_id`, `note`
  and `geometry` are unchanged, so `evaluate_vs_reference.py` keeps working.

## 4. Evaluation script compatibility (one issue found)

`scripts\evaluate_vs_reference.py` handles `TRACED_EXTENT` correctly: the extent is excluded from the roofs, and
both reference roofs and AI blobs are clipped to it (tested). But it cannot tell "traced, no roofs" from
"not traced yet": an untouched window is scored as zero roofs (precision 0, all blobs "unmatched"), and a layer
with no roofs at all makes it exit. The digitizer therefore writes `window_status.json`, and an **optional**
3-edit patch makes the script score only windows marked complete:

```
cd /d D:\Telangana_Rural_Project\digitizer
python apply_eval_patch.py              (dry run: shows the diff, changes nothing)
python apply_eval_patch.py --apply      (makes evaluate_vs_reference.py.bak_before_digitizer_patch, then patches)
```

It refuses to patch if your script differs from what it expects. Skip it if you prefer to edit by hand or to
score every window.

## 5. Checks

**Against your real files (run this first, read-only on your data):**

```
cd /d D:\Telangana_Rural_Project\digitizer
python -m unittest discover -s tests -p "test_real_data.py" -v
```

It checks that the raster is EPSG:32644, ~0.6 m, 11296 x 7171; that `digitize_windows.gpkg` has the `windows` and
`reference_buildings` layers in EPSG:32644; that for sample points in every real window the image the tool
shows has the same pixel values as rasterio reads directly at that map coordinate; that window outlines and AI
candidates map correctly into the crop; and that a test commit on a **temporary copy** of the GeoPackage keeps
the `windows` layer identical. The last test proves the real GeoPackage, raster and candidate layer were not
modified. Expect 7 tests, all `ok`. Any `FAIL` or `skipped` line: paste the output.

**Synthetic-data tests and integrity check:**

```
python -m unittest discover -s tests -v      # 12 backend tests on a synthetic project in a temp folder
python verify_integrity.py                   # raster, candidates, routes, windows layer unchanged?
```

## 6. What has and has not been tested

Tested (Linux, Python 3.13, synthetic data that mimics your CRS, 0.6 m pixels and layer schema): the 12 backend
tests; a headless Chromium session that draws with real mouse clicks (polygon lands on the known marker
coordinate, unsure flag, Esc, rejected bow-tie, CORE guard, preview, commit, reload/resume; 20/20 checks); the
evaluation script before/after the patch; the integrity checker (clean, after a commit session, and after a
1-byte change).

**Not yet tested:** on Windows, with your real 11296 x 7171 mosaic and real windows file, or in Edge/Firefox.
`tests\\test_real_data.py` exists for exactly that (its logic was only validated on the synthetic stand-in). Run `--selfcheck` first; if anything differs from what is described here, paste its output.

## 7. Files

```
digitizer\app.py                 server + command line
digitizer\core.py                coordinate conversion, autosave, safe commit
digitizer\static\index.html      the drawing interface
digitizer\verify_integrity.py    fingerprint check (raster, candidates, routes, windows layer)
digitizer\apply_eval_patch.py    optional patch for evaluate_vs_reference.py
digitizer\tests\                 unit tests (synthetic) + test_real_data.py (your real files)
digitizer\requirements.txt       rasterio, geopandas, shapely, numpy, pandas, Pillow
```

Created at run time inside `...\results\v6_buildings\reference\`: `digitizer_draft.json`(+`.prev`),
`digitizer_backups\`, `window_status.json`, `digitizer_commit_log.jsonl`, `digitizer_integrity_baseline.json`.

Traced polygons are manual reference labels from a single annotator on 0.6 m imagery; uncertain roofs are
flagged. No field validation is implied.
