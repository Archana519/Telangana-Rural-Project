from pathlib import Path

import geopandas as gpd
import rasterio
from rasterio.warp import transform_bounds

ROOT = Path(r"D:\Telangana_Rural_Project")
VILLAGE = ROOT / "Siddipet" / "Damarakunta"

BOUNDARY_PATH = (
    VILLAGE / "study_area" / "damarakunta_boundary.gpkg"
)

SOURCES = {
    "WorldCover": (
        ROOT / "Siddipet" / "Angadi_Kistapur"
        / "raw" / "landcover"
        / "ESA_WorldCover_10m_2021_v200_N15E078_Map.tif"
    ),
    "DEM": (
        ROOT / "Siddipet" / "Angadi_Kistapur"
        / "raw" / "dem" / "n17_e078_1arc_v3.tif"
    ),
}

boundary = gpd.read_file(BOUNDARY_PATH)

if boundary.empty or boundary.geometry.isna().all():
    raise ValueError("Damarakunta boundary is empty.")

boundary = boundary.loc[boundary.geometry.notna()].copy()
boundary = boundary.loc[~boundary.geometry.is_empty].copy()

print("Damarakunta boundary CRS:", boundary.crs)
print("Boundary bounds:", boundary.total_bounds)
print()

for name, path in SOURCES.items():
    print("=" * 65)
    print(name)
    print("Path:", path)

    if not path.exists():
        print("STATUS: SOURCE FILE NOT FOUND")
        continue

    with rasterio.open(path) as src:
        print("CRS:", src.crs)
        print("Dimensions:", src.width, "x", src.height)
        print("Band count:", src.count)
        print("Pixel size:", src.res)
        print("NoData:", src.nodata)
        print("Raster bounds:", src.bounds)

        if src.crs is None or boundary.crs is None:
            print("COVERAGE: Cannot check because CRS is missing.")
            continue

        village_in_raster_crs = boundary.to_crs(src.crs)
        village_geom = village_in_raster_crs.geometry.union_all()
        raster_bounds = src.bounds

        bounds_intersect = (
            village_geom.bounds[0] < raster_bounds.right
            and village_geom.bounds[2] > raster_bounds.left
            and village_geom.bounds[1] < raster_bounds.top
            and village_geom.bounds[3] > raster_bounds.bottom
        )

        print("Boundary bounding boxes intersect:", bounds_intersect)

        if bounds_intersect:
            try:
                from rasterio.mask import mask

                _, out_transform = mask(
                    src,
                    [village_geom],
                    crop=True,
                    filled=False
                )
                print("Clipped-window transform:", out_transform)
                print("COVERAGE: Intersects; full coverage still needs verification.")
            except ValueError as exc:
                print("COVERAGE: Could not crop raster:", exc)
        else:
            print("COVERAGE: No intersection; this raster cannot cover the village.")

    print()

print("=" * 65)
print("CHECK COMPLETE")