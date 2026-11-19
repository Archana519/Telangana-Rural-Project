# Contribution 3: multi-village generalisation of the Phase 1 / Stage B pipeline

Replaces the earlier hierarchical (Gram Panchayat / mandal / district) extension. The same Stage B workflow (boundary and roads, land cover / DEM / slope,
building footprints, 10 m cost surface with footprint penalty mu = 4, Stage A / Stage B shared-network planner, penalty and omission sensitivity) is applied to
settlements of three density tiers and compared with the Damarakunta baseline. `DELIVERABLES_DAMARAKUNTA_STAGE_B/` is only read, never written.

| Tier | Settlement | Status |
|---|---|---|
| 1, urban / peri-urban | Adilabad (Adilabad Urban mandal, Adilabad district) | **done, awaiting review** -> `01_ADILABAD/` |
| 2, semi-urban | Aswaraopeta (Bhadradri Kothagudem district) | not started (waits for the owner's confirmation) |
| 3, rural | Alampur (Jogulamba Gadwal district) | not started (waits for the owner's confirmation) |

Code: `src/multivillage/` (`acquire`, `prepare`, `pipeline`, `run`, `report`, `facilities`, `sources`); parameters shared by every village: `configs/multivillage/common.yaml`;
per-village settings: `configs/multivillage/villages/<id>.yaml`. Tests: `tests/test_multivillage.py`.
