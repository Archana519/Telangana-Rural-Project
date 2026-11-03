# Exclusions applied to the deliverables

## Anganwadi Damarakunt-I (facility_id 1702300): excluded from the planning scenarios and from all new deliverable layers, CSVs and maps

Decision: requested by the project owner on 2026-10-31 ("remove the faulty out-of-settlement Anganwadi coordinate").

Evidence recorded before the exclusion (outputs verification of 2026-10-30): the TGRAC coordinate (17.703800 N, 78.747400 E, given to four decimals) lies
371 m from the nearest detected building footprint and 126 m from the nearest Google Open Buildings v3 polygon (30 m2); an undated Esri crop shows open scrub with no roof within 100 m.
Its planned route in the 4-facility runs was 168.9 m (cost 700.0), the longest facility route.

What was done
- A new facility layer without this point: `Siddipet/Damarakunta/reference/derived/damarakunta_priority_facilities_excl_1702300.gpkg` (3 facilities: MPPS and ZPHS schools, Sub Centre).
- The runner option `--fac-file` and the scenarios `S2_fac_C0_s25_final_*` plan with that layer. All final maps, charts, comparison tables, the chapter and the visual-audit kit are built from them.
- The original `reference/damarakunta_priority_facilities.gpkg` is NOT edited: it is a hash-pinned input of the verified reference run (`run_20261029_01`).

What this does not do
- It does not show the anganwadi is absent from the village; the point is excluded because its position is unsupported. The facility still needs a verified location (registry or Google Earth visual audit); until then the plan serves 3 of 4 priority facilities.
- The historical verified baseline (`results/run_20261029_01`, and its copies under `DELIVERABLES_DAMARAKUNTA_STAGE_B/03..05`) is left as it was so that the reproduction checks still hold; it still contains this facility. Delete it there if you want it scrubbed as well.
- This file and `outputs/verification/excluded_facilities.csv` are the only places that keep the excluded record, as an audit trail.
