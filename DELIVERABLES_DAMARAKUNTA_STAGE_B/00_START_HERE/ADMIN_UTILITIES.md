# Administrative and governance utilities (village baseline template)

Requested as primary administrative utility points: Gram Panchayat office, MeeSeva centre, Directorate of ESD (Aadhaar/service) centre. Status checked 2026-10-31.

| Utility | Status | Source | Position | Verification done |
|---|---|---|---|---|
| Damarakunta Gram Panchayat headquarters | **Included** in the facility layer | TGRAC `AdministrativeInfoSystem_Folder/Administrative_Information_System/MapServer/10` ("Gram Pancahayat Head Quarter", point layer; GP = Damarakunta, DMV code 1745013) | 17.706404 N, 78.753015 E (EPSG:32644 x 261687.56, y 1959125.49); attribute lat/lon equals the geometry (0.0 m) | Inside the village boundary; 0.7 m from a detected footprint (an unresolved-merge blob of 4,769 m2, so the building is not identified); 3.4 m from an Open Buildings polygon (41 m2, confidence 0.84); 216.6 m from the nearest other facility |
| Kashireddypally Gram Panchayat headquarters (second GP whose revenue village is Damarakunta) | **Included** | same layer (GP = Kashireddypally, same DMV code) | 17.699092 N, 78.779906 E (x 264531.25, y 1958282.22); attribute lat/lon equals the geometry | Inside the boundary; on a detected footprint (391 m2, unresolved merge); 2.5 m from an Open Buildings polygon (116 m2, confidence 0.86); 2.9 km from the other facilities, in the eastern settlement |
| MeeSeva centre | **Not located; not in the layer** | No source found: the 162 TGRAC MapServers (2,019 layers) have no layer with MeeSeva, ESD, Aadhaar or citizen-service in its name, and OpenStreetMap has no such feature in the village area | none | none |
| Directorate of ESD (Aadhaar/service) centre | **Not located; not in the layer** | same as above | none | none |

What "verified" means here: the two GP points come from an official TGRAC layer and agree with independent building layers (on or within a few metres of a footprint and an Open Buildings polygon). That shows consistency, not that the building is the Panchayat office; a visual or field check is still needed. TGRAC calls the point a "Head Quarter" location, not the office building.

To add MeeSeva and ESD: fill `inputs/admin_utilities_intake.csv` with the coordinate and its source (for example the MeeSeva "locate a centre" page, the UIDAI enrolment-centre locator, a field GPS reading or an official register), then re-run the facility-layer build. They will not be placed on a guess. In many villages the MeeSeva centre sits in the Panchayat office, but that is an assumption and is not applied.

Scaling to other villages: query the same TGRAC layer 10 by village or GP name; for MeeSeva and ESD use the same intake file.
