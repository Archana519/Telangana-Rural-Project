# PHASE_C_READINESS_PLAN (proposed document, 2026-10-24)

Save as a NEW file in `D:\Telangana_Rural_Project\`. Nothing here changes the architecture, existing results, the research gap, or the C1/C2 definitions. No imagery is downloaded and no inference is started by anything below.

Evidence labels: **Verified** = from code I read in the review pack. **Unverified** = inferred. I read the structure, check lists and output files of the `phase25_*` scripts, not every line, and I have not run them.

## 1. What the `phase25_*` scripts can and cannot do for Phase C

| Script (step) | What it does (Verified from the code) | Reusable for Phase C? |
|---|---|---|
| `phase25_multiple_villages` (1) | Checks required folders and whether the old `phase18` to `phase24` result CSVs exist | No. It tests the older pipeline's outputs; the current chain (v8 buildings, access, `network_v2`) is not represented |
| `phase25_village_template` (2) | Writes a folder template (`study_area`, `raw`, `reference`, `aligned`, `derived`, `predictions`, `results`) and a config template with keys district, mandal, village, study_area, data, processing, status | Partly. The folder layout matches both existing villages. The config keys do not match `damarakunta.json` (which has crs, paths and stages), so a new per-village config should be modelled on `damarakunta.json` |
| `phase25_discover_villages` (3) | Lists village folders under `Siddipet` and checks the standard subfolders exist | Idea only. It checks folders, not data |
| `phase25_validate_village_inputs` (4) | Checks whether the expected input directories contain files, including `raw\imagery` | No as evidence. It tests file presence, not content, and it looks in `raw\imagery`, while the imagery used for modelling in Damarakunta is the mosaic in `aligned` |
| `phase25_create_village_manifest` (5), `phase25_batch_readiness` (6) | Build a manifest and a batch-readiness table from earlier step CSVs and from the `phase18` to `phase24` outputs | No, same reason as step 1 |
| `phase25_processing_summary` (7), `phase25_village_expansion_checklist` (9), `phase25_master_status_report` (10) | Summaries and checklists over those CSVs. Step 10 contains step statuses written in as the fixed text "COMPLETED" | No. Do not use their output as status evidence |

Step 8 was not in the review pack, so I have not seen it.

Conclusion: the folder template is reusable; nothing in `phase25_*` verifies that data are usable.

## 2. The two new read-only scripts

| Script | Purpose |
|---|---|
| `discover_mandal_villages.py` | Lists villages of a mandal from the TGRAC Master Administrative Boundary service (HTTP GET only), with area, size relative to Damarakunta, whether a local folder or 0.6 m mosaic exists, and whether a DEM / WorldCover tile on your disk covers the village. `--nearby-km K` also lists villages of other mandals within K km of the mandal |
| `village_readiness.py` | Opens the data and records PRESENT / MISSING / UNVERIFIED per input: boundary polygon; local imagery (opened and measured: resolution, coverage, non-empty share); DEM and WorldCover (window read inside the village bounding box); road, school, health, anganwadi and plinth layers (queried over the village polygon). It writes the readiness CSV, the measurements, a shortlist with exact blockers, and provenance |

Status meanings: **PRESENT** = opened or queried and the stated test was met (the test is written in the detail column). **MISSING** = looked for, nothing usable. **UNVERIFIED** = partly there, or cannot be checked from here. PRESENT does not mean the data are accurate.

How the script avoids guessing: TGRAC layer URLs are read from your own scripts, and each layer's name is read from the server. Which layer is "roads", "schools" and so on is inferred from the layer name and is marked UNVERIFIED until you confirm it with `--layers-json`.

Not tested against the real TGRAC service. I tested both scripts on a made-up village folder with a stand-in service.

## 3. Commands (from `D:\Telangana_Rural_Project`)
```powershell
# 1. villages of Markook, plus villages of other mandals within 5 km (adjust or drop --nearby-km)
.venv\Scripts\python.exe scripts\discover_mandal_villages.py --mandal MARKOOK --nearby-km 5

# 2. readiness of the Markook villages (add --include-nearby for the others; use the folder printed in step 1)
.venv\Scripts\python.exe scripts\village_readiness.py --discovery-dir Siddipet\_village_discovery\<tag from step 1>
```
Each run writes a new folder and refuses to reuse one. If the TGRAC server rejects the connection, add `--insecure` (as your earlier TGRAC scripts did).

## 4. What the table will not tell us
- Imagery use rights (still UNVERIFIED, DECISIONS row 15) or whether imagery at 0.6 m exists for a village. Obtaining imagery means repeating the ESRI export used for Damarakunta, which needs your approval first.
- Whether the road and facility layers are accurate, or whether the segmentation model works on the village.
- Whether a village is suitable for the research question; the shortlist ranks data availability only.

## 5. Approvals needed before the next stage
1. The village list (after you read the readiness table).
2. Any imagery download (licence UNVERIFIED).
3. Any inference run (about 1 hour of CPU per village, estimated from the Damarakunta note).
4. New per-village config files (new files only; `damarakunta.json` is not edited).
