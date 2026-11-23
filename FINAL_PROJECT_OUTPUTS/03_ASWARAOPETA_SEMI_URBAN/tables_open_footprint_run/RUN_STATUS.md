# Aswaraopeta (Ashwaraopet town): run status

Study area: **Aswaraopeta (Ashwaraopet town)**, Aswaraopeta mandal, Bhadradri Kothagudem district, a *derived built-up settlement extent* (2.82 km², not an administrative boundary), centre = Overture division point
"Ashwaraopet" (17.24094N, 81.12817E); 100 % inside the 2018 Aswaraopeta mandal. Boundary + provenance: `configs/multivillage/villages/aswaraopeta_boundary.geojson` / `.provenance.json`.

Done here (sandbox): open data; Esri tiles (6) and mosaic (6,765 x 5,849 px, git-ignored); open-footprint routing, **main strategy comparison only** (`--quick`).
Not done: the sweeps, and the StrongDINOv2Seg chain (checkpoint on the owner's PC).
**Read the numbers with the road layer in mind:** the mapped road density inside the polygon is only 10.1 km/km² (Adilabad: 15.5 in the 2018 polygon, 27.4 in the updated one) and 51 % of the 3,678 footprints are more than 30 m from a mapped road,
so 1,890 targets are routed and 138 of them found no route. The Overture / OSM road layer is incomplete for this town; the large independent-route length mostly reflects missing roads, not geography.

**Update:** the StrongDINOv2Seg chain has since been completed on the owner's PC; see `../02_ASWARAOPETA_SEGMENTATION/RUN_STATUS.md`. The statement above that segmentation was not done is superseded.
