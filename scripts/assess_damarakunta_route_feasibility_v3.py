import geopandas as gpd
import pandas as pd
from pathlib import Path

# ============================================================
# DAMARAKUNTA ROUTE FEASIBILITY SCREENING - V3
# This module screens V3 candidate routes only.
# It does NOT replace the overall major-project workflow.
# ============================================================

# 1. PROJECT PATHS
ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = ROOT / "reference"
RESULTS = ROOT / "results"

ROUTES = RESULTS / "damarakunta_routes_v3.gpkg"
PARCELS = REF / "damarakunta_cadastral_valid.gpkg"
SCHOOLS = REF / "school_compounds_utm44n.gpkg"
ROADS = REF / "tgrac_road_network.gpkg"

# V3 output names preserve all V2 outputs.
OUT_CSV = RESULTS / "damarakunta_route_feasibility_screening_v3.csv"
OUT_GPKG = RESULTS / "damarakunta_route_parcel_impacts_v3.gpkg"
TEMP_CSV = RESULTS / "damarakunta_route_feasibility_screening_v3_temporary.csv"

# 2. CHECK INPUT FILES
for path in [ROUTES, PARCELS, SCHOOLS, ROADS]:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")

# Do not overwrite outputs from earlier runs.
existing = [p for p in [OUT_CSV, OUT_GPKG, TEMP_CSV] if p.exists()]
if existing:
    raise FileExistsError(
        "V3 output file(s) already exist. Rename or back them up first:\n"
        + "\n".join(str(p) for p in existing)
    )

# 3. LOAD DATA
routes = gpd.read_file(ROUTES)
parcels = gpd.read_file(PARCELS)
schools = gpd.read_file(SCHOOLS)
roads = gpd.read_file(ROADS)

for name, layer in [
    ("Routes", routes),
    ("Parcels", parcels),
    ("Schools", schools),
    ("Roads", roads),
]:
    if layer.crs is None:
        raise ValueError(f"{name} layer has no defined CRS.")

target_crs = routes.crs

if target_crs is None or not target_crs.is_projected:
    raise ValueError(
        "Route CRS must be projected for distance measurements in metres."
    )

# 4. ALIGN CRS AND CLEAN GEOMETRIES
parcels = parcels.to_crs(target_crs)
schools = schools.to_crs(target_crs)
roads = roads.to_crs(target_crs)

def clean_geometries(layer):
    layer = layer[
        layer.geometry.notna() & ~layer.geometry.is_empty
    ].copy()
    return layer

routes = clean_geometries(routes)
parcels = clean_geometries(parcels)
schools = clean_geometries(schools)
roads = clean_geometries(roads)

if routes.empty:
    raise ValueError("No usable route geometries were found.")

# 5. SCREEN ROUTES
parcel_records = []
summary_records = []

for _, route in routes.iterrows():
    geom = route.geometry

    route_id = str(route.get("facility_id", "unknown"))
    facility = str(route.get("facility_name", "unknown"))
    alternative = route.get("alternative", "unknown")

    if geom.geom_type not in ["LineString", "MultiLineString"]:
        print(f"Warning: skipping non-line geometry for {facility}")
        continue

    # A. Cadastral parcel intersections
    hits = parcels[parcels.intersects(geom)]
    parcel_ids = []

    for _, parcel in hits.iterrows():
        parcel_id = str(parcel.get("Base_Syno", "unknown"))
        parcel_ids.append(parcel_id)

        try:
            intersection = parcel.geometry.intersection(geom)

            if intersection.is_empty:
                continue

            # Intersection length can be zero for point-only touches.
            parcel_records.append({
                "facility_id": route_id,
                "facility_name": facility,
                "alternative": alternative,
                "parcel_survey_id": parcel_id,
                "intersection_length_m": float(intersection.length),
                "intersection_geometry_type": intersection.geom_type,
                "ownership_status": "UNKNOWN",
                "legal_access_status": "NOT_VERIFIED",
                "geometry": intersection,
            })

        except Exception as error:
            print(
                f"Warning: parcel {parcel_id}, facility {facility}: {error}"
            )

    # B. School compound intersections
    school_hits = schools[schools.intersects(geom)]

    # C. Distance to nearest mapped road
    if not roads.empty:
        road_distance = float(roads.distance(geom).min())
    else:
        road_distance = float("nan")

    # D. Carry through route-planning diagnostics when available
    # Field names are checked safely because schemas can vary by version.
    route_diagnostics = {}
    for field in [
        "route_length_m",
        "facility_snap_distance_m",
        "facility_to_route_distance_m",
        "facility_to_start_distance_m",
        "start_to_road_distance_m",
        "end_to_road_distance_m",
        "accumulated_cost",
        "max_slope_deg",
        "builtup_cells",
        "water_cells",
        "overlap_ratio",
        "corridor_penalty",
        "location_status",
        "status",
        "review_status",
    ]:
        if field in route.index:
            route_diagnostics[field] = route.get(field)

    # D. Route summary
    record = {
        "facility_id": route_id,
        "facility_name": facility,
        "alternative": alternative,
        "route_length_m": float(geom.length),
        "intersected_parcel_count": len(hits),
        "parcel_survey_ids": "; ".join(sorted(set(parcel_ids))),
        "school_compound_intersections": len(school_hits),
        "distance_to_nearest_existing_road_m": road_distance,
        "ownership_clearance": "UNKNOWN",
        "drainage_clearance": "NOT_ASSESSED_NO_DEDICATED_LAYER",
        "building_clearance": "NOT_VERIFIED",
        "construction_feasibility": "REQUIRES_ENGINEERING_REVIEW",
        "overall_status": "PRELIMINARY_SCREENING_ONLY",
    }
    record.update(route_diagnostics)
    summary_records.append(record)

if not summary_records:
    raise ValueError("No line route records were available for screening.")

# 6. SAVE CSV SAFELY
summary = pd.DataFrame(summary_records)
summary.to_csv(TEMP_CSV, index=False)
TEMP_CSV.replace(OUT_CSV)

# 7. SAVE PARCEL INTERSECTIONS
if parcel_records:
    impacts = gpd.GeoDataFrame(
        parcel_records,
        geometry="geometry",
        crs=target_crs,
    )

    impacts.to_file(
        OUT_GPKG,
        layer="parcel_route_intersections",
        driver="GPKG",
    )
else:
    print("No route/parcel intersection geometries found; no parcel GPKG created.")

# 8. DISPLAY RESULTS
print("\n" + "=" * 70)
print("DAMARAKUNTA ROUTE FEASIBILITY SCREENING V3 COMPLETE")
print("=" * 70)

print(f"\nRoutes screened: {len(summary)}")
print("\n--- Feasibility Summary ---")
print(summary.to_string(index=False))

print("\n--- Output Files ---")
print(f"CSV summary: {OUT_CSV}")
if parcel_records:
    print(f"Parcel impacts: {OUT_GPKG}")

print("\n--- Limitations ---")
print("1. Parcel intersections do not identify legal owners.")
print("2. Ownership, consent and right-of-way remain unverified.")
print("3. Drainage, culverts and flooding have not been assessed.")
print("4. Building clearance has not been verified.")
print("5. School-compound intersections require entrance review.")
print("6. Nearest-road distance does not prove usable connectivity.")
print("7. WorldCover 10 m classes cannot confirm individual roof clearance.")
print("8. Candidate routes require visual, engineering and field review.")
print("9. Results are preliminary GIS screening, not construction approval.")
print("10. This module screens public-facility route candidates only;")
print("    residential-building connectivity and shared-route optimization")
print("    remain part of the unchanged major-project workflow.")
