# Adilabad Urban (Adilabad Town), updated boundary: run status

Study area: **Adilabad Urban (Adilabad Town)**, a *derived built-up settlement extent* (18.59 km², not an administrative boundary), written for the village id `adilabad_urban_updated`
(`configs/multivillage/villages/adilabad_urban_updated_boundary.geojson` + `.provenance.json`: derivation, centre, edge-continuity check, covered mandals and localities). It covers the urban area of
Adilabad Urban mandal (50.5 %) and the adjoining built-up parts of Mavala (32.2 %) and Adilabad Rural (17.4 %) mandals (2018 layer names); Overture localities inside: Adilabad, Anukunta, Kurshid Nagar, Mavala, Vidya Nagar.
The district of Adilabad is not the study area. The frozen 2018-based run `01_ADILABAD*` is unchanged.

Done here (sandbox): open data (Overture roads / buildings / places, WorldCover, Copernicus DEM) on the new polygon; Esri 0.6 m tiles (26 of 36 grid tiles touch the polygon) and the mosaic (16,749 x 16,833 px, EPSG:32644, git-ignored);
open-footprint routing, **main strategy comparison only** (`--quick`), tables in this folder.
Not done: the penalty / omission / road-gap sweeps for this variant, and the whole StrongDINOv2Seg chain (inference, extraction, segmentation routing, maps): the checkpoint lives on the owner's PC.
On the PC: `python scripts\run_village_end_to_end.py --village adilabad_urban_updated --stage infer` (then extract, route, report) and `python scripts\make_village_map_series.py --village adilabad_urban_updated`.

**Update:** the StrongDINOv2Seg chain has since been completed on the owner's PC; see `../01_ADILABAD_UPDATED_SEGMENTATION/RUN_STATUS.md`. The statement above that segmentation was not done is superseded.
