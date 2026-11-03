> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# Damarakunta Stage B: deliverables package (reconstruction)

Case study: GIS and remote-sensing based smart-village road planning, Damarakunta, Markook mandal, Siddipet, Telangana.
Planning results on a 10 m grid (EPSG:32644). Routes are unverified planning alternatives, not roads. Costs are ordinal planning units, not rupees.
No field validation, legal access, ownership, drainage, road width or construction cost is established. The completion gate is **not approved** and C3 (five other villages) has **not started**.

| Folder | Content |
|---|---|
| 00_START_HERE | this file, `COMPLETION_GATE.md`, `EXECUTION_STATUS.md`, `RESULTS_INDEX.csv`, `GENERATED_FILES.csv`, `COPY_MANIFEST.csv` |
| 01_ARCHITECTURE | architecture and workflow diagrams, data and process flow |
| 02_FINAL_MAPS | the five final maps, `MAP_FILE_CHECK.csv` |
| 03_RESULTS_TABLES | primary (final x4) tables, comparison tables, charts 1-5, connectivity, and the verified-baseline C1, C2 and uncertainty tables |
| 04_VALIDATION | acceptance tests, validator results, manifests, detection and facility verification, visual audit kit |
| 05_DIAGNOSTICS | boundary, road-component and chain-cell diagnostics |
| 06_REPRODUCIBILITY | commands, input and script hashes, script snapshot, P3 reproduction note |
| 07_LIMITATIONS_AND_OPEN_ISSUES | limitations and unresolved issues, `METHODOLOGICAL_LIMITATIONS_AND_FUTURE_SCOPE.md` (data terms, field validation, C3) |
| 08_SOURCE_REFERENCES | data sources and licence status |

The final scenarios exclude the anganwadi (`00_START_HERE/EXCLUSIONS.md`); the verified 4-facility baseline run is kept only as reproduction evidence (C1, C2, uncertainty and diagnostics below come from it and are not scrubbed).

Run everything again with `python src/run_pipeline.py --profile full` and `python src/run_final_package.py` (see `CLEANUP_PHASE1_REPORT.md` in `docs/`).
