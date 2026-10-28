# Inspection report | root=D:\Telangana_Rural_Project | village=Siddipet\Damarakunta | 2026-10-24 16:19
Files scanned: 1865

## 1. Model weights / checkpoints
NONE FOUND (.pt/.pth/.ckpt/.safetensors > 1 MB)

## 2. Building / candidate vector outputs
- D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\derived\buildings.gpkg [buildings] | n=52 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=82.2/895.6/7419360.1 | invalid=0
    columns: ['building_id', 'pixel_area', 'area_m2', 'bbox_width_px', 'bbox_height_px', 'centroid_x', 'centroid_y', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\results\phase18_new_road_candidates.gpkg [candidate_routes] | n=15 | geom=['LineString'] | crs=EPSG:32644
    columns: ['route_id', 'facility_id', 'facility_name', 'facility_type', 'priority_group', 'candidate_route', 'candidate_type', 'route_length_m', 'mean_cost', 'coverage_gap_percentage', 'water_percentage', 'builtup_percentage', 'cropland_percentage', 'vegetation_percentage']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\planning_experiments\access_gain_v1\ag1\buildings_access.gpkg [buildings_access] | n=163 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=10.4/235.8/4769.3 | invalid=0
    columns: ['cand_id', 'cluster_id', 'quality_class', 'cluster_kind', 'in_gap_cluster', 'polygon_gap_flag', 'd_base_m', 'd_run5_na_m', 'd_run5_ic_m', 'd_run6_slope_soft_na_m', 'd_run6_slope_soft_ic_m', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\access\access_assessment.gpkg [candidate_access] | n=113 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=10.4/204.8/25550.6 | invalid=0
    columns: ['cand_id', 'comp_id', 'area_m2', 'mean_prob', 'max_prob', 'status', 'dist_to_ref_road_m', 'cluster_id', 'gap_flag', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\access\access_assessment.gpkg [clusters] | n=33 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=453.8/1081.4/100790.0 | invalid=0
    columns: ['cluster_id', 'n_candidates', 'footprint_area_m2', 'min_dist_to_ref_road_m', 'extent_area_m2', 'kind', 'gap_flag', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\access\access_assessment.gpkg [facility_access] | n=4 | geom=['Point'] | crs=EPSG:32644 | POINTS ONLY (not footprints)
    columns: ['facility_id', 'facility_name', 'facility_type', 'priority_group', 'source', 'dist_to_ref_road_m', 'nearest_cand_id', 'dist_to_nearest_cand_m', 'nearest_cluster_id', 'dist_to_nearest_cluster_m', 'near_candidate_building', 'note', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\candidate_buildings_full.gpkg [candidate_buildings] | n=113 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=10.4/204.8/25550.6 | invalid=0
    columns: ['cand_id', 'comp_id', 'area_m2', 'mean_prob', 'max_prob', 'status', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\plan_gap1\plan.gpkg [stageA_alternatives] | n=42 | geom=['LineString'] | crs=EPSG:32644
    columns: ['target', 'kind', 'alt', 'length_m', 'cost', 'status', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\plan_gap1\plan.gpkg [stageB_credit_plan] | n=15 | geom=['LineString'] | crs=EPSG:32644
    columns: ['target', 'kind', 'alt', 'length_m', 'cost', 'status', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\plan_gap1\plan.gpkg [independent_plan] | n=15 | geom=['LineString'] | crs=EPSG:32644
    columns: ['target', 'kind', 'alt', 'length_m', 'cost', 'status', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\plan_gap1\plan.gpkg [straight_baseline] | n=15 | geom=['LineString'] | crs=EPSG:32644
    columns: ['target', 'kind', 'alt', 'length_m', 'cost', 'status', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\reference\digitize_windows.gpkg [windows] | n=6 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=40000.0/40000.0/40000.0 | invalid=0
    columns: ['window_id', 'role', 'cx', 'cy', 'n_pred', 'pred_area_m2', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\routes_burnin\routes_v4style.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\routes_centeronly\routes_v4style.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\routes_scored\routes_scored.gpkg [routes_scored] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\anytouch_min10\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\dilate2m\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s1\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s2\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s3\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s4\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s5\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s1\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s2\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s3\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s4\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s5\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s1\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s2\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s3\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s4\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s5\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\min100\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\min25\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\min50\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\ref_center_min10\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\anytouch_min10\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\dilate2m\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s1\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s2\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s3\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s4\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s5\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s1\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s2\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s3\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s4\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s5\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s1\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s2\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s3\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s4\r.gpkg [route_alternatives] | n=10 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s5\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\min100\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\min25\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\min50\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\ref_center_min10\r.gpkg [route_alternatives] | n=9 | geom=['LineString'] | crs=EPSG:32644
    columns: ['facility_id', 'facility_name', 'facility_type', 'alternative', 'status', 'raster_path_length_m', 'facility_connector_length_m', 'road_connector_length_m', 'total_geometry_length_m', 'facility_to_nearest_road_m', 'facility_to_start_snap_m', 'start_cell_to_road_m', 'end_cell_to_road_m', 'route_to_road_geometry_m']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v7_instances\buildings_v7_full.gpkg [buildings] | n=326 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=7.2/175.5/2523.6 | invalid=0
    columns: ['cand_id', 'bld_id', 'comp_id', 'piece', 'n_in_comp', 'area_m2', 'perimeter_m', 'solidity', 'compactness', 'mean_prob', 'max_prob', 'flags', 'inside_village', 'status']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v7_instances\buildings_v7_full.gpkg [components] | n=228 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=7.2/142.0/25550.6 | invalid=0
    columns: ['comp_id', 'n_pixels', 'area_m2', 'n_pieces', 'mean_prob', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\access\access_assessment.gpkg [candidate_access] | n=163 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=10.4/235.8/4769.3 | invalid=0
    columns: ['cand_id', 'bld_id', 'comp_id', 'piece', 'n_in_comp', 'split_method', 'neck_ratio', 'area_m2', 'perimeter_m', 'solidity', 'compactness', 'mean_prob', 'max_prob', 'nodata_frac']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\access\access_assessment.gpkg [clusters] | n=33 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=453.8/1081.4/100790.0 | invalid=0
    columns: ['cluster_id', 'n_candidates', 'footprint_area_m2', 'min_dist_to_ref_road_m', 'extent_area_m2', 'n_unresolved_merge', 'n_plausible', 'kind', 'gap_flag', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\access\access_assessment.gpkg [facility_access] | n=4 | geom=['Point'] | crs=EPSG:32644 | POINTS ONLY (not footprints)
    columns: ['facility_id', 'facility_name', 'facility_type', 'priority_group', 'source', 'dist_to_ref_road_m', 'nearest_cand_id', 'dist_to_nearest_cand_m', 'nearest_cluster_id', 'dist_to_nearest_cluster_m', 'near_candidate_building', 'note', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\buildings_v8_full.gpkg [buildings] | n=278 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=7.2/170.5/4769.3 | invalid=0
    columns: ['cand_id', 'bld_id', 'comp_id', 'piece', 'n_in_comp', 'split_method', 'neck_ratio', 'area_m2', 'perimeter_m', 'solidity', 'compactness', 'mean_prob', 'max_prob', 'nodata_frac']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\buildings_v8_full.gpkg [components] | n=228 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=7.2/142.0/25550.6 | invalid=0
    columns: ['comp_id', 'area_m2', 'n_pieces', 'mean_prob', 'geometry']
- D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v8_instances\buildings_v8_full.gpkg [rejected] | n=10 | geom=['Polygon'] | crs=EPSG:32644 | area m2 min/median/max=25.2/25.2/25.2 | invalid=0
    columns: ['comp_id', 'piece', 'n_in_comp', 'split_method', 'neck_ratio', 'area_m2', 'perimeter_m', 'solidity', 'compactness', 'mean_prob', 'max_prob', 'nodata_frac', 'edge_mosaic', 'reject_reason']

## 3. Rasters: imagery and prediction masks
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_cost_surface.tif | 448x266 | bands=1 float32 | res=8.932 | crs=EPSG:32644 | bounds=(257818.5, 1968284.5, 261820.2, 1970660.5) | 0.3 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_dem.tif | 136x77 | bands=1 int16 | res=0.000 | crs=EPSG:4326 | bounds=(78.7, 17.8, 78.8, 17.8) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_full_village_georeferenced.tif | 2000x2000 | bands=3 uint8 | res=0.000 | crs=EPSG:4326 | bounds=(78.7, 17.8, 78.8, 17.8) | 1.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_georeferenced.tif | 1000x1000 | bands=3 uint8 | res=0.000 | crs=EPSG:4326 | bounds=(78.7, 17.8, 78.8, 17.8) | 1.7 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_slope.tif | 136x77 | bands=1 float32 | res=0.000 | crs=EPSG:4326 | bounds=(78.7, 17.8, 78.8, 17.8) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_slope_filled_10m.tif | 448x266 | bands=1 float32 | res=8.932 | crs=EPSG:32644 | bounds=(257818.5, 1968284.5, 261820.2, 1970660.5) | 0.3 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_slope_utm44n_10m.tif | 448x266 | bands=1 float32 | res=8.932 | crs=EPSG:32644 | bounds=(257818.5, 1968284.5, 261820.2, 1970660.5) | 0.3 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_utm44n.tif | 1981x2066 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(257812.1, 1967379.9, 261827.4, 1971567.5) | 1.4 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_worldcover.tif | 450x252 | bands=1 uint8 | res=0.000 | crs=EPSG:4326 | bounds=(78.7, 17.8, 78.8, 17.8) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_worldcover_utm44n.tif | 448x266 | bands=1 uint8 | res=8.932 | crs=EPSG:32644 | bounds=(257818.5, 1968284.5, 261820.2, 1970660.5) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_001_r00_c00.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(257812.1, 1970432.4, 258947.2, 1971567.5) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_002_r00_c01.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(258720.2, 1970432.4, 259855.3, 1971567.5) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_003_r00_c02.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(259628.2, 1970432.4, 260763.3, 1971567.5) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_004_r00_c03.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260536.3, 1970432.4, 261671.4, 1971567.5) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_005_r00_c04.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260692.4, 1970432.4, 261827.4, 1971567.5) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_006_r01_c00.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(257812.1, 1969524.4, 258947.2, 1970659.4) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_007_r01_c01.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(258720.2, 1969524.4, 259855.3, 1970659.4) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_008_r01_c02.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(259628.2, 1969524.4, 260763.3, 1970659.4) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_009_r01_c03.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260536.3, 1969524.4, 261671.4, 1970659.4) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_010_r01_c04.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260692.4, 1969524.4, 261827.4, 1970659.4) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_011_r02_c00.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(257812.1, 1968616.3, 258947.2, 1969751.4) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_012_r02_c01.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(258720.2, 1968616.3, 259855.3, 1969751.4) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_013_r02_c02.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(259628.2, 1968616.3, 260763.3, 1969751.4) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_014_r02_c03.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260536.3, 1968616.3, 261671.4, 1969751.4) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_015_r02_c04.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260692.4, 1968616.3, 261827.4, 1969751.4) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_016_r03_c00.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(257812.1, 1967708.2, 258947.2, 1968843.3) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_017_r03_c01.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(258720.2, 1967708.2, 259855.3, 1968843.3) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_018_r03_c02.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(259628.2, 1967708.2, 260763.3, 1968843.3) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_019_r03_c03.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260536.3, 1967708.2, 261671.4, 1968843.3) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_020_r03_c04.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260692.4, 1967708.2, 261827.4, 1968843.3) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_021_r04_c00.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(257812.1, 1967379.9, 258947.2, 1968515.0) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_022_r04_c01.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(258720.2, 1967379.9, 259855.3, 1968515.0) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_023_r04_c02.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(259628.2, 1967379.9, 260763.3, 1968515.0) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_024_r04_c03.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260536.3, 1967379.9, 261671.4, 1968515.0) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\tiles_560\tile_025_r04_c04.tif | 560x560 | bands=3 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(260692.4, 1967379.9, 261827.4, 1968515.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\predictions\angadi_kistapur_segmentation.tif | 1981x2066 | bands=1 uint8 | res=2.027 | crs=EPSG:32644 | bounds=(257812.1, 1967379.9, 261827.4, 1971567.5) | 0.2 MB | values={1: 1010258, 2: 373199, 4: 365257, 5: 400488, 6: 276, 7: 100522}
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\raw\dem\n17_e078_1arc_v3.tif | 3601x3601 | bands=1 int16 | res=0.000 | crs=EPSG:4326 | bounds=(78.0, 17.0, 79.0, 18.0) | 26.0 MB | tags={'DTED_CompilationDate': '0002', 'DTED_MaintenanceDate': '0000', 'DTED_MatchMergeDate': '0000'}
- single-band D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\raw\landcover\ESA_WorldCover_10m_2021_v200_N15E078_Map.tif | 36000x36000 | bands=1 uint8 | res=0.000 | crs=EPSG:4326 | bounds=(78.0, 15.0, 81.0, 18.0) | 116.3 MB | tags={'copyright': 'ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium', 'creation_time': '2022-10-21 07:35:40.236136', 'license': 'CC-BY 4.0 - https://creativecommons.org/licenses/by/4.0/', 'time_end': '2021-12-31T23:59:59Z', 'time_start': '2021-01-01T00:00:00Z'}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_cost_surface_10m.tif | 679x432 | bands=1 float32 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.8 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_dem_30m.tif | 227x144 | bands=1 float32 | res=30.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265620.0, 1960920.0) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_esri_highres_mosaic_0p6m.tif | 11296x7171 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1956609.5, 265592.5, 1960912.1) | 241.3 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_model_input_rgb.tif | 2048x2048 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1956609.3, 265592.3, 1960912.1) | 7.1 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_prohibited_mask_10m.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB | values={0: 183370, 1: 109958}
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_sentinel2_model_rgb_uint8.tif | 682x436 | bands=3 uint8 | res=10.000 | crs=EPSG:32643 | bounds=(895310.0, 1959120.0, 902130.0, 1963480.0) | 0.3 MB | tags={'source': 'Copernicus Sentinel-2 L2A'}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_slope_10m.tif | 679x432 | bands=1 float32 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.9 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_slope_30m.tif | 227x144 | bands=1 float32 | res=30.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265620.0, 1960920.0) | 0.1 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\aligned\damarakunta_worldcover_10m.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0001.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1960576.1, 259150.9, 1960912.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0002.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1960576.1, 259486.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0003.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1960576.1, 259822.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0004.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1960576.1, 260158.9, 1960912.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0005.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1960576.1, 260494.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0006.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1960576.1, 260830.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0007.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1960576.1, 261166.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0008.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1960576.1, 261502.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0009.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1960576.1, 261838.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0010.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1960576.1, 262174.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0011.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1960576.1, 262510.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0012.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1960576.1, 262846.9, 1960912.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0013.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1960576.1, 263182.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0014.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1960576.1, 263518.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0015.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1960576.1, 263854.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0016.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1960576.1, 264190.9, 1960912.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0017.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1960576.1, 264526.9, 1960912.1) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0018.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1960576.1, 264862.9, 1960912.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0019.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1960576.1, 265198.9, 1960912.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0020.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1960576.1, 265534.9, 1960912.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0021.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1960576.1, 265870.9, 1960912.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0022.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1960240.1, 259150.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0023.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1960240.1, 259486.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0024.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1960240.1, 259822.9, 1960576.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0025.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1960240.1, 260158.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0026.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1960240.1, 260494.9, 1960576.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0027.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1960240.1, 260830.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0028.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1960240.1, 261166.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0029.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1960240.1, 261502.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0030.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1960240.1, 261838.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0031.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1960240.1, 262174.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0032.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1960240.1, 262510.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0033.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1960240.1, 262846.9, 1960576.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0034.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1960240.1, 263182.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0035.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1960240.1, 263518.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0036.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1960240.1, 263854.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0037.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1960240.1, 264190.9, 1960576.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0038.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1960240.1, 264526.9, 1960576.1) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0039.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1960240.1, 264862.9, 1960576.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0040.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1960240.1, 265198.9, 1960576.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0041.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1960240.1, 265534.9, 1960576.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0042.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1960240.1, 265870.9, 1960576.1) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0043.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1959904.1, 259150.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0044.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1959904.1, 259486.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0045.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1959904.1, 259822.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0046.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1959904.1, 260158.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0047.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1959904.1, 260494.9, 1960240.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0048.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1959904.1, 260830.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0049.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1959904.1, 261166.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0050.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1959904.1, 261502.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0051.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1959904.1, 261838.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0052.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1959904.1, 262174.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0053.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1959904.1, 262510.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0054.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1959904.1, 262846.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0055.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1959904.1, 263182.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0056.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1959904.1, 263518.9, 1960240.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0057.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1959904.1, 263854.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0058.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1959904.1, 264190.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0059.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1959904.1, 264526.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0060.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1959904.1, 264862.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0061.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1959904.1, 265198.9, 1960240.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0062.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1959904.1, 265534.9, 1960240.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0063.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1959904.1, 265870.9, 1960240.1) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0064.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1959568.1, 259150.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0065.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1959568.1, 259486.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0066.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1959568.1, 259822.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0067.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1959568.1, 260158.9, 1959904.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0068.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1959568.1, 260494.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0069.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1959568.1, 260830.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0070.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1959568.1, 261166.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0071.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1959568.1, 261502.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0072.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1959568.1, 261838.9, 1959904.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0073.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1959568.1, 262174.9, 1959904.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0074.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1959568.1, 262510.9, 1959904.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0075.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1959568.1, 262846.9, 1959904.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0076.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1959568.1, 263182.9, 1959904.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0077.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1959568.1, 263518.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0078.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1959568.1, 263854.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0079.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1959568.1, 264190.9, 1959904.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0080.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1959568.1, 264526.9, 1959904.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0081.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1959568.1, 264862.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0082.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1959568.1, 265198.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0083.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1959568.1, 265534.9, 1959904.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0084.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1959568.1, 265870.9, 1959904.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0085.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1959232.1, 259150.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0086.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1959232.1, 259486.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0087.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1959232.1, 259822.9, 1959568.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0088.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1959232.1, 260158.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0089.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1959232.1, 260494.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0090.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1959232.1, 260830.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0091.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1959232.1, 261166.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0092.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1959232.1, 261502.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0093.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1959232.1, 261838.9, 1959568.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0094.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1959232.1, 262174.9, 1959568.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0095.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1959232.1, 262510.9, 1959568.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0096.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1959232.1, 262846.9, 1959568.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0097.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1959232.1, 263182.9, 1959568.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0098.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1959232.1, 263518.9, 1959568.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0099.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1959232.1, 263854.9, 1959568.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0100.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1959232.1, 264190.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0101.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1959232.1, 264526.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0102.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1959232.1, 264862.9, 1959568.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0103.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1959232.1, 265198.9, 1959568.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0104.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1959232.1, 265534.9, 1959568.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0105.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1959232.1, 265870.9, 1959568.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0106.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1958896.1, 259150.9, 1959232.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0107.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1958896.1, 259486.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0108.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1958896.1, 259822.9, 1959232.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0109.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1958896.1, 260158.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0110.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1958896.1, 260494.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0111.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1958896.1, 260830.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0112.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1958896.1, 261166.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0113.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1958896.1, 261502.9, 1959232.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0114.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1958896.1, 261838.9, 1959232.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0115.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1958896.1, 262174.9, 1959232.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0116.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1958896.1, 262510.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0117.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1958896.1, 262846.9, 1959232.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0118.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1958896.1, 263182.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0119.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1958896.1, 263518.9, 1959232.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0120.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1958896.1, 263854.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0121.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1958896.1, 264190.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0122.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1958896.1, 264526.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0123.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1958896.1, 264862.9, 1959232.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0124.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1958896.1, 265198.9, 1959232.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0125.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1958896.1, 265534.9, 1959232.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0126.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1958896.1, 265870.9, 1959232.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0127.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1958560.1, 259150.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0128.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1958560.1, 259486.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0129.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1958560.1, 259822.9, 1958896.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0130.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1958560.1, 260158.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0131.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1958560.1, 260494.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0132.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1958560.1, 260830.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0133.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1958560.1, 261166.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0134.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1958560.1, 261502.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0135.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1958560.1, 261838.9, 1958896.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0136.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1958560.1, 262174.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0137.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1958560.1, 262510.9, 1958896.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0138.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1958560.1, 262846.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0139.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1958560.1, 263182.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0140.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1958560.1, 263518.9, 1958896.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0141.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1958560.1, 263854.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0142.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1958560.1, 264190.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0143.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1958560.1, 264526.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0144.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1958560.1, 264862.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0145.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1958560.1, 265198.9, 1958896.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0146.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1958560.1, 265534.9, 1958896.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0147.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1958560.1, 265870.9, 1958896.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0148.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1958224.1, 259150.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0149.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1958224.1, 259486.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0150.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1958224.1, 259822.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0151.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1958224.1, 260158.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0152.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1958224.1, 260494.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0153.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1958224.1, 260830.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0154.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1958224.1, 261166.9, 1958560.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0155.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1958224.1, 261502.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0156.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1958224.1, 261838.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0157.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1958224.1, 262174.9, 1958560.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0158.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1958224.1, 262510.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0159.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1958224.1, 262846.9, 1958560.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0160.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1958224.1, 263182.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0161.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1958224.1, 263518.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0162.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1958224.1, 263854.9, 1958560.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0163.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1958224.1, 264190.9, 1958560.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0164.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1958224.1, 264526.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0165.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1958224.1, 264862.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0166.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1958224.1, 265198.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0167.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1958224.1, 265534.9, 1958560.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0168.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1958224.1, 265870.9, 1958560.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0169.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1957888.1, 259150.9, 1958224.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0170.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1957888.1, 259486.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0171.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1957888.1, 259822.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0172.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1957888.1, 260158.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0173.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1957888.1, 260494.9, 1958224.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0174.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1957888.1, 260830.9, 1958224.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0175.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1957888.1, 261166.9, 1958224.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0176.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1957888.1, 261502.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0177.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1957888.1, 261838.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0178.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1957888.1, 262174.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0179.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1957888.1, 262510.9, 1958224.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0180.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1957888.1, 262846.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0181.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1957888.1, 263182.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0182.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1957888.1, 263518.9, 1958224.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0183.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1957888.1, 263854.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0184.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1957888.1, 264190.9, 1958224.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0185.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1957888.1, 264526.9, 1958224.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0186.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1957888.1, 264862.9, 1958224.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0187.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1957888.1, 265198.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0188.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1957888.1, 265534.9, 1958224.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0189.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1957888.1, 265870.9, 1958224.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0190.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1957552.1, 259150.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0191.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1957552.1, 259486.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0192.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1957552.1, 259822.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0193.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1957552.1, 260158.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0194.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1957552.1, 260494.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0195.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1957552.1, 260830.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0196.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1957552.1, 261166.9, 1957888.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0197.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1957552.1, 261502.9, 1957888.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0198.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1957552.1, 261838.9, 1957888.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0199.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1957552.1, 262174.9, 1957888.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0200.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1957552.1, 262510.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0201.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1957552.1, 262846.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0202.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1957552.1, 263182.9, 1957888.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0203.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1957552.1, 263518.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0204.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1957552.1, 263854.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0205.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1957552.1, 264190.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0206.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1957552.1, 264526.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0207.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1957552.1, 264862.9, 1957888.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0208.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1957552.1, 265198.9, 1957888.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0209.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1957552.1, 265534.9, 1957888.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0210.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1957552.1, 265870.9, 1957888.1) | 0.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0211.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1957216.1, 259150.9, 1957552.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0212.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1957216.1, 259486.9, 1957552.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0213.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1957216.1, 259822.9, 1957552.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0214.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1957216.1, 260158.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0215.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1957216.1, 260494.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0216.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1957216.1, 260830.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0217.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1957216.1, 261166.9, 1957552.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0218.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1957216.1, 261502.9, 1957552.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0219.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1957216.1, 261838.9, 1957552.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0220.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1957216.1, 262174.9, 1957552.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0221.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1957216.1, 262510.9, 1957552.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0222.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1957216.1, 262846.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0223.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1957216.1, 263182.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0224.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1957216.1, 263518.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0225.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1957216.1, 263854.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0226.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1957216.1, 264190.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0227.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1957216.1, 264526.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0228.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1957216.1, 264862.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0229.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1957216.1, 265198.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0230.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1957216.1, 265534.9, 1957552.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0231.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1957216.1, 265870.9, 1957552.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0232.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1956880.1, 259150.9, 1957216.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0233.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1956880.1, 259486.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0234.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1956880.1, 259822.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0235.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1956880.1, 260158.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0236.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1956880.1, 260494.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0237.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1956880.1, 260830.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0238.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1956880.1, 261166.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0239.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1956880.1, 261502.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0240.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1956880.1, 261838.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0241.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1956880.1, 262174.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0242.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1956880.1, 262510.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0243.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1956880.1, 262846.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0244.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1956880.1, 263182.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0245.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1956880.1, 263518.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0246.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1956880.1, 263854.9, 1957216.1) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0247.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1956880.1, 264190.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0248.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1956880.1, 264526.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0249.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1956880.1, 264862.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0250.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1956880.1, 265198.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0251.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1956880.1, 265534.9, 1957216.1) | 0.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0252.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1956880.1, 265870.9, 1957216.1) | 0.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0253.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1956544.1, 259150.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0254.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259150.9, 1956544.1, 259486.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0255.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259486.9, 1956544.1, 259822.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0256.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(259822.9, 1956544.1, 260158.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0257.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260158.9, 1956544.1, 260494.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0258.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260494.9, 1956544.1, 260830.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0259.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260830.9, 1956544.1, 261166.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0260.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261166.9, 1956544.1, 261502.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0261.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261502.9, 1956544.1, 261838.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0262.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261838.9, 1956544.1, 262174.9, 1956880.1) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0263.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1956544.1, 262510.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0264.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262510.9, 1956544.1, 262846.9, 1956880.1) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0265.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262846.9, 1956544.1, 263182.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0266.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263182.9, 1956544.1, 263518.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0267.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263518.9, 1956544.1, 263854.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0268.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(263854.9, 1956544.1, 264190.9, 1956880.1) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0269.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264190.9, 1956544.1, 264526.9, 1956880.1) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0270.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264526.9, 1956544.1, 264862.9, 1956880.1) | 0.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0271.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(264862.9, 1956544.1, 265198.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0272.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265198.9, 1956544.1, 265534.9, 1956880.1) | 0.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_model_input_tiles\tile_0273.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1956544.1, 265870.9, 1956880.1) | 0.2 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_test_masks\tile_0001_mask.tif | 560x560 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1960576.1, 259150.9, 1960912.1) | 0.0 MB | values={1: 4225, 3: 3827, 7: 305548}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_test_masks\tile_0137_mask.tif | 560x560 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262174.9, 1958560.1, 262510.9, 1958896.1) | 0.0 MB | values={1: 63096, 5: 214773, 6: 35606, 7: 125}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\esri_test_masks\tile_0273_mask.tif | 560x560 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(265534.9, 1956544.1, 265870.9, 1956880.1) | 0.0 MB | values={1: 58712, 3: 141, 5: 482, 6: 8603, 7: 245662}
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_000.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_001.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1959735.5, 262521.3, 1960912.1) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_002.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1959735.5, 264374.5, 1960912.1) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_003.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1959735.5, 266227.7, 1960912.1) | 0.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_004.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1958559.0, 260668.1, 1959735.5) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_005.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1958559.0, 262521.3, 1959735.5) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_006.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1958559.0, 264374.5, 1959735.5) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_007.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1958559.0, 266227.7, 1959735.5) | 0.5 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_008.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1957382.5, 260668.1, 1958559.0) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_009.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1957382.5, 262521.3, 1958559.0) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_010.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1957382.5, 264374.5, 1958559.0) | 0.6 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_011.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1957382.5, 266227.7, 1958559.0) | 0.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_012.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1956205.9, 260668.1, 1957382.5) | 0.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_013.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1956205.9, 262521.3, 1957382.5) | 0.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_014.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1956205.9, 264374.5, 1957382.5) | 0.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\input_tiles\tile_015.tif | 560x560 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1956205.9, 266227.7, 1957382.5) | 0.3 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\residential_diagnostic_mask.tif | 560x560 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261518.5, 1958785.1, 261854.5, 1959121.1) | 0.0 MB | values={1: 270529, 2: 15074, 5: 27709, 7: 288}
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\residential_diagnostic_tile.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261518.5, 1958785.1, 261854.5, 1959121.1) | 1.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\school_diagnostic_masks\mpps_school_tile_mask.tif | 560x560 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261252.1, 1959057.5, 261588.1, 1959393.5) | 0.0 MB | values={1: 232660, 2: 60475, 3: 540, 5: 19925}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\school_diagnostic_masks\zphs_school_tile_mask.tif | 560x560 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261249.1, 1959090.5, 261585.1, 1959426.5) | 0.0 MB | values={1: 249607, 2: 46985, 5: 16983, 7: 25}
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\school_diagnostic_tiles\mpps_school_tile.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261252.1, 1959057.5, 261588.1, 1959393.5) | 1.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\school_diagnostic_tiles\zphs_school_tile.tif | 560x560 | bands=3 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261249.1, 1959090.5, 261585.1, 1959426.5) | 1.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_000.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_001.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1959735.5, 262521.3, 1960912.1) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_002.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1959735.5, 264374.5, 1960912.1) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_003.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1959735.5, 266227.7, 1960912.1) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_004.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1958559.0, 260668.1, 1959735.5) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_005.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1958559.0, 262521.3, 1959735.5) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_006.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1958559.0, 264374.5, 1959735.5) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_007.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1958559.0, 266227.7, 1959735.5) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_008.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1957382.5, 260668.1, 1958559.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_009.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1957382.5, 262521.3, 1958559.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_010.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1957382.5, 264374.5, 1958559.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_011.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1957382.5, 266227.7, 1958559.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_012.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1956205.9, 260668.1, 1957382.5) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_013.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(260668.1, 1956205.9, 262521.3, 1957382.5) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_014.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(262521.3, 1956205.9, 264374.5, 1957382.5) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\segmentation_masks\tile_015.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(264374.5, 1956205.9, 266227.7, 1957382.5) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\sentinel2_input_tiles\tile_000.tif | 560x560 | bands=3 uint8 | res=10.000 | crs=EPSG:32643 | bounds=(895310.0, 1957880.0, 900910.0, 1963480.0) | 0.3 MB | tags={'source': 'Copernicus Sentinel-2 L2A'}
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\sentinel2_input_tiles\tile_001.tif | 560x560 | bands=3 uint8 | res=10.000 | crs=EPSG:32643 | bounds=(900910.0, 1957880.0, 906510.0, 1963480.0) | 0.0 MB | tags={'source': 'Copernicus Sentinel-2 L2A'}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\sentinel2_segmentation_masks\tile_000_mask.tif | 560x560 | bands=1 uint8 | res=10.000 | crs=EPSG:32643 | bounds=(895310.0, 1957880.0, 900910.0, 1963480.0) | 0.0 MB | tags={'source': 'Sentinel-2 L2A'} | values={1: 235248, 4: 138, 6: 57252, 7: 20962}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\sentinel2_segmentation_masks\tile_001_mask.tif | 560x560 | bands=1 uint8 | res=10.000 | crs=EPSG:32643 | bounds=(900910.0, 1957880.0, 906510.0, 1963480.0) | 0.0 MB | tags={'source': 'Sentinel-2 L2A'} | values={1: 59308, 4: 13678, 5: 2161, 6: 16907, 7: 221546}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\tiled_v1\building_prob_full.tif | 11296x7171 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1956609.5, 265592.5, 1960912.1) | 4.0 MB | values={0: 307020, 1: 963364, 2: 538209, 3: 214449, 4: 86488, 5: 44359, 6: 25489, 7: 13816, 8: 8486, 9: 5966, 10: 4182, 11: 3124}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\tiled_v1\building_prob_smoke.tif | 1400x1400 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261814.9, 1958272.1, 262654.9, 1959112.1) | 0.1 MB | values={0: 772262, 1: 624568, 2: 417797, 3: 112403, 4: 22711, 5: 4679, 6: 808, 7: 383, 8: 220, 9: 177, 10: 166, 11: 144}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\tiled_v1\pred_classes_full.tif | 11296x7171 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1956609.5, 265592.5, 1960912.1) | 1.4 MB | values={1: 865853, 2: 7502, 3: 1148, 4: 17266, 5: 872991, 6: 52933, 7: 432307}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\predictions\tiled_v1\pred_classes_smoke.tif | 1400x1400 | bands=1 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261814.9, 1958272.1, 262654.9, 1959112.1) | 0.0 MB | values={1: 1010677, 2: 1363, 3: 3388, 4: 5204, 5: 292916, 6: 194171, 7: 452281}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\dem\damarakunta_dem_clip.tif | 232x141 | bands=1 int16 | res=0.000 | crs=EPSG:4326 | bounds=(78.7, 17.7, 78.8, 17.7) | 0.0 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\damarakunta_sentinel_feb2022.tif | 2048x2048 | bands=3 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1956609.3, 265592.3, 1960912.1) | 7.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_damarakunta_test_1km_georef.tif | 1667x1667 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(261703.6, 1958260.7, 262703.6, 1959260.7) | 7.2 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_01.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1956609.3, 260614.9, 1958409.3) | 30.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_02.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260614.9, 1956609.3, 262414.9, 1958409.3) | 30.5 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_03.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262414.9, 1956609.3, 264214.9, 1958409.3) | 30.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_04.tif | 3000x3000 | bands=4 uint8 | res=0.459 | crs=EPSG:32644 | bounds=(264214.9, 1956609.3, 265592.3, 1958409.3) | 29.8 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_05.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1958409.3, 260614.9, 1960209.3) | 30.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_06.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260614.9, 1958409.3, 262414.9, 1960209.3) | 29.7 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_07.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262414.9, 1958409.3, 264214.9, 1960209.3) | 30.3 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_08.tif | 3000x3000 | bands=4 uint8 | res=0.459 | crs=EPSG:32644 | bounds=(264214.9, 1958409.3, 265592.3, 1960209.3) | 30.1 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_09.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(258814.9, 1960209.3, 260614.9, 1960912.1) | 29.4 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_10.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(260614.9, 1960209.3, 262414.9, 1960912.1) | 29.9 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\esri_full_tiles\damarakunta_esri_tile_11.tif | 3000x3000 | bands=4 uint8 | res=0.600 | crs=EPSG:32644 | bounds=(262414.9, 1960209.3, 264214.9, 1960912.1) | 29.2 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_B02.tif | 10980x10980 | bands=1 uint16 | res=10.000 | crs=EPSG:32643 | bounds=(799980.0, 1890240.0, 909780.0, 2000040.0) | 277.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_B02_clipped_10m.tif | 682x436 | bands=1 uint16 | res=10.000 | crs=EPSG:32643 | bounds=(895310.0, 1959120.0, 902130.0, 1963480.0) | 0.3 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_B03.tif | 10980x10980 | bands=1 uint16 | res=10.000 | crs=EPSG:32643 | bounds=(799980.0, 1890240.0, 909780.0, 2000040.0) | 278.6 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_B03_clipped_10m.tif | 682x436 | bands=1 uint16 | res=10.000 | crs=EPSG:32643 | bounds=(895310.0, 1959120.0, 902130.0, 1963480.0) | 0.3 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_B04.tif | 10980x10980 | bands=1 uint16 | res=10.000 | crs=EPSG:32643 | bounds=(799980.0, 1890240.0, 909780.0, 2000040.0) | 284.1 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_B04_clipped_10m.tif | 682x436 | bands=1 uint16 | res=10.000 | crs=EPSG:32643 | bounds=(895310.0, 1959120.0, 902130.0, 1963480.0) | 0.3 MB
- IMAGERY D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\imagery\sentinel2_20260429\damarakunta_sentinel2_RGB_B04_B03_B02_10m.tif | 682x436 | bands=3 uint16 | res=10.000 | crs=EPSG:32643 | bounds=(895310.0, 1959120.0, 902130.0, 1963480.0) | 0.8 MB | tags={'acquisition_date': '2026-04-29', 'source': 'Copernicus Sentinel-2 L2A'}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\raw\landcover\damarakunta_worldcover_clip.tif | 768x468 | bands=1 uint8 | res=0.000 | crs=EPSG:4326 | bounds=(78.7, 17.7, 78.8, 17.7) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\ALL_OUTPUT_IMAGES\channel_order_model_test\prediction_123.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313531, 6: 55, 7: 14}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\ALL_OUTPUT_IMAGES\channel_order_model_test\prediction_132.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313600}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\ALL_OUTPUT_IMAGES\channel_order_model_test\prediction_213.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 310980, 7: 2620}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\ALL_OUTPUT_IMAGES\channel_order_model_test\prediction_231.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313598, 7: 2}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\ALL_OUTPUT_IMAGES\channel_order_model_test\prediction_312.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313440, 4: 94, 6: 62, 7: 4}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\ALL_OUTPUT_IMAGES\channel_order_model_test\prediction_321.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313579, 6: 21}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\channel_order_model_test\prediction_123.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313531, 6: 55, 7: 14}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\channel_order_model_test\prediction_132.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313600}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\channel_order_model_test\prediction_213.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 310980, 7: 2620}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\channel_order_model_test\prediction_231.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313598, 7: 2}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\channel_order_model_test\prediction_312.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313440, 4: 94, 6: 62, 7: 4}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\channel_order_model_test\prediction_321.tif | 560x560 | bands=1 uint8 | res=3.309 | crs=EPSG:32644 | bounds=(258814.9, 1959735.5, 260668.1, 1960912.1) | 0.0 MB | values={1: 313579, 6: 21}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\routes_burnin\damarakunta_worldcover_10m_buildings.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB | values={0: 108859, 10: 6763, 20: 6430, 30: 65887, 40: 99138, 50: 2170, 60: 3857, 80: 224}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\routes_centeronly\damarakunta_worldcover_10m_buildings.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB | values={0: 108860, 10: 6774, 20: 6430, 30: 66104, 40: 99313, 50: 1678, 60: 3945, 80: 224}
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\anytouch_min10\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\dilate2m\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s1\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s2\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s3\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s4\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop10_s5\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s1\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s2\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s3\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s4\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop20_s5\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s1\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s2\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s3\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s4\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\drop30_s5\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\min100\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\min25\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\min50\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep\ref_center_min10\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\anytouch_min10\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\dilate2m\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s1\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s2\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s3\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s4\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop10_s5\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s1\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s2\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s3\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s4\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop20_s5\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s1\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s2\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s3\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s4\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\drop30_s5\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\min100\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\min25\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\min50\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB
- single-band D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\sweep_c1sweep_v1\ref_center_min10\wc.tif | 679x432 | bands=1 uint8 | res=10.000 | crs=EPSG:32644 | bounds=(258810.0, 1956600.0, 265600.0, 1960920.0) | 0.0 MB

