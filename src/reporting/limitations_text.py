"""Text of the 'Methodological Limitations and Future Scope' section, shared by the thesis chapter (Section 13) and the deliverables folder.

Facts here come from project records (docs/DAMARAKUNTA_STAGE_B_C_PROPOSALS.md, inputs/METADATA.md, reference/external/esri_world_imagery_identify.json,
Zenodo record of LoveDA). Nothing here is legal advice and no usage term has been confirmed in writing.
"""

TEXT = """## 13. Methodological Limitations and Future Scope

### 13.1 Data sources, attribution and usage terms (status as of 2026-10-31)
The terms below are what the project has recorded. **None has been confirmed in writing**, and nothing here is legal advice or a statement that academic use, redistribution or publication of the data or of figures made from it is permitted.

| Dataset | Source and attribution to cite | Recorded terms and status | Action before publication |
|---|---|---|---|
| TGRAC village boundary, 43 road lines, facilities (school and health layers; Gram Panchayat headquarters points from layer 10; the anganwadi record is excluded), cadastral parcels, school compounds | TGRAC, Government of Telangana (name as used in the project); ArcGIS REST services at tgrac.telangana.gov.in (boundary: Administrative Information System MapServer layer 27; roads: Schools MapServer layer 20); downloaded 4 to 5 Oct 2026 | No licence or terms of use were found for these services as recorded. Currentness, completeness and authority are not verified. The saved boundary equals the stored query response (IoU 1.0), which shows consistency, not authority | Ask TGRAC in writing for terms for research use and for publishing derived maps; record the query date; cite as TGRAC, Government of Telangana |
| Esri World Imagery 0.6 m mosaic (11,296 x 7,171 px) | Esri World Imagery. The identify result saved with the project names Vantor (60 cm layer, dated 29 Apr 2026 at the one point sampled) and Earthstar Geographics as sources; attribution to Esri and its data providers is required by the terms summary the project recorded | The recorded Esri terms summary (21 Apr 2025) says basemap data may only be taken offline using Esri Content Packages, prohibits systematic harvesting of tiles by other methods, and requires attribution. The mosaic was built from 11 map-image export requests (4 Oct 2026), not Content Packages. Whether this use, model inference on the pixels, and publishing derived maps or figures is allowed is **not determined**. The enquiry draft has not been sent. Acquisition dates elsewhere in the mosaic are not recorded | Send the enquiry (or ask CBIT's GIS office whether an ArcGIS licence covers it). Until answered, do not redistribute the imagery or figures containing it; maps with imagery are review drafts |
| Building footprints (278 candidates) | Project extraction from the imagery above | Derived from imagery of unresolved terms, so the same question applies | Settle the imagery terms first |
| ESA WorldCover | ESA WorldCover (esa-worldcover.org); project notes record 2021 v200, not stored in the raster | CC BY 4.0 per project notes (not re-checked) | Confirm the product version and cite as the product requires |
| DEM (30 m, interpolated to 10 m) | Source not recorded; the file name n17_e078_1arc_v3 suggests an SRTM-type 1 arc-second product | Unknown | Identify the product and its terms |
| Google Open Buildings v3 (agreement checks only) | Sirko et al., 2021 | CC BY 4.0 / ODbL per Google's notes (not re-checked) | Cite |
| LoveDA (segmentation benchmark only) | Wang et al., NeurIPS 2021 Datasets and Benchmarks; doi 10.5281/zenodo.5706578 | CC BY 4.0 per its Zenodo record (checked 29 Oct 2026) | Cite |

### 13.2 Field validation status
Every route in this work is the output of a **GIS simulation**: an ordinal cost surface on a 10 m raster, built from ESA WorldCover land cover and slope computed from a DEM of about 30 m resolution that was interpolated to 10 m, with the TGRAC road lines as the existing network and automatically detected building footprints as targets. The routes are unverified planning alternatives (status `UNVERIFIED_PLANNING_ALTERNATIVE_NOT_A_ROAD`).
**No ground truthing has been done.** There has been no field visit, no surveyed road centreline, width, drainage or soil data, no check of ownership or right of way, and no confirmation of facility positions or of building use. Interpolating a 30 m DEM does not give 10 m terrain accuracy. **Ground-level physical validation is designated for future phases.**

Proposed validation steps (not scheduled):
1. Verify facility positions against a registry, Google Earth and then the field; re-include the excluded anganwadi once its location is verified; locate the MeeSeva and Directorate of ESD (Aadhaar/service) centres and add them through `inputs/admin_utilities_intake.csv`; confirm which building is the Gram Panchayat office.
2. Label a subset of buildings in the village to measure detector precision and recall, and to replace the synthetic C1 omissions with measured errors.
3. Walk a sample of the proposed routes and record obstructions, width, gradient, drainage and crossings.
4. Check parcel and right-of-way status with revenue records.
5. Compare the DEM slope with a surveyed or higher-resolution profile.
6. Replace the illustrative cost and material assumptions with State Schedule of Rates values and a design section.

### 13.3 Network generalisation (C3)
C3 asks whether the method carries over to other villages. **It has not started.** Only Damarakunta has been processed, and no transfer result exists or is claimed. Testing across multiple villages remains part of the extended future work and begins only after the project owner approves the Damarakunta completion gate in writing. Planned, not scheduled: five additional villages, the same pipeline and metrics, a per-village input check (imagery, boundary, roads, facilities, DEM) and the licence questions of Section 13.1 settled first. Results from Damarakunta, for example the unique-length saving of the shared network, must not be quoted as general.

### 13.4 Other methodological limits
- Two Gram Panchayat headquarters points are included as administrative utilities; the MeeSeva and ESD centres are not, because no coordinate source exists.
- Costs are ordinal planning units, not rupees; the economic and material figures are assumption-driven and illustrative.
- The planner is a greedy heuristic with no optimality guarantee; shared-edge credit counts identical grid edges only.
- Building detections are unverified and the 163 routing targets are not a house count; agreement with Open Buildings is not accuracy.
- The omit/add runs (C1) are synthetic probes, not measured segmentation error.
- Building avoidance is bounded, not complete: some house routes still cross a neighbouring footprint (counts in Table 6), mostly where a target starts among touching buildings.
- 44.7% of the raw TGRAC road length lies outside the village polygon. The road layer was clipped to the boundary with gpd.clip() (51,707 m of 93,497 m remain, in 50 parts) and only the clipped roads are routed; the boundary itself has not been independently validated.
- The route of the health sub-centre uses a manual local override: the building penalty is lifted within 20 m of the facility point because the facility sits at the edge of its own footprint. The override changes no other route and is not a verified finding about access.
- 961 slope cells and 178 land-cover cells inside the boundary have no value because of the coarse 30 m DEM and land-cover source. This is a spatial limitation: the gaps are not filled by interpolation, and the planner treats them as invalid cells.
"""
