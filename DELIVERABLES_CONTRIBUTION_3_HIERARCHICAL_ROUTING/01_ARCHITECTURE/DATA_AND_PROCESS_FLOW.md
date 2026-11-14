# Data and process flow

```
open data (WorldCover, Copernicus DEM, geoBoundaries, Overture)  +  Stage B / TGRAC files (Level 2)
        |  src/utils/data_downloader_helper.py  (hashes + provenance JSON; Overture release pinned)
        v
layers (src/routing/layers.py): land cover + slope -> cost c(x) = [c_lc(class) + g(slope)] * m(x);  m(x) = 1 + (mu-1) * 1[footprint] * (1 - 1[within r of an exempt facility])
        v
RoutingProblem (Levels 2-3, grid)   |   DistrictProblem (Level 4: 250 m coarse plan -> contract_chains -> 30 m windows inside a 1 km corridor)
        v   lazy-greedy shared-network attachment (Stage B Grid search, no diagonal corner-cutting)
LevelResult (routes, unique / total length, connectivity by union-find, new vs existing-road length)
        v   src/evaluation/hierarchy_metrics.py
GeoPackage (routes_shared, routes_independent, nodes) + summary JSON + metrics / override / omission CSV   -> docs/results/hierarchy_real_run/
        v   src/evaluation/plot_hierarchy_figures.py, plot_level1_omission.py, build_contribution3_deliverables.py
figures, maps, charts, tables (this package)
        v   src/evaluation/provenance_audit.py
PROVENANCE_AND_PROOFS.md  (hashes, re-run, re-download, manuscript numbers, figures, this package)
```

Level 1 (Stage B) is not re-executed: `DELIVERABLES_DAMARAKUNTA_STAGE_B/` holds its recorded results and its tables are re-read and recomputed by the audit.
Levels 3-4 nodes are proxies (see `05_LIMITATIONS_AND_OPEN_ISSUES/LIMITATIONS.md`).
