# Real-data multi-level run (2026-11-14)

Command: `python -m src.routing.run_hierarchy --levels 2 3 4 --data real --out outputs/hierarchy_real` (log: `run_log.txt`).
Inputs were fetched with `src/utils/data_downloader_helper.py` (Copernicus GLO-30 DEM, ESA WorldCover 2021, geoBoundaries, Overture roads / villages); Level 2 also uses the
repository's TGRAC roads, 5 facilities, v8 building footprints and the 163 Stage B house targets. See each input's `.provenance.json` (regenerable, git-ignored).

| Level | Nodes | Shared unique length | New construction | Independent (new) | Reading |
|---|---|---|---|---|---|
| 2 GP (Damarakunta) | 18 hamlet hubs + 5 facilities (163 houses) | 1,764 m | 1,764 m | 1,791 m | sharing saves 1.5%; the local override shortens facility routes by 42 m in total and changes no other route |
| 3 Mandal (Markook) | 14 village points + 1 PROXY Mandal HQ | 5,913 m | 5,913 m | 5,913 m | villages are scattered, so no sharing; attachments are to collector-grade roads (tertiary and above) |
| 4 District (Siddipet) | 22 PROXY mandal terminals -> PROXY district HQ | 359.9 km | **15.1 km** | 19.1 km | 95.8% of the backbone runs on existing roads; the headline saving is road reuse, the new-construction saving is 20.9% |

## Read before quoting any number
* Levels 3 and 4 terminals are interior points of geoBoundaries polygons (`proxy=True`), not verified HQ/PHC/market locations. GP hubs at Level 3 are OSM village points with weight 1 (no GP polygons / house counts exist in the open sources).
* Level 2 routes hamlet hubs, not houses: not comparable with the Level-1 5,069 m.
* Costs are ordinal planning units, not rupees (see docs/DECISIONS.md, U03/U04 for the plan).
* Omission columns are synthetic random omissions of units (3 seeds x 10/20%), not measured detection false-negative rates.
* Roads are Overture (OSM-derived) segments, not a PMGSY/TGRAC inventory; the district run uses motorway-tertiary only.
* Nothing is field validated.
