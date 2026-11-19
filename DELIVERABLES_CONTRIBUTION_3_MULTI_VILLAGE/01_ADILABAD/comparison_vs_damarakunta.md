# Adilabad vs Damarakunta

Damarakunta numbers are read from `DELIVERABLES_DAMARAKUNTA_STAGE_B/03_RESULTS_TABLES/` (read-only).

| metric | Damarakunta (Phase 1 / Stage B, village) | Adilabad (urban / peri-urban window) |
|---|---|---|
| Settlement tier | rural village (dispersed) | urban / peri-urban mandal (dense) |
| Study area (km2) | 18.47 (TGRAC village polygon) | 17.75 (geoBoundaries ADM3 'Adilabad Urban') |
| Building source | StrongDINOv2Seg candidates on 0.6 m Esri imagery (278 polygons, 165 inside) | Overture open footprints: OSM + Google Open Buildings (24,924 polygons) |
| Footprints used for the penalty layer | 165 candidates inside the boundary (all classes) | 18,242 polygons (area >= 30 m2, confidence >= 0.7) |
| House targets | 163 (all candidates) | 874 (houses > 30 m from a road, = 4.8% of footprints) |
| Median target footprint area (m2) | 235.8 | 139.6 |
| Median target distance to nearest road (m) | 27.7 | 42.3 |
| Facilities planned | 5 (TGRAC schools, sub-centre, GP HQ points) | 71 verified of 83 candidates (Overture places) |
| Houses routed | 163 of 163 | 873 of 874 |
| Independent routes: total / unique (m) | 10,045.4 / 6,753.1 | 56,308.0 / 46,419.2 |
| Length-only control: unique (m) | 6,979.8 | 43,787.2 |
| Roads-only shared reference: unique (m) | 5,229.3 | 45,058.9 |
| Two-stage shared plan: unique (m) | 5,069.0 | 34,358.8 |
| Saving vs independent (%) | 24.9 | 26.0 |
| Roads-only shared saving (%) | 22.6 | 2.9 |
| Length-only control vs independent (%) | -3.4 | 5.7 |
| Unique length per routed house (m) | 31.1 | 39.4 |
| Routes crossing other footprints (two-stage) | 28 of 163 (17%) | 332 of 873 (38%) |
| Length inside other footprints (m) | 209.1 | 2,041.1 |
| mu = 1 -> 4: unique length change (%) | +7.7 | +13.3 |
| mu = 1 -> 4: routes crossing (n) | 56 -> 28 | 618 -> 332 |
| Facility phase: unique length (m) / facilities | 249.3 / 5 | 1,090.1 / 71 |
| 10% random omission: length change (%) / households unserved | -7.6 / 16 of 163 | -7.6 / 88 of 874 |
| 20% random omission: length change (%) / households unserved | -16.9 / 33 of 163 | -15.0 / 176 of 874 |
| smallest-10% omission: length change (%) / households unserved | -8.3 / 17 of 163 | -7.9 / 89 of 874 |
| smallest-25% omission: length change (%) / households unserved | -25.1 / 41 of 163 | -21.2 / 220 of 874 |
