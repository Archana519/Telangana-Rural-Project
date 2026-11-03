# Detailed plan: reference building labels (PLAN ONLY; `reference_buildings_v1.gpkg` is NOT created; awaiting your approval)

## 1. Scope
Six existing purposive 200 x 200 m windows (W1_CORE, W2_EAST, W3_FRINGE, W4_GAP, W5_GAP, W6_FARMNEG; window layer as recorded in the Stage A report; 67 model buildings inside them in total). The seeded random windows (separate plan) are added only after you approve that plan. Windows are not changed.

## 2. Digitising rules
**Include** a polygon for each: roofed building footprint as seen from above (roof outline, not shadow); each separately roofed structure; attached rooms under one continuous roof as one polygon; each house in a row where a roof ridge or wall line separates them; partially built structures with visible walls/roof; sheds and animal shelters with a solid roof of at least 10 m2.
**Exclude:** open yards and compound walls without roof; tents, tarpaulin-only and vehicles; water tanks and silos below 10 m2; shadows; trees; ruins with no roof; temporary crop heaps.
**Uncertain** (mark `confidence = low`, still digitise): cannot tell roof from bare ground, deep shadow, tree-occluded roof, very small structure near 10 m2. Areas where nothing can be decided go to a separate `uncertain_areas` layer and are excluded from scoring (counted and reported).
**Partial** buildings cut by the window edge: digitise to the edge, `partial_in_window = true`; scored with the rest but also reported without them.
**Procedure:** QGIS, mosaic at 1:300 to 1:500, snapping off, vertices at roof corners. Annotate with all model layers hidden (blind to predictions). One annotator (you). Optional: re-annotate two windows after at least one week for intra-annotator agreement.

## 3. GeoPackage schema and CRS
File `Siddipet\Damarakunta\reference\manual_building_labels\reference_buildings_v1.gpkg` (the folder is currently empty; refuse to overwrite). CRS EPSG:32644, polygons.
- Layer `reference_buildings`: `ref_id` (text, unique, e.g. W2-014), `window_id`, `sample` ('purposive'/'random'), `source` (always 'reference_manual'), `confidence` (high/medium/low), `partial_in_window` (bool), `annotator`, `annotated_on` (ISO date), `imagery` (mosaic file name), `blind_to_model` (bool), `notes`.
- Layer `uncertain_areas`: `area_id, window_id, reason, annotated_on`.
- Layer `annotation_log` (non-spatial): `window_id, started_on, finished_on, n_buildings, n_uncertain, minutes_spent, comments`.
- Sidecar `reference_buildings_v1_manifest.json`: SHA-256 of the gpkg and mosaic, script versions, date.

## 4. Geometry validity and quality control (script `scripts\validate_reference_buildings.py`, read-only, shown before it runs)
CRS equals 32644; `is_valid` for all; no empty/null; at least 3 distinct vertices; no self-intersection; area at least 10 m2 (smaller flagged); area above 2,000 m2 flagged for review; overlap between buildings below 1 m2 (larger overlaps flagged); every polygon within or clipped to its window (`partial_in_window` consistent); `ref_id` unique; no feature in the blank-corner zone; every window has a log entry; counts per window by confidence; a 10 % visual spot-check by overlay PNG that you review.

## 5. Keeping reference apart from predictions
Separate file, folder and layer names; `source = 'reference_manual'`; no model attribute columns; nothing written into `predictions\`; evaluation scripts read the two inputs by explicit path and fail if `source` is not 'reference_manual'. The existing empty `reference_buildings` (0 features) is left as it is.

## 6. Metrics (script `scripts\evaluate_building_segmentation.py`, new output folder, shown before it runs)
Prediction sides compared: (a) building class 2 of `pred_classes_full.tif`, (b) the 163 candidate polygons the planner uses (these include merged blobs).
- **Instance matching:** one-to-one, greedy by descending IoU, a match needs IoU at least 0.5 (sensitivity at 0.3 and 0.7). TP = matched pairs, FP = unmatched predictions, FN = unmatched references.
- Precision = TP/(TP+FP); recall = TP/(TP+FN); F1 = 2PR/(P+R); instance IoU = mean IoU of matched pairs.
- **Pixel level** (within windows, excluding `uncertain_areas`): IoU = |pred ∩ ref| / |pred ∪ ref| on class 2; also precision/recall by pixel.
- Merge/split diagnostics: predictions touching more than one reference (merged) and references covered by more than one prediction (split).
- W6_FARMNEG has 0 predictions and perhaps 0 references: precision is undefined there; report false alarms as counts, not ratios.
- Per window and pooled; purposive and random never pooled together; bootstrap over windows for intervals; every number labelled "image-interpretation reference, one annotator".
- **Planning effect:** repeat the 103 -> 118 access count using the reference polygons instead of predicted ones, inside the windows only, as a sensitivity statement, not a result about the village.

## 7. Documenting uncertainty and imagery limits
Report: imagery date unknown (not in metadata I have seen); nominal 0.6 m resolution; edge-tile georeferencing check pending; shadow/tree/roof-colour ambiguity counts; share of `confidence = low`; single annotator; windows chosen from predictions so recall there is an upper-bound-style figure; no field survey. Reported as "segmentation accuracy in these windows", never as village-wide accuracy.

## 8. Approval needed
Approve this plan (or edit), and then I show the two scripts before anything writes; the gpkg itself is created by you in QGIS (or an empty template by script on your say-so).