## 4. Licence / provenance / metadata documents near imagery
(If nothing is listed above, no licence/terms file for the imagery exists in the project.)

## 5. Scripts that look related to inference / building extraction
- scripts\assess_building_access.py (7061 bytes)
    """Proximity-based access screening: candidate buildings / clusters / facilities vs TGRAC reference roads.
    CAND = os.path.join(ROOT, "results", "v6_buildings", "candidate_buildings_full.gpkg")
    OUT_DIR = os.path.join(ROOT, "results", "v6_buildings", "access")
    near_candidate_building=bool(dc[i] <= a.fac_near_m),
- scripts\assess_building_access_v2.py (8838 bytes)
    """v2 (parameterised copy of assess_building_access.py; the original is untouched).
    Proximity-based access screening: candidate buildings / clusters / facilities vs TGRAC reference roads.
    ap.add_argument("--cands", default=os.path.join(ROOT, "results", "v8_instances", "buildings_v8_full.gpkg"))
    ap.add_argument("--cands-layer", default="buildings")
    help="v8 quality classes kept as targets; UNRESOLVED_MERGE = built-up extent, not one building")
    near_candidate_building=bool(dc[i] <= a.fac_near_m),
- scripts\audit_road_connectivity.py (106992 bytes)
    overpasses, road width, building truth, or any monetary cost. A geometric touch or an endpoint within a tolerance is not proof of a
    CAND_OPTIONAL = ["building_id", "instance_id", "area_m2", "inside_village", "nearest_m", "neck_ratio"]
    ("area_m2", "Polygon area stored by the extraction step (extract_buildings_v8), rounded to 0.01. Pass-through, not recomputed.", "m2", "per polygon"),
