# DATA_SOURCES — Angadi Kistapur, Markook, Siddipet

Status as of 30 Sep 2026. "Verified" = confirmed from an official or primary page; "Not verified" = could not be confirmed yet. Nothing here has been downloaded; `download_manifest.csv` starts empty and is filled by the scripts.

## Study-area identity (secondary evidence, to be confirmed by `scripts/verify_siddipet_village.py`)

| Item | Value | Evidence | Status |
|---|---|---|---|
| Village | Angadi Kistapur | Wikidata Q15687164 (cites District Census Handbook) | Secondary |
| Mandal / district | Markook / Siddipet | Wikidata; village lists | Secondary |
| Census 2011 village code | 573656 | Wikidata Q15687164 | Verify against Census PCA |
| Population / households (2011) | 998 / 224 | Wikidata Q15687164 | Verify against Census PCA |
| Area (2011) | 461 ha | Wikidata Q15687164 | Verify against boundary |
| LGD village code | — | — | Not verified |
| Context note | Markook mandal is within the HMDA region | Wikipedia, Markook mandal | Report in thesis |

## Datasets

| Dataset | Provider | URL | Coverage | Resolution | Format | CRS | Date | License | Download method | Account? | Free? | Purpose | Limitations | Citation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Master Administrative Boundary | TGRAC | tgrac.telangana.gov.in/arcgis/rest/services/Master_Administrative_Folder/Master_Administrative_Boundary/MapServer | Telangana | Vector | ArcGIS REST | Not verified | Not verified | Not stated | REST query (if Query enabled) | No | Not verified | Village boundary, hierarchy | Licence unknown | TGRAC, Govt of Telangana |
| Abadi_Final (Angadi Kistapur layers, drone + satellite image layers) | TGRAC | …/Abadi_Folder/Abadi_Final/MapServer | Named villages | Not verified | MapServer | Not verified | Not verified | Not stated → treat as not licensed | MapServer export = rendered picture only; original pixels only via an ImageServer (none verified) | No | — | Candidate imagery + building/plinth reference | Permission required before use | TGRAC |
| Schools (SchoolGIS) | TGRAC | …/SchoolGIS_Folder/Schools/MapServer | Telangana | Points | ArcGIS REST | Not verified | Not verified | Not stated | REST query | No | Not verified | Schools, Anganwadi | Completeness unknown | TGRAC |
| Health_Facilities_Query | TGRAC | …/GovtHospitals_Folder/Health_Facilities_Query/MapServer | Telangana | Points | ArcGIS REST | Not verified | Not verified | Not stated | REST query | No | Not verified | PHC/CHC/sub-centre | Completeness unknown | TGRAC |
| BaseLayers | TGRAC | …/TGIIC_Folder/BaseLayers/MapServer | Telangana | Vector | ArcGIS REST | Not verified | Not verified | Not stated | REST query | No | Not verified | Roads, tanks, rivers | Unknown | TGRAC |
| SRTM 1 arc-second | USGS/NASA | earthexplorer.usgs.gov | Global | ~30 m | GeoTIFF | EPSG:4326 | 2000 | Public domain, credit requested | EarthExplorer | Yes (free) | Yes | Elevation, slope | 30 m; cannot show micro-terrain | NASA SRTM, USGS |
| ESA WorldCover 2021 v200 | ESA/VITO | esa-worldcover.org | Global | 10 m | COG GeoTIFF | EPSG:4326 | 2021 | CC BY 4.0 | One 3×3° tile | No | Yes | Land-cover cost, water, trees (support only) | 10 m; 2021 | Zanaga et al. 2022 |
| PMGSY GeoSadak open data | MoRD/NRIDA | geosadak-pmgsy.nic.in/OpenData | India | Vector | SHP/GeoJSON | Not verified | Not verified | GODL-India | Download (may need Indian IP) | No | Yes | Rural roads, habitations, facilities | Siddipet coverage Not verified | NRIDA |
| Google Open Buildings V3 | Google Research | sites.research.google/gr/open-buildings/ | South Asia | Polygons from 50 cm imagery | CSV (WKT) | EPSG:4326 | May 2023 inference | CC BY 4.0 / ODbL | One S2-cell CSV | No | Yes | Building REFERENCE, pseudo-labels | Model output; confidence varies | Sirko et al. 2021 |
| OpenStreetMap (Southern Zone) | Geofabrik / OSM | download.geofabrik.de/asia/india.html | Southern India | Vector | .osm.pbf | EPSG:4326 | Daily | ODbL | One regional extract, clipped | No | Yes | Roads, water, POIs (supplementary) | Rural completeness varies | © OpenStreetMap contributors |
| Census 2011 PCA / Village Directory | ORGI | censusindia.gov.in/nada/index.php/catalog/42559 | India | Village table | XLSX | — | 2011 | OGDL-India | Download | No | Yes | Population, 2011 amenities (context only) | 15 years old; filed under Andhra Pradesh | ORGI 2011 |
| Sentinel-2 L2A | ESA Copernicus | dataspace.copernicus.eu | Global | 10/20/60 m | SAFE/COG | UTM | 2015– | Open | Browser or API | Yes (free) | Yes | Seasonal land-cover/water support only | Too coarse for rural buildings/roads | ESA Copernicus |

## Imagery decision status
Sub-metre imagery that can legally be used for training, evaluation and figures is **not yet secured**. Order of preference: (1) TGRAC imagery with written permission and native-resolution access; (2) NRSC Cartosat through Bhoonidhi (priced for non-government users); (3) SVAMITVA orthophoto via official request. Sentinel-2 is not a substitute for building/road segmentation.
