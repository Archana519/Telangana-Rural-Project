# Detection and facility verification

No building ground truth exists in this project, so nothing here is an accuracy figure. Agreement is with independent layers (TGRAC tables, school compounds, Google Open Buildings v3). Thresholds were fixed before the run: footprint within 20 m, Open Buildings within 30 m, IoU >= 0.25.

## Facilities (latitude/longitude from the geometry)

| facility_id                  | name                                                            |     lat |     lon |   table_vs_geometry_m | inside_school_compound   |   dist_to_nearest_footprint_m | nearest_footprint_class   |   nearest_open_buildings_m | verdict      |
|:-----------------------------|:----------------------------------------------------------------|--------:|--------:|----------------------:|:-------------------------|------------------------------:|:--------------------------|---------------------------:|:-------------|
| 36181600902                  | Mpps Damarakunta                                                | 17.7073 | 78.7505 |                   nan | MPPS DAMARAKUNTA         |                           8.5 | UNRESOLVED_MERGE          |                        0   | CORROBORATED |
| 36181600903                  | Zphs Damarakunta                                                | 17.7076 | 78.7505 |                   nan | ZPHS DAMARAKUNTA         |                           3.1 | UNRESOLVED_MERGE          |                        1.4 | CORROBORATED |
| HEALTH_8734223673            | Sub Centre, Damarakunta                                         | 17.7082 | 78.7538 |                   nan |                          |                           1.8 | UNRESOLVED_MERGE          |                        8.7 | CORROBORATED |
| GP_DAMARAKUNTA               | Damarakunta Gram Panchayat HQ                                   | 17.7064 | 78.753  |                     0 |                          |                           0.7 | UNRESOLVED_MERGE          |                        3.4 | CORROBORATED |
| GP_KASHIREDDYPALLY           | Kashireddypally Gram Panchayat HQ (Damarakunta revenue village) | 17.6991 | 78.7799 |                     0 |                          |                           0   | UNRESOLVED_MERGE          |                        2.5 | CORROBORATED |
| HEALTH_ALT_health_layer      | Sub Centre, Damarakunta                                         | 17.7082 | 78.7538 |                     0 |                          |                           1.8 | UNRESOLVED_MERGE          |                        8.7 | CORROBORATED |
| HEALTH_ALT_sub_centres_layer | SubCentre, Damarakunta                                          | 17.7072 | 78.7519 |                     0 |                          |                           0   | PLAUSIBLE                 |                        0.5 | CORROBORATED |

## Building candidates inside the boundary versus Open Buildings v3 (proxy agreement)

| group            |   candidates |   proxy_TP |   proxy_FP |   proxy_agreement_rate |
|:-----------------|-------------:|-----------:|-----------:|-----------------------:|
| ALL              |          165 |        118 |         47 |                  0.715 |
| PLAUSIBLE        |           71 |         51 |         20 |                  0.718 |
| REVIEW           |           32 |         14 |         18 |                  0.438 |
| UNRESOLVED_MERGE |           62 |         53 |          9 |                  0.855 |

Reference polygons with confidence >= 0.70 and no candidate (proxy false negatives): 1186 of 1298 (proxy recall-like 0.09). These include sheds, farm buildings and structures the project's extraction did not keep, so a low value does not by itself mean missed houses.

Read these as: the share of candidates that another detector also sees (proxy-TP) and the share that only this project sees (proxy-FP, which may be real buildings Open Buildings missed). Neither measures real accuracy; that needs labelled buildings (Phase-II).
