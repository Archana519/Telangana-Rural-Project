Damarakunta route reconstruction V2
===================================
CRS: EPSG:32644
Maximum facility snap distance: 35.0 m
Mapped-road endpoint tolerance: 15.0 m
Slope screening cap: 25.0 degrees

Outputs:
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\damarakunta_routes_v2.gpkg
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\damarakunta_routes_v2_comparison.csv
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\damarakunta_routes_v2_facility_checks.csv

Important limitations:
- These are GIS-generated planning candidates, not construction-ready roads.
- Alternative routes exclude a one-cell corridor around earlier routes where possible.
- total_access_distance_m is the facility-to-start-cell snap plus route-line length.
- WorldCover is 10 m land-cover data and cannot reliably identify individual roofs.
- A zero built-up cell count does not prove every building is avoided.
- The slope threshold is a computational screening setting, not an engineering standard.
- Verify route alignments, facility coordinates, land ownership, drainage and field feasibility.
