DAMARAKUNTA V4 ROUTE CONNECTIVITY VALIDATION

Routes checked: 10
Mapped road tolerance (screening only): 15.0 m
Facility distance tolerance (screening only): 5.0 m
Approximate raster sample spacing: 5.0 m
Global mask/cost NoData mismatch cells: 0
Road connection classifications: {'POINT_CONTACT_ONLY': 8, 'NEAR_ROAD_BUT_NO_INTERSECTION': 2}

LIMITATIONS:
- This script reads the V4 route_alternatives layer directly.
- Raster samples are spaced approximately 5 m apart; not every pixel crossed is guaranteed to be sampled.
- WorldCover 10 m classes do not verify individual roof/building clearance.
- Geometric intersections do not prove navigable road-network topology.
- Facility locations are not independently verified.
- Ownership, legal right-of-way, drainage, road width, and construction feasibility are not established.
- A near-road result is not equivalent to a connected route.
- Outputs are preliminary GIS screening only.