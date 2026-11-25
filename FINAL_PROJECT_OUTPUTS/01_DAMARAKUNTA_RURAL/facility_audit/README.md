# Facility audit: damarakunta

Produced by `scripts/audit_facilities.py --village damarakunta` (four passes). Final tables: `pass4_verified_facilities.csv` (also `configs/multivillage/villages/damarakunta_verified_facilities.csv`, read by the pipeline) and
`pass4_exclusions.csv` (every removed or merged record with its reason; also `damarakunta_facility_exclusions.csv`).

| file | content |
|---|---|
| `pass1_candidates.csv` | every source record harvested (OpenStreetMap, Overture Places, Wikidata, Wikipedia, local reference layers) before any cleaning |
| `pass2_clusters.csv` | records after classification (five categories), false-positive removal and duplicate merging across sources |
| `pass3_snapping.csv` | each facility with its source point, the footprint it was snapped to, snap distance and building area |
| `pass4_verified_facilities.csv` | facility_id, name, category, lat, lon, verification_sources, confidence, snapped_to_building, use_in_analysis (False = low confidence, for an on-site check) |
| `contact_sheet_NN.jpg` | Esri imagery chips (120 m): red x = source point, cyan ring = final marker, yellow = footprints |
| `sources_checked.json` | which sources answered and how many records each gave; sources that were not reachable are stated |
| `raw/` | saved raw answers (Overpass per query, Photon, Wikidata, Overture places) so the audit can be redone offline (`--from-raw`) |
| `damarakunta_facility_overrides.csv` (in configs/multivillage/villages/) | manual decisions after looking at the contact sheets or Google Maps |

Limits: LGD / UDISE+ / Telangana directories have no open query API and were not used; Overpass mirrors were overloaded at times (see `sources_checked.json` for the share of answered queries);
snapping uses the open Overture footprints (StrongDINOv2Seg footprints exist only on the owner's PC); anything that needs a field visit is listed with `use_in_analysis = False` or in the exclusions.
