# DAMARAKUNTA_STAGE_B_C_PROPOSALS (proposed document, 2026-10-24)

Save as a NEW file in `D:\Telangana_Rural_Project\`. Nothing here exports imagery, creates labels, or changes any existing file.

## Part B. Imagery licence (Damarakunta mosaic)

### What is known (documented in project files)
- The mosaic `aligned\damarakunta_esri_highres_mosaic_0p6m.tif` was built on 4 Oct 2026 from 11 tiles requested one by one from `https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export` (`export_esri_damarakunta_full.py`, `mosaic_esri_damarakunta.py`). The tiles were then rewritten as GeoTIFF files (about 1.28 GB of raw imagery files in total, incl. `raw_` copies).
- The script sends a browser-like User-Agent string and has no licence or opt-in check. DECISIONS row 15 already lists the licence as unverified.
- The same imagery is the input of the inference, building extraction, access assessment and route planning for Damarakunta, and of any figures or maps in the report.

### What the sources I read say (my reading, not legal advice)
- Esri terms summary, last updated 21 Apr 2025: basemap data "may only be taken offline using Esri Content Packages"; prohibits "systematically harvest[ing] basemap tiles through any method other than using Esri Content Packages"; requires attribution to Esri and its data providers; allows use "for projects and applications that are for internal or external use" and points to a separate permitted-uses page. It does not name World Imagery, derivative products, or research publication. [PDF](https://www.esri.com/content/dam/arcgisonline/docs/tou_summary.pdf)
- Esri support article 000014855: the World Imagery "for Export" service is "designed to support exporting small volumes of basemap tiles for offline use". [article](https://support.esri.com/en/technical-article/000014855)

### Interpretation (not established)
- 11 map-image requests of about 3.2 km2 each are a small volume, but "Content Packages" is the route the summary names, and these requests were not that route.
- Whether training/inference on the pixels, storing them locally, and publishing derived building/road maps is covered is **not determined** by anything I read.

### Needs confirmation from the authority
Questions for CBIT's GIS/library office (does the institution hold an ArcGIS licence?) and, if needed, for Esri:
1. Does our ArcGIS licence (or the free public World Imagery service) permit saving map images from the `MapServer/export` operation for local storage, for an academic M.Tech project?
2. Is machine-learning inference on those saved images, and storing the predictions, permitted?
3. May figures and maps derived from the imagery (overlays, extracted building footprints, route maps) appear in a thesis and a conference or journal paper, and with what attribution wording?
4. May the derived footprints and rasters be shared with reviewers or deposited in a repository? May the imagery itself be?
5. Is an Esri Content Package or a tile-package export the required route, and is it available to us (with credits)?
6. Is there an acceptable alternative with documented terms for the same use?

### Options (your decision; none executed)
- **B1** Ask CBIT/Esri; keep all work, label the licence status in every report; no new export.
- **B2** Treat the mosaic as internal research data, publish only derived planning results and attribution; state the limitation. Still requires the answer to question 3.
- **B3** Replace the imagery source (changes the experiment; needs your approval and a re-run).

## Part C. Segmentation ground truth: proposed labelling workflow (NOT started)

### Current state (Verified)
`windows` has 6 polygons; `reference_buildings` has 0 features; `reference\manual_building_labels` is empty. I have not yet seen the window sizes or which areas they cover (command below).

### Windows
Reuse the 6 existing windows unchanged. First list their area, location and how many model-predicted buildings fall inside; if they are all in one part of the village, or contain very few buildings, report that as a limitation and ask before adding windows (more windows would be a new, separately named layer).

### Storage (no change to existing data)
New file `reference\manual_building_labels\reference_buildings_v1.gpkg`, layer `reference_buildings`, EPSG:32644, with fields `ref_id, window_id, annotator, annotated_on, confidence (clear/uncertain), notes`. The existing windows GeoPackage is read, never written. A hash of the windows file is recorded before and after.

### Digitising rules (to fix before starting)
- One polygon per roof outline visible on the 0.6 m mosaic (not per room, not per shadow); minimum 10 m2 to match the 10 m2 rule of the access assessment (smaller structures noted but kept apart as `uncertain`).
- Attached roofs: one polygon per visibly separate roof; merged only if no visible gap. Record these as `uncertain`.
- Zoom a fixed scale (for example 1:300), annotate without looking at the model output, then compare.
- Annotator, date and imagery file hash recorded in the layer metadata or a sidecar file.
- Single annotator = no agreement estimate. Optional: re-label 20 % of buildings a week later (intra-annotator check) or by a second person.

### Comparison with predictions
Two levels, because the planner uses roof instances (`buildings_v8_full.gpkg`) and not pixels:
1. **Instance level:** match model polygons to reference polygons by IoU >= 0.5 (one-to-one); report precision, recall, F1 per window and pooled, with counts. Report the matching rule and the 10 m2 filter.
2. **Pixel level (building class 2 of `pred_classes_full.tif`):** IoU, precision, recall inside the windows.
3. **Planning-relevant:** share of reference buildings within 50 m of a road versus the same share from the model's polygons (the access metric), and the effect on the 163-polygon figures.

### Limitations to report with any number
Six windows only; selection of windows is not random; one annotator; imagery vintage unknown; labels from the same imagery the model uses (no independent field check); small counts give wide uncertainty (report counts, and bootstrap intervals only as indicative). No claim of accuracy beyond the windows.

### Approval needed before anything is created
Your approval of: windows to use, annotation rules, tool (for example QGIS), and the new file name above.

### Read-only command to describe the windows
See the message that accompanied this file (uses the `windows_gpkg` path from `configs\damarakunta.json`).
