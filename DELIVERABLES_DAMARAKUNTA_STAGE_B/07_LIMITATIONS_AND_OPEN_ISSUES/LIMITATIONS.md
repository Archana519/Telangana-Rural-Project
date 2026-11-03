> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# Limitations

## Claims not made
No field validation, legal road access, ownership confirmation, physical passability, construction savings, or real-world accessibility improvement. Costs are ordinal model units, not rupees. Evidence is on a 10 m planning grid.

## From the run configuration
- Building candidates are model detections, unverified. Routes are planning alternatives, not roads.
- Slope is a bilinear resample of a slope computed from a ~30 m DEM; it is not true 10 m terrain.
- TGRAC reference roads may be incomplete; only road cells inside the valid village grid are planner goals.
- Parcel counts are crossings of parcel units, not ownership or legal access.
- Facility identities and coordinates are not field-verified. The anganwadi was excluded from the deliverables because its coordinate lies 371 m from the nearest detected footprint (inputs/EXCLUSIONS.md).
- Imagery source/date/licence, model-weight location and TGRAC data licence are unresolved.

## C1 / C2
- Omission and addition scenarios are synthetic and deterministic (seeded), not measured segmentation false-negative rates. A shorter network with fewer routed targets is not greater efficiency; compare length per routed target.
- Shared-edge credit counts only identical grid edges; the planner is not globally optimal.
- K1/K3 summaries match at each pass setting but pairwise geometry identity is not established.

## Boundary-related connectivity limitation
Of 1,564 road-line-covered cells with invalid cost and prohibited-mask value 1, 1,532 (98.0%) have centres outside the study polygon; 32 are inside, within 23.3 m of it. 41,789.51 m of 93,496.76 m (44.70%) of TGRAC road geometry, in 20 of 43 features, lies outside the polygon.
House C0002 attaches to component 10 (5 cells, 155.24 m from the main cells in the road-cell diagnostic). This is documented as a boundary-truncation limitation of the planning domain; no cell was made passable, no routing was done outside the polygon, and the planner is not shown to be defective. On the TGRAC lines the same road is connected to the main network (about 630 m along the lines, 385 m of it outside the polygon).

## Building avoidance
Hard blocking of footprint cells fails (every house point lies inside its own blocked cell). The buffer scenario keeps some house routes crossing another footprint, most of them only within the first 20 m of the route (table6_obstacle_avoidance.csv).

## Boundary
The saved boundary equals the stored raw TGRAC response exactly (EPSG:32644, IoU 1.0). Authority and currentness of the TGRAC polygon were not verified; the cadastral union covers 97.81% of the boundary, a cross-check only.

## Figures
The C1 bar chart (`fig1_length_and_per_routed.png`) had its legend overlapping a value label. No figure is declared publication-ready.