- scripts\audit_road_connectivity_new.py (106992 bytes)
    overpasses, road width, building truth, or any monetary cost. A geometric touch or an endpoint within a tolerance is not proof of a
    CAND_OPTIONAL = ["building_id", "instance_id", "area_m2", "inside_village", "nearest_m", "neck_ratio"]
    ("area_m2", "Polygon area stored by the extraction step (extract_buildings_v8), rounded to 0.01. Pass-through, not recomputed.", "m2", "per polygon"),
- scripts\calculate_school_overlap.py (2298 bytes)
    BUILDING_CLASS_ID = 2
    building_pixels = int(
    ((prediction == BUILDING_CLASS_ID) & compound_mask).sum()
    building_pixels / reference_pixels * 100
    print("Pixels predicted as Building inside polygon:", building_pixels)
    print("Reference-polygon coverage by Building predictions:",
- scripts\check_class_mapping.py (5349 bytes)
    "site-packages", "node_modules", "checkpoints"
    r"pred_classes|building_prob",
    r"argmax|softmax|building_prob|pred_classes",
    "If building_prob uses softmax(logits)[:, 2], it refers to "
    "output channel 2. That is Building only if training targets "
    "used ID 2 for Building."
    "loader's target conversion before treating any predicted ID as Building."
- scripts\check_school_class_distribution.py (903 bytes)
    2: "Building",
- scripts\create_damarakunta_esri_visual_diagnostic.py (4953 bytes)
    2: "Building",
- scripts\create_damarakunta_sentinel2_visual_diagnostic.py (11601 bytes)
    2: "Building",
    2: (255, 0, 0),        # Building
    # BUILDING / ROAD CHECK
    building_pixels = total_counts.get(
    building_percentage = (
    building_pixels
    print("\nBUILDING / ROAD CHECK")
    f"Building prediction: "
- scripts\create_damarakunta_visual_diagnostic.py (3919 bytes)
    2: "Building",
    # Building
- scripts\create_phase13_diagnostic.py (1943 bytes)
    building_mask = BASE / "derived" / "building_mask.png"
    buildings = Image.open(building_mask).convert("L")
    buildings = buildings.resize(size, Image.Resampling.NEAREST)
    building_rgb = Image.merge("RGB", (buildings, buildings, buildings))
    building_rgb = add_label(building_rgb, "PREDICTED BUILDING MASK")
    combined.paste(building_rgb, (size[0], 0))
- scripts\create_residential_visual_diagnostic.py (2929 bytes)
    # 0 Ignore, 1 Background, 2 Building, 3 Road,
    2: (255, 0, 0),      # Building — red
    2: "Building",
    # Overlay Building and Road predictions on the original imagery.
    "Building red | Road blue",
- scripts\diagnose_damarakunta_model.py (6398 bytes)
    CHECKPOINT = os.path.join(
    "checkpoints",
    "best_model.pth"
    2: "Building",
    print("Checkpoint:", CHECKPOINT)
    print("Exists:", os.path.isfile(CHECKPOINT))
    if not os.path.isfile(CHECKPOINT):
    raise SystemExit("[ERROR] Checkpoint not found.")
- scripts\evaluate_layer_vs_reference.py (4258 bytes)
    Usage: python scripts\\evaluate_layer_vs_reference.py --cands <gpkg> [--layer buildings] [--name v7]"""
    ap.add_argument("--ref", default=r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\v6_buildings\reference\digitize_windows.gpkg")
    ref = gpd.read_file(REF, layer="reference_buildings").to_crs(CRS)
- scripts\extract_buildings_roads.py (16074 bytes)
    BUILDING_GPKG = OUTPUT_DIR / "buildings.gpkg"
    BUILDING_CSV = OUTPUT_DIR / "buildings.csv"
    BUILDING_PREVIEW = OUTPUT_DIR / "building_mask.png"
    BUILDING_CLASS = 1
    # BUILDING EXTRACTION SETTINGS
    MIN_BUILDING_PIXELS = 20
    # BUILDING EXTRACTION
    def extract_buildings(prediction, transform, crs):
- scripts\extract_buildings_v7.py (18078 bytes)
    Inputs (read-only):  pred_classes_<tag>.tif  (class IDs, 2 = Building)
    building_prob_<tag>.tif (building probability scaled 0-255)
    Output (new folder): buildings_v7_<tag>.gpkg  layers: buildings (instances), components (v6-style blobs)
    buildings_v7_<tag>.csv, summary_v7_<tag>.json, overlays/*.png
    * The checkpoint is a SEMANTIC segmentation model (one class per pixel). It has no per-roof (instance) output.
    * Step 1 keeps pixels the model calls Building (or prob >= --prob-thr) and labels connected regions
    Every polygon is an UNVERIFIED model prediction, not a surveyed building or a house count.
    ap.add_argument("--windows-gpkg", default=os.path.join(ROOT, "results", "v6_buildings", "reference",
- scripts\extract_buildings_v8.py (24134 bytes)
    Writes only to a NEW folder (results\\v8_instances). Does not touch v6/v7 outputs, rasters, checkpoint or references.
    extent, not as individual buildings. The reference roof size is the median of compact single polygons
    LIMITS (read this): the checkpoint is a semantic model. The mask boundary is coarse, so footprints are blob
    ap.add_argument("--windows-gpkg", default=os.path.join(ROOT, "results", "v6_buildings", "reference", "digitize_windows.gpkg"))
    ap.add_argument("--v6", default=os.path.join(ROOT, "results", "v6_buildings", "candidate_buildings_full.gpkg"))
    ap.add_argument("--v7", default=os.path.join(ROOT, "results", "v7_instances", "buildings_v7_full.gpkg"))
    ap.add_argument("--out-name", default=None, help="file stem; default buildings_v8_<tag>")
    stem = a.out_name or f"buildings_v8_{a.tag}"
- scripts\extract_candidate_buildings.py (3810 bytes)
    """Class-2 raster -> candidate building polygons (EPSG:32644). Unvalidated."""
    OUT_DIR = os.path.join(ROOT, "results", "v6_buildings")
    ap.add_argument("--min-prob", type=float, default=0.0, help="min mean building prob (0-1)")
    out_gpkg = os.path.join(OUT_DIR, f"candidate_buildings_{a.tag}.gpkg")
    with rasterio.open(os.path.join(PRED, f"building_prob_{a.tag}.tif")) as s:
    gdf.to_file(out_gpkg, layer="candidate_buildings", driver="GPKG")
    print("Wrote:", out_gpkg, "| layer: candidate_buildings | CRS:", gdf.crs)
- scripts\generate_damarakunta_routes_v4_review_map.py (32201 bytes)
    # BUILDING + HOUSE + ROAD CONNECTIVITY REVIEW
    # This script visualizes existing building footprints.
    # from satellite pixels when no building layer is available.
    # Optional: enter the exact path of your building-footprint file.
    # BUILDINGS_SOURCE = BASE / "reference" / "village_buildings.gpkg"
    # Leave as None to search for an existing building layer.
    BUILDINGS_SOURCE = None
    BUILDINGS_LAYER = None
- scripts\generate_damarakunta_v5_building_review.py (32201 bytes)
    # BUILDING + HOUSE + ROAD CONNECTIVITY REVIEW
    # This script visualizes existing building footprints.
    # from satellite pixels when no building layer is available.
    # Optional: enter the exact path of your building-footprint file.
    # BUILDINGS_SOURCE = BASE / "reference" / "village_buildings.gpkg"
    # Leave as None to search for an existing building layer.
    BUILDINGS_SOURCE = None
    BUILDINGS_LAYER = None
- scripts\generate_presentation_maps.py (19371 bytes)
    return "Context imagery only (%.0f m pixels; too coarse for individual buildings/narrow roads). " % info["res_m"] + base
    if L.get("candidates") is not None: clip(L["candidates"], ext).plot(ax=ax, facecolor=C["build"], edgecolor="white", alpha=0.55, lw=0.4, zorder=7); h.a
    log("SKIP Figure 2: building polygons (audit 'candidates' layer or model extraction GPKG) not found.")
    fig, ax = canvas(e2, bg2, "Building Extraction and Road Network – Main Settlement" + tag, attrib2)
    legend(ax, [Patch(fc=C["build"], ec="white", alpha=0.6, label="Model-derived building polygons (unverified)"), Line2D([], [], color=C["road"], lw=2.5,
    save(fig, a.out, "02_building_extraction_road_network")
    for kind, mk, col, lab in (("FACILITY", "*", C["fac"], "Facility targets"), ("CLUSTER", "o", "white", "Building-cluster targets")):
    if "candidates" in L: clip(L["candidates"], ext).plot(ax=ax, facecolor=C["build"], edgecolor="white", alpha=0.45, lw=0.3, zorder=5); h.append(Patch(fc
- scripts\generate_presentation_maps_backup.py (19371 bytes)
    return "Context imagery only (%.0f m pixels; too coarse for individual buildings/narrow roads). " % info["res_m"] + base
    if L.get("candidates") is not None: clip(L["candidates"], ext).plot(ax=ax, facecolor=C["build"], edgecolor="white", alpha=0.55, lw=0.4, zorder=7); h.a
    log("SKIP Figure 2: building polygons (audit 'candidates' layer or model extraction GPKG) not found.")
    fig, ax = canvas(e2, bg2, "Building Extraction and Road Network – Main Settlement" + tag, attrib2)
    legend(ax, [Patch(fc=C["build"], ec="white", alpha=0.6, label="Model-derived building polygons (unverified)"), Line2D([], [], color=C["road"], lw=2.5,
    save(fig, a.out, "02_building_extraction_road_network")
    for kind, mk, col, lab in (("FACILITY", "*", C["fac"], "Facility targets"), ("CLUSTER", "o", "white", "Building-cluster targets")):
    if "candidates" in L: clip(L["candidates"], ext).plot(ax=ax, facecolor=C["build"], edgecolor="white", alpha=0.45, lw=0.3, zorder=5); h.append(Patch(fc
- scripts\inspect_building_pipeline.py (7558 bytes)
    """READ-ONLY inspection of model weights, building outputs and imagery for a village.
    .venv\\Scripts\\python.exe scripts\\inspect_building_pipeline.py --village Siddipet\\Damarakunta
    p("\n## 1. Model weights / checkpoints")
    ws = [f for f in files if f.lower().endswith((".pt", ".pth", ".ckpt", ".safetensors", ".bin")) and os.path.getsize(f) > 1e6]
    if not ws: p("NONE FOUND (.pt/.pth/.ckpt/.safetensors > 1 MB)"); return
    if torch and f.lower().endswith((".pt", ".pth", ".ckpt")):
    p("\n## 2. Building / candidate vector outputs")
    p("\n## 5. Scripts that look related to inference / building extraction")
- scripts\inspect_school_building_components.py (1222 bytes)
    building = mask == 2
    building,
    print("Building pixels:", int(building.sum()))
    print("Building pixel area (m2):",
    round(int(building.sum()) * pixel_area, 2))
    print("Connected building-like regions:", int(count))
- scripts\make_digitizing_windows.py (3612 bytes)
    """Create sampling windows + an empty reference layer for manual building digitizing (QGIS).
    ACC = ROOT / "results" / "v6_buildings" / "access" / "access_assessment.gpkg"
    OUT_DIR = ROOT / "results" / "v6_buildings" / "reference"
    sys.exit(f"{OUT} exists; will not overwrite (it may hold your traced buildings)")
    chosen.append((f"W{len(chosen)+1}_FARMNEG", "farmland, no predicted buildings", b))
    with fiona.open(OUT, "w", driver="GPKG", layer="reference_buildings", crs=CRS, schema=schema):
    print("\nWrote:", OUT, "| layers: windows, reference_buildings (empty)")
- scripts\phase0_audit.py (21623 bytes)
    loads the checkpoint on CPU, and (optionally) builds the model once to test
    checkpoint compatibility.
    (no images, no checkpoint) for review
    --no-model-load   skip building StrongDINOv2Seg (skips the HuggingFace download)
    CHECKPOINT = SEG_ROOT / "checkpoints" / "best_model.pth"
    "class_ids_or_names": r"(?i)(num_classes|class_names|classes\s*=|building|road)\s*[:=]",
    def checkpoint_summary(path: Path):
    def status_block(checkpoint, build, scan, data):
- scripts\phase25_master_status_report.py (10801 bytes)
    ("PHASE 13", "Building / Road Extraction", "COMPLETED"),
    "5. Already well-connected buildings/areas generally "
- scripts\phase25_village_expansion_checklist.py (10817 bytes)
    "requirement": "Building and road extraction",
    "7. Already well-connected buildings/areas generally "
- scripts\plan_gap_routes.py (15819 bytes)
    """Two-stage generate-and-select prototype for gap-building clusters + priority facilities.
    Stage A: existing V4 search (imported, unmodified) on WorldCover with candidate buildings burned in.
    CAND = ROOT / "results" / "v6_buildings" / "candidate_buildings_full.gpkg"
    out_dir = ROOT / "results" / "v6_buildings" / f"plan_{a.tag}"
    print(f"candidate buildings touched by straight-line baseline connectors (excluding own cluster): {bl_cross}")
    print("selected routes crossing other candidate buildings (credit plan):",
    f"reference gap buildings {len(ref_gap)}, within {SERVE:.0f} m of plan: {ref_served}")
    print(f"\n(reference gap buildings served by reference plan: {ref_served} of {len(ref_gap)})")
- scripts\plan_network_v2.py (47435 bytes)
    SOFT constraints (cost multipliers, parameters not facts): WorldCover built-up multiplier, building-polygon multiplier
    cluster_buildings_served=sum(t.get("n_buildings", 0) for t in ts if t["kind"] == "CLUSTER"),
    ap.add_argument("--buildings", default=d("results", "v8_instances", "buildings_v8_full.gpkg"))
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--building-mult", type=float, default=4.0, help="soft multiplier on cells whose CENTRE lies in a building polygon (1 = off)")
    ap.add_argument("--building-quality", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--cluster-weight-per-building", type=float, default=0.25)
    if a.buildings and os.path.exists(a.buildings) and a.building_mult != 1.0:
- scripts\plan_network_v2_before_experiments_backup.py (47435 bytes)
    SOFT constraints (cost multipliers, parameters not facts): WorldCover built-up multiplier, building-polygon multiplier
    cluster_buildings_served=sum(t.get("n_buildings", 0) for t in ts if t["kind"] == "CLUSTER"),
    ap.add_argument("--buildings", default=d("results", "v8_instances", "buildings_v8_full.gpkg"))
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--building-mult", type=float, default=4.0, help="soft multiplier on cells whose CENTRE lies in a building polygon (1 = off)")
    ap.add_argument("--building-quality", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--cluster-weight-per-building", type=float, default=0.25)
    if a.buildings and os.path.exists(a.buildings) and a.building_mult != 1.0:
- scripts\plan_network_v2_before_slopefix_backup.py (40559 bytes)
    SOFT constraints (cost multipliers, parameters not facts): WorldCover built-up multiplier, building-polygon multiplier
    cluster_buildings_served=sum(t.get("n_buildings", 0) for t in ts if t["kind"] == "CLUSTER"),
    ap.add_argument("--buildings", default=d("results", "v8_instances", "buildings_v8_full.gpkg"))
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--building-mult", type=float, default=4.0, help="soft multiplier on cells whose CENTRE lies in a building polygon (1 = off)")
    ap.add_argument("--building-quality", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--cluster-weight-per-building", type=float, default=0.25)
    if a.buildings and os.path.exists(a.buildings) and a.building_mult != 1.0:
- scripts\plan_network_v2_run1_backup.py (40559 bytes)
    SOFT constraints (cost multipliers, parameters not facts): WorldCover built-up multiplier, building-polygon multiplier
    cluster_buildings_served=sum(t.get("n_buildings", 0) for t in ts if t["kind"] == "CLUSTER"),
    ap.add_argument("--buildings", default=d("results", "v8_instances", "buildings_v8_full.gpkg"))
    ap.add_argument("--buildings-layer", default="buildings")
    ap.add_argument("--building-mult", type=float, default=4.0, help="soft multiplier on cells whose CENTRE lies in a building polygon (1 = off)")
    ap.add_argument("--building-quality", default="PLAUSIBLE,REVIEW,UNRESOLVED_MERGE")
    ap.add_argument("--cluster-weight-per-building", type=float, default=0.25)
    if a.buildings and os.path.exists(a.buildings) and a.building_mult != 1.0:
- scripts\plot_connectivity_audit.py (3019 bytes)
    "02_building_road_connectivity.png",
    "Candidate Buildings and Mapped Road Connectivity",
- scripts\rerun_v4_with_buildings.py (5263 bytes)
    """Re-run the EXISTING V4 route generator with candidate buildings burned into a COPY of WorldCover
    Candidate buildings are UNVERIFIED model predictions; routes are unverified planning alternatives."""
    CAND = ROOT / "results" / "v6_buildings" / "candidate_buildings_full.gpkg"
    out_dir = ROOT / "results" / "v6_buildings" / f"routes_{a.tag}"
    new_wc = out_dir / "damarakunta_worldcover_10m_buildings.tif"
    print("\n===== running existing V4 main() on building-burned WorldCover =====")
    tn = table(new, "NEW routes (buildings burned in)")
- scripts\run_damarakunta_inference.py (10204 bytes)
    CHECKPOINT = os.path.join(
    "checkpoints",
    "best_model.pth"
    2: "Building",
    print("Checkpoint:", CHECKPOINT)
    print("Checkpoint exists:", os.path.isfile(CHECKPOINT))
    if not os.path.isfile(CHECKPOINT):
    print("\n[ERROR] Checkpoint not found.")
- scripts\run_damarakunta_sentinel2_inference.py (10158 bytes)
    CHECKPOINT = os.path.join(
    r"checkpoints\best_model.pth"
    "Building",
    print("\nCheckpoint:")
    print(CHECKPOINT)
    if not os.path.exists(CHECKPOINT):
    f"Checkpoint not found:\n{CHECKPOINT}"
    # LOAD CHECKPOINT
- scripts\run_planning_experiments.py (24526 bytes)
    """run_planning_experiments.py - C1 (building-input perturbation) and C2 (attachment / shared-credit) experiments.
    Nothing here measures segmentation accuracy. C1 perturbations are SYNTHETIC controlled changes to the model-predicted building
    polygons; they show how SENSITIVE the road plan is to building-input errors, not how wrong the real segmentation is.
    Evaluation set (fixed): the buildings of the baseline gap clusters + the baseline facilities. With few seeds results are
    """Same logic as assess_building_access_v2.build() (re-implemented so perturbed buildings can be re-clustered)."""
    def building_mult(ctx, polys):
    if ctx.a.building_mult == 1.0 or polys is None or len(polys) == 0:
    m = ctx.W["mult_base"].copy(); m[bm] *= ctx.a.building_mult
- scripts\run_rural_planning_pipeline.py (16473 bytes)
    python scripts\\run_rural_planning_pipeline.py --config ... --force extract_buildings_v8      rerun one stage (and later ones)
    "They are NOT land cover; extraction rejects building blobs on them." if blank > 0.001 else "no blank area")
    pc, pb = P.get("pred_classes"), P.get("building_prob")
    add("OK" if s.dtypes[0] == "uint8" else "WARN", "pred.prob", f"building_prob dtype {s.dtypes[0]} (expected uint8 0-255 = softmax channel {cfg.get('bui
    "Outputs are UNVERIFIED model-derived candidates (not surveyed buildings, not construction-ready roads).", "",
- scripts\run_tiled_inference.py (6161 bytes)
    CHECKPOINT = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
    p_bp = os.path.join(OUT_DIR, f"building_prob_{tag}.tif")
    ck = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)
    sys.exit("Missing model keys: checkpoint mismatch")
    log = dict(raster=RASTER, checkpoint=CHECKPOINT, window=[int(win.col_off), int(win.row_off), w, h],
- scripts\run_village_segmentation.py (14332 bytes)
    CHECKPOINT = (
    / "checkpoints"
    / "best_model.pth"
    1: "Building",
    print("Checkpoint      :", CHECKPOINT)
    if not CHECKPOINT.exists():
    f"Checkpoint not found: {CHECKPOINT}"
    checkpoint = torch.load(
- scripts\save_damarakunta_residential_mask.py (4670 bytes)
    r"\checkpoints\best_model.pth"
    print("ERROR: Model checkpoint not found:")
    checkpoint = torch.load(
    checkpoint["state_dict"],
    "Checkpoint epoch:",
    checkpoint.get("epoch")
    checkpoint.get("mIoU")
    checkpoint.get("mDice")
- scripts\score_routes_with_buildings.py (5942 bytes)
    """Read-only scoring of V4 route alternatives vs candidate buildings, with shared-edge accounting.
    No weights applied. Candidate buildings are UNVERIFIED predictions; routes are unverified alternatives."""
    ACC = os.path.join(ROOT, "results", "v6_buildings", "access", "access_assessment.gpkg")
    OUT_DIR = os.path.join(ROOT, "results", "v6_buildings", "routes_scored")
- scripts\summarise_access_gain.py (38444 bytes)
    gap_flag_composition.csv, checks.csv, buildings_access.gpkg, access_gain_report.txt, access_gain_summary.json
    WHAT IT DOES NOT ESTABLISH: network-level accessibility, graph connectivity gain, monetary cost, road width, building accuracy,
    "Candidate polygons are unverified model predictions. UNRESOLVED_MERGE polygons are settlement extents, so counts are polygons, not verified buildings
    ap.add_argument("--gap-m", type=float, default=50.0, help="gap threshold used by assess_building_access_v2 (cross-checked against the data)")
    # ---- 3. building sets (derived from the data; definitions are explicit)
    sum_rows.append(OrderedDict(run=rn, scenario=SCENARIO_LABEL[scen], building_set=sname, set_role=role, threshold_m=T, n_polygons=n,
    sub = summ_df[(summ_df.building_set == sname) & (summ_df.threshold_m == a.gap_m)]
    for _, grp in summ_df.groupby(["run", "scenario", "building_set"], sort=False):
- scripts\test_damarakunta_channel_orders_model.py (4447 bytes)
    CHECKPOINT = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
    print("Checkpoint:", CHECKPOINT)
    checkpoint = torch.load(
    CHECKPOINT,
    checkpoint["state_dict"],
    print("Checkpoint epoch:", checkpoint.get("epoch"))
    print("Training mIoU:", checkpoint.get("mIoU"))
    print("Training mDice:", checkpoint.get("mDice"))
- scripts\test_damarakunta_esri_inference.py (8049 bytes)
    CHECKPOINT = Path(
    r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
    "Building",
    print("Checkpoint:", CHECKPOINT)
    if not CHECKPOINT.exists():
    f"Checkpoint not found: {CHECKPOINT}"
    checkpoint = torch.load(
    CHECKPOINT,
- scripts\test_damarakunta_residential_inference.py (1743 bytes)
    MODEL_PATH = r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
    checkpoint = torch.load(
    checkpoint["state_dict"],
    print("Checkpoint epoch:", checkpoint.get("epoch"))
    print("Training mIoU:", checkpoint.get("mIoU"))
    print("Training mDice:", checkpoint.get("mDice"))
    "Building",
- scripts\test_esri_appearance_normalization.py (4988 bytes)
    CHECKPOINT = Path(
    r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
    checkpoint = torch.load(
    CHECKPOINT,
    checkpoint["state_dict"],
    print("Checkpoint epoch:", checkpoint.get("epoch"))
    "Building",
- scripts\test_esri_scale_normalization.py (3654 bytes)
    CHECKPOINT = Path(
    r"D:\new_MPS\remoteSensingWebApp\checkpoints\best_model.pth"
    checkpoint = torch.load(
    CHECKPOINT,
    checkpoint["state_dict"],
    print("Checkpoint epoch:", checkpoint.get("epoch"))
    "Building",
- scripts\validate_damarakunta_route_connectivity_v3.py (14641 bytes)
    "building clearance, drainage, ownership and engineering feasibility."
    "- This does not assess ownership, drainage, roof/building clearance, or construction feasibility.",
- scripts\validate_damarakunta_route_connectivity_v3_backup.py (14641 bytes)
    "building clearance, drainage, ownership and engineering feasibility."
    "- This does not assess ownership, drainage, roof/building clearance, or construction feasibility.",
- scripts\visualize_school_predictions.py (6865 bytes)
    BUILDING_ID = 2
    building = pred == BUILDING_ID
    # Panel 2: Building predictions blended in red.
    overlay[building] = (
    0.55 * overlay[building]
    axes[r, 1].set_title("Building predictions in red")
    np.ma.masked_where(~building, building),
    "Red: building | Cyan: compound boundary"