Damarakunta route reconstruction V3
===================================
CRS: EPSG:32644
Maximum facility snap distance: 35.0 m
Mapped-road endpoint tolerance: 15.0 m
Slope screening cap: 25.0 degrees

Outputs:
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\damarakunta_routes_v3.gpkg
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\damarakunta_routes_v3_comparison.csv
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\damarakunta_routes_v3_facility_checks.csv

Important limitations:
- These are GIS-generated planning candidates, not construction-ready roads.
- Alternative routes use a soft cost penalty around previous routes; alternatives with >85% cell overlap are rejected.
- snap_plus_route_length_proxy_m is the straight-line facility snap plus route-line length; it is not a verified travel distance.
- WorldCover is 10 m land-cover data and cannot reliably identify individual roofs.
- A zero built-up cell count does not prove every building is avoided.
- The slope threshold is a computational screening setting, not an engineering standard.
- The health-centre record has conflicting source coordinates and must be verified before interpreting its route.
- Verify route alignments, facility coordinates, land ownership, drainage and field feasibility.
