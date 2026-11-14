# Inputs still needed from the project owner

Levels 3-4 are PROXY demonstrations until these are supplied. Nothing below has been invented or estimated.

| # | Input | Used for | Where it goes |
|---|---|---|---|
| 1 | Verified Mandal HQ, PHC and market coordinates (lat/lon, with source) | Level 3 root and facility terminals; Level 4 mandal terminals | `Siddipet/_mandal/`, `Siddipet/_district/` (replace proxy files) |
| 2 | Gram Panchayat polygons with house counts | Level 3 hub weights; replaces village points | `Siddipet/_mandal/` |
| 3 | Anganwadi coordinate (decision U15) | Level 2 facility override | `docs/DECISIONS.md` U15, Level 2 facility table |
| 4 | State Schedule of Rates or PMGSY unit rates (U03/U04) | rupee cost model instead of ordinal units | `configs/hierarchy_levels.yaml` |
| 5 | Original SRTM tile `n17_e078_1arc_v3.tif` and Stage B rasters (U08) | closes the masked-DEM issue; lets the audit re-execute Level 1 | `Siddipet/Damarakunta/` (git-ignored) |
| 6 | PMGSY/TGRAC road inventory (optional) | replaces Overture roads of unknown completeness | `configs/hierarchy_levels.yaml` |
| 7 | Current mandal list for Siddipet (optional) | geoBoundaries has 23 mandals and may be outdated | `Siddipet/_district/` |

After supplying 1-2, re-run `python -m src.routing.run_hierarchy` and `python -m src.evaluation.build_contribution3_deliverables`, then the audit.
