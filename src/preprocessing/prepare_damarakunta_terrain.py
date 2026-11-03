from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask

ROOT = Path(r"D:\Telangana_Rural_Project")
VILLAGE = ROOT / "Siddipet" / "Damarakunta"

BOUNDARY_PATH = (
    VILLAGE / "study_area" / "damarakunta_boundary.gpkg"
)

WORLD_COVER_SOURCE = (
    ROOT / "Siddipet" / "Angadi_Kistapur"
    / "raw" / "landcover"
    / "ESA_WorldCover_10m_2021_v200_N15E078_Map.tif"
)

DEM_SOURCE = (
    ROOT / "Siddipet" / "Angadi_Kistapur"
    / "raw" / "dem" / "n17_e078_1arc_v3.tif"
)

WORLD_COVER_OUTPUT = (
    VILLAGE / "raw" / "landcover"
    / "damarakunta_worldcover_clip.tif"
)

DEM_OUTPUT = (
    VILLAGE / "raw" / "dem"
    / "damarakunta_dem_clip.tif"
)


def clip_raster(source_path, output_path, boundary, name):
    if not source_path.exists():
        raise FileNotFoundError(f"{name} source not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(source_path) as src:
        if src.crs is None:
            raise ValueError(f"{name} source has no CRS.")

        boundary_src = boundary.to_crs(src.crs)
        geom = boundary_src.geometry.union_all()

        # Check that the raster covers the complete village boundary.
        from shapely.geometry import box

        raster_footprint = box(
            src.bounds.left,
            src.bounds.bottom,
            src.bounds.right,
            src.bounds.top
        )

        if not raster_footprint.covers(geom):
            raise ValueError(
                f"{name} raster does not fully cover the village boundary. "
                "No output was written."
            )

        clipped, transform = mask(
            src,
            [geom],
            crop=True,
            filled=False
        )

        data = clipped.filled(src.nodata if src.nodata is not None else 0)

        profile = src.profile.copy()
        profile.update(
            height=data.shape[1],
            width=data.shape[2],
            transform=transform,
            compress="lzw"
        )

        if src.nodata is None:
            profile.update(nodata=0)

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data)

        valid = ~np.ma.getmaskarray(clipped[0])

        print(f"\n{name}")
        print("Source:", source_path)
        print("Output:", output_path)
        print("CRS:", src.crs)
        print("Dimensions:", data.shape[2], "x", data.shape[1])
        print("Valid pixels in cropped window:", int(valid.sum()))
        print("Total pixels in cropped window:", int(valid.size))


def main():
    if not BOUNDARY_PATH.exists():
        raise FileNotFoundError(f"Boundary not found: {BOUNDARY_PATH}")

    boundary = gpd.read_file(BOUNDARY_PATH)

    if boundary.empty or boundary.crs is None:
        raise ValueError("Boundary is empty or has no CRS.")

    boundary = boundary.loc[boundary.geometry.notna()].copy()
    boundary = boundary.loc[~boundary.geometry.is_empty].copy()

    if boundary.empty:
        raise ValueError("Boundary has no valid geometries.")

    print("Preparing Damarakunta source rasters")
    print("Boundary:", BOUNDARY_PATH)
    print("Boundary CRS:", boundary.crs)

    clip_raster(
        WORLD_COVER_SOURCE,
        WORLD_COVER_OUTPUT,
        boundary,
        "WorldCover"
    )

    clip_raster(
        DEM_SOURCE,
        DEM_OUTPUT,
        boundary,
        "DEM"
    )

    print("\nPreparation complete.")


if __name__ == "__main__":
    main()