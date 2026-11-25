# Proofs for alampur

Put here (not committed unless the licence allows): screenshots of the download pages, licence text, API responses, e-mails or letters that confirm each source in `../../SOURCES_AND_PROOFS.md`. Name files `<source>_<date>.<ext>`.

Items to attach:

- [ ] Boundary candidate table and preview (data/villages/alampur/aoi_candidates/) and the reason the chosen polygon was picked
- [ ] Overpass / Nominatim response (raw JSON) for the chosen OSM relation or way, with its retrieval date
- [ ] Overture release notes page for release 2026-10-21.0 (buildings, transportation, places) and the divisions release named in alampur_boundary.provenance.json
- [ ] ESA WorldCover v200 tile page and Copernicus DEM GLO-30 tile page for the tiles listed in `alampur_acquired_data_manifest.csv`
- [ ] Esri World Imagery terms page and a screenshot of one exported tile request (extent, size, date)
- [ ] geoBoundaries gbOpen IND ADM3 / ADM2 metadata JSON (licence ODbL 1.0, build date) used as the 2018 reference layer
- [ ] Facility audit: Google Maps / on-site check of every facility in alampur_verified_facilities.csv (and of the use_in_analysis = False rows), plus the evidence for every row of alampur_facility_exclusions.csv
- [ ] Any official polygon you hold (LGD / Census / municipal) if you decide to replace the derived boundary: pass it with `propose_aoi.py --use-file` and keep the file here
