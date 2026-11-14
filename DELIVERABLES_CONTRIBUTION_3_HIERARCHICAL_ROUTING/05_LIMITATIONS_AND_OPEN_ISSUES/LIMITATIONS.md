# Limitations and open issues (Contribution 3)

## What is real and what is not
| Item | Status |
|---|---|
| Level 1 (Stage B) numbers | recorded results, re-read and recomputed by the audit; Level 1 is not re-executed (its rasters are git-ignored) |
| Level 2 (Damarakunta GP) | real inputs; routes **hamlet hubs** (not houses), so lengths are not comparable with Level 1's 5,069 m |
| mu sweep | real inputs, deterministic; mu = 4 signed off by the owner; the swept set excludes 16 |
| Level 3 Markook, Level 4 Siddipet | **proxy nodes**: scalability demonstration only, no planning conclusion |
| Omission scenarios | synthetic random omission of units, not measured detection errors |
| Costs | ordinal units, not rupees (U03/U04 not implemented) |
| Field validation, legal access, passability | none |

## Needs the owner's data or decisions
* Verified Mandal HQ, PHC and market coordinates and Gram Panchayat polygons with house counts (Level 3); verified mandal HQ points (Level 4) - replace the proxy files in `Siddipet/_mandal/` and `Siddipet/_district/`.
* Anganwadi coordinate (U15), State Schedule of Rates / PMGSY rates (U03/U04), PMGSY or TGRAC road inventory in place of Overture roads.
* The original SRTM tile `n17_e078_1arc_v3.tif` to close the original U08 (masked DEM cells) and Stage B rasters to let the audit re-execute Level 1.
* Imagery basemaps are not used: the Esri imagery licence is unresolved; land cover (WorldCover, CC BY 4.0) gives the map context instead.
* The geoBoundaries release has 23 mandals in Siddipet district; the current administrative set may differ.
