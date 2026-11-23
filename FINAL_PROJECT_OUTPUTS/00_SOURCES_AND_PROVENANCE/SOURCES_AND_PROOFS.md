# Data sources and provenance proofs (to be completed by the owner)

Pre-filled with the sources the pipeline uses. Licences are as understood when written and are NOT verified: fill the last two columns after checking each page, and attach proofs under `proofs/<study area>/`.

| source | URL | licence (to verify) | used for | verified by owner (date) | proof file |
|---|---|---|---|---|---|
| Esri World Imagery (0.6 m) | https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer | Esri Master Agreement / World Imagery terms; non-commercial academic use, credit required | all three |  |  |
| Overture Maps (buildings, transportation, places, divisions), release 2026-11-18.0 where used | https://docs.overturemaps.org/ | ODbL (buildings/transportation) and CDLA-Permissive-2.0 (places, divisions); check per theme | all three |  |  |
| ESA WorldCover 10 m | https://esa-worldcover.org/ | CC BY 4.0 | all three |  |  |
| Copernicus DEM GLO-30 | https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model | Copernicus licence | all three |  |  |
| OpenStreetMap / Overpass / Nominatim (boundary candidates) | https://www.openstreetmap.org/copyright | ODbL | adilabad_urban_updated, aswaraopeta |  |  |
| geoBoundaries ADM3 (2018 reference layer, frozen Adilabad run) | https://www.geoboundaries.org/ | CC BY 4.0 | adilabad_urban (frozen) |  |  |
| TGRAC village polygon (Damarakunta) |  | OWNER TO FILL | damarakunta |  |  |
| PMGSY rate Rs 75 lakh/km (60-90) |  | OWNER-SUPPLIED, UNVERIFIED: attach the circular or schedule of rates | all three (illustrative only) |  |  |

## Study-area boundaries

Polygon files and their provenance JSON are in each study area's `boundary/` folder (Adilabad updated, Aswaraopeta). Damarakunta's polygon is in `DELIVERABLES_DAMARAKUNTA_STAGE_B/` (read-only). Adilabad updated and Aswaraopeta are derived built-up settlement extents, not administrative boundaries. SHA-256 of the committed files is in `provenance_hashes.csv`.
