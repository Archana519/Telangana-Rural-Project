import rasterio
import geopandas as gpd
from shapely.geometry import box
from pathlib import Path


mosaic_path = Path(
    "Siddipet/Damarakunta/aligned/"
    "damarakunta_esri_highres_mosaic_0p6m.tif"
)

boundary_path = Path(
    "Siddipet/Damarakunta/study_area/"
    "damarakunta_boundary.gpkg"
)


print("=" * 70)
print("DAMARAKUNTA ESRI MOSAIC COVERAGE CHECK")
print("=" * 70)


# ------------------------------------------------------------
# READ MOSAIC
# ------------------------------------------------------------

with rasterio.open(mosaic_path) as src:

    mosaic_crs = src.crs
    mosaic_bounds = src.bounds

    print()
    print("Mosaic CRS:", mosaic_crs)
    print("Mosaic bounds:", mosaic_bounds)
    print("Mosaic resolution:", src.res)
    print("Mosaic size:", src.width, "x", src.height)


mosaic_polygon = box(
    mosaic_bounds.left,
    mosaic_bounds.bottom,
    mosaic_bounds.right,
    mosaic_bounds.top
)


# ------------------------------------------------------------
# READ VILLAGE BOUNDARY
# ------------------------------------------------------------

boundary = gpd.read_file(
    boundary_path
)

print()
print("Boundary CRS:", boundary.crs)
print("Boundary records:", len(boundary))


if boundary.crs != mosaic_crs:
    boundary = boundary.to_crs(
        mosaic_crs
    )


village_geometry = boundary.geometry.unary_union


# ------------------------------------------------------------
# AREA CALCULATIONS
# ------------------------------------------------------------

village_area = village_geometry.area

covered_geometry = village_geometry.intersection(
    mosaic_polygon
)

covered_area = covered_geometry.area

uncovered_geometry = village_geometry.difference(
    mosaic_polygon
)

uncovered_area = uncovered_geometry.area


coverage_percent = (
    covered_area / village_area
) * 100

uncovered_percent = (
    uncovered_area / village_area
) * 100


# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

print()
print("=" * 70)
print("COVERAGE RESULTS")
print("=" * 70)

print()
print(
    f"Village area:       {village_area:,.2f} m²"
)

print(
    f"Mosaic-covered area: {covered_area:,.2f} m²"
)

print(
    f"Uncovered area:      {uncovered_area:,.2f} m²"
)

print(
    f"Coverage:            {coverage_percent:.4f}%"
)

print(
    f"Uncovered:           {uncovered_percent:.4f}%"
)


# ------------------------------------------------------------
# SAVE COVERAGE POLYGON
# ------------------------------------------------------------

coverage_output = Path(
    "Siddipet/Damarakunta/results/"
    "damarakunta_esri_mosaic_coverage.gpkg"
)

coverage_output.parent.mkdir(
    parents=True,
    exist_ok=True
)

coverage_layer = gpd.GeoDataFrame(
    {
        "type": ["covered", "uncovered"],
        "area_m2": [
            covered_area,
            uncovered_area
        ],
        "geometry": [
            covered_geometry,
            uncovered_geometry
        ]
    },
    crs=mosaic_crs
)

coverage_layer.to_file(
    coverage_output,
    layer="coverage",
    driver="GPKG"
)


print()
print("Coverage layer saved:")
print(coverage_output)

print()
print("=" * 70)
print("COVERAGE CHECK COMPLETED")
print("=" * 70)