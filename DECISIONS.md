# DECISIONS

| # | Date | Decision | Reason | Evidence | Alternative considered | Why rejected |
|---|---|---|---|---|---|---|
| 1 | 2026-09-30 | Phase 0 audit runs on the user's machine via `scripts/phase0_audit.py` | The project, checkpoint and GPU are on the user's Windows PC; the assistant's sandbox cannot see them | No files uploaded; sandbox is a separate Linux container | Assistant writes the audit from the user's description | Would be unverified; violates "audit before coding" |
| 2 | 2026-09-30 | LoveDA mIoU 53.80 / mDice 68.91 reported only as source-domain results | Checkpoint was validated on LoveDA only | Checkpoint metadata (to be confirmed by audit) | Report as project performance | Not Siddipet evidence |
| 3 | 2026-09-30 | Never use 0.55 m/pixel for Siddipet; distances only in a projected UTM CRS chosen from data coordinates | Fixed scale came from LoveDA resizing | User instruction; audit will locate the constant | Keep scale factor | Not true georeferencing |
| 4 | 2026-09-30 | TGRAC MapServer imagery treated as NOT downloadable and NOT licensed until proven | MapServer export returns rendered images; no licence stated | TGRAC Web GIS page describes services for departments/collaborators | Scrape tiles | Legal and scientific risk |
| 5 | 2026-09-30 | Sentinel-2 used only for seasonal land-cover/water support, not building segmentation | 10 m pixels cannot resolve individual rural buildings | Sensor specification | Use Sentinel-2 as main imagery | Resolution far from model's training scale |
| 6 | 2026-09-30 | Open Buildings, OSM, PMGSY, TGRAC, WorldCover labelled REFERENCE, never GROUND_TRUTH | They are model outputs or unvalidated compilations | Dataset documentation | Treat as ground truth | Inflates reported accuracy |
| 7 | 2026-09-30 | Facilities come only from external records; the size heuristic survives only as `P1_candidate`, `confirmed=false` | Building size does not identify function | User instruction | Keep heuristic as primary | Scientifically invalid |
| 8 | 2026-09-30 | Earlier `tools/` folder renamed `scripts/` | Match the agreed project structure | — | Keep both | Avoid duplicate paths |
