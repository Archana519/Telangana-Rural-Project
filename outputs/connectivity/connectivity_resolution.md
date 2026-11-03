# Connectivity resolution (road-line topology)

Run `S2_fac_C0_s25_final_x4`. Planner results are unchanged. Road line components: 7 at 0.01 m joining, 6 at 10 m (raw TGRAC lines before gpd.clip(), including the 44.7% of the length outside the village polygon; the planner routes on the clipped roads only).

| Measure | Targets |
|---|---|
| Routed targets | 168 |
| Route end snaps to a TGRAC line within 15 m | 168 |
| Reaches the main component on the planning RASTER (planner definition) | 167 |
| Reaches the main component on the road LINES (0.01 m joining) | 168 |
| Reaches the main component on the road LINES (10 m joining) | 168 |

Exception C0002: raster says not connected; road lines say connected. Road-line path from its attachment to the main raster component: 630.4 m, of which 385.3 m lies outside the village polygon (about +/-5 m).

Reading: where lines are connected but the raster is not, the cut comes from clipping the grid to the village polygon, not from a gap in the road data. In the clipped network that is routed, C0002 is therefore not connected to the main road component inside the boundary: its only link runs through roads outside the boundary, which are excluded. This shows connectivity in the raw TGRAC lines; it does not show that the roads exist, are passable or are legally accessible. Bridge proposals: 0 (none needed).
