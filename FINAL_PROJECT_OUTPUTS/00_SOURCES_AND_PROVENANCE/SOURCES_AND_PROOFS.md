# Data sources and provenance proofs (to be completed by the owner)

Pre-filled with the sources the pipeline uses. Licences and versions are as understood when written and are NOT verified: fill the last two columns after checking each page, and attach proofs under `proofs/<study area>/`.

| source | URL (exact endpoint pattern used by the code) | release / version | licence (to verify) | used for | verified by owner (date) | proof file |
|---|---|---|---|---|---|---|
| Esri World Imagery (0.6 m) | https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export | live service (no release number); tiles exported on the acquisition date | Esri Master Agreement / World Imagery terms; non-commercial academic use, credit required | all four |  |  |
| Overture Maps buildings / transportation / places (open data run) | https://overturemaps-us-west-2.s3.amazonaws.com/release/2026-10-21.0/theme={buildings|transportation|places}/type={building|segment|place}/ | release 2026-10-21.0 (pinned in configs/multivillage/common.yaml) | ODbL 1.0 (buildings, transportation); CDLA-Permissive-2.0 (places, divisions): check per theme | adilabad_urban_updated, aswaraopeta, alampur |  |  |
| Overture Maps divisions (boundary candidates, centre point) | https://overturemaps-us-west-2.s3.amazonaws.com/release/<newest>/theme=divisions/type=division_area/ | newest release at the time; the release is recorded in each *_boundary.provenance.json | CDLA-Permissive-2.0 (per Overture documentation) | adilabad_urban_updated, aswaraopeta, alampur |  |  |
| ESA WorldCover 10 m | https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_<tile>_Map.tif | v200 (2021) | CC BY 4.0 (doi:10.5281/zenodo.7254221) | all four (Damarakunta via aligned_open) |  |  |
| Copernicus DEM GLO-30 | https://copernicus-dem-30m.s3.amazonaws.com/<tile name>/<tile name>.tif | GLO-30 (DGED COG) | Copernicus DEM licence (free, attribution; doi:10.5270/ESA-c5d3d65) | all four |  |  |
| OpenStreetMap through Overpass / Nominatim (boundary candidates) | https://overpass-api.de/api/interpreter ; https://nominatim.openstreetmap.org/search | live; retrieval date in the provenance file | ODbL 1.0 (https://www.openstreetmap.org/copyright) | adilabad_urban_updated, aswaraopeta, alampur |  |  |
| geoBoundaries gbOpen IND ADM2 / ADM3 (2018 mandal layer; consistency reference and frozen Adilabad run) | https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3.geojson | buildDate Dec 12, 2023; boundaryYear 2018 (source lgdirectory.gov.in via Pathways Data) | ODbL 1.0 per the geoBoundaries metadata JSON | adilabad_urban (frozen), reference row elsewhere |  |  |
| TGRAC village polygon, road network, facilities (Damarakunta) |  | OWNER TO FILL | OWNER TO FILL | damarakunta |  |  |
| PMGSY rate Rs 75 lakh/km (60-90) |  | OWNER-SUPPLIED | UNVERIFIED: attach the circular or schedule of rates | all four (illustrative only) |  |  |

## Study areas

| id | study area | proofs folder |
|---|---|---|
| damarakunta | Damarakunta (rural; TGRAC village polygon; frozen Stage B) | `proofs/damarakunta/` |
| adilabad_urban_updated | Adilabad Urban (Adilabad Town), derived built-up extent | `proofs/adilabad_urban_updated/` |
| aswaraopeta | Aswaraopeta (Ashwaraopet town), derived built-up extent | `proofs/aswaraopeta/` |
| alampur | Alampur (Alampur town), Jogulamba Gadwal district | `proofs/alampur/` |

## Study-area boundaries

Polygon files and their provenance JSON are in each study area's `boundary/` folder (Adilabad updated, Aswaraopeta, Alampur). Damarakunta's polygon is in `DELIVERABLES_DAMARAKUNTA_STAGE_B/` (read-only). Adilabad updated and Aswaraopeta are derived built-up settlement extents, not administrative boundaries; the type of the Alampur boundary is stated in `alampur_boundary.provenance.json`. SHA-256 of the committed files is in `provenance_hashes.csv`.

## Alampur acquired data

`alampur_acquired_data_manifest.csv` (copied from `DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/03_ALAMPUR/`) lists every downloaded input file with its size, SHA-256 and source URL.
