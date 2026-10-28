import rasterio
import geopandas as gpd
from rasterio.mask import mask

worldcover_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\raw\landcover\ESA_WorldCover_10m_2021_v200_N15E078_Map.tif"

boundary_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\raw\tgrac_master_admin\village_boundary_20260930T115300Z.geojson"

output_path = r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur\aligned\angadi_kistapur_worldcover.tif"

print("Reading village boundary...")
boundary = gpd.read_file(boundary_path)

print("Reading WorldCover...")
with rasterio.open(worldcover_path) as src:

    # WorldCover is EPSG:4326, so make sure boundary uses same CRS
    boundary = boundary.to_crs(src.crs)

    geometries = boundary.geometry.tolist()

    print("Clipping WorldCover to village boundary...")

    clipped, transform = mask(
        src,
        geometries,
        crop=True,
        nodata=0
    )

    profile = src.profile.copy()
    profile.update(
        height=clipped.shape[1],
        width=clipped.shape[2],
        transform=transform,
        nodata=0,
        compress="lzw"
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(clipped)

print()
print("DONE")
print("Output:", output_path)
print("Size:", clipped.shape[2], "x", clipped.shape[1])