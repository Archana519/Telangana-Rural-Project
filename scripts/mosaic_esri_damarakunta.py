import glob
from pathlib import Path

import rasterio
from rasterio.merge import merge


# ============================================================
# INPUT
# ============================================================

input_dir = Path(
    "Siddipet/Damarakunta/raw/imagery/esri_full_tiles"
)

files = sorted(
    glob.glob(
        str(input_dir / "damarakunta_esri_tile_*.tif")
    )
)

print("=" * 70)
print("DAMARAKUNTA ESRI HIGH-RESOLUTION MOSAIC")
print("=" * 70)

print()
print("Tiles found:", len(files))

if len(files) != 11:
    raise RuntimeError(
        f"Expected 11 valid tiles, found {len(files)}"
    )


# ============================================================
# VERIFY INPUTS
# ============================================================

src_files = []

for file in files:

    print()
    print("Checking:", Path(file).name)

    src = rasterio.open(file)

    print("  Size:", src.width, "x", src.height)
    print("  Bands:", src.count)
    print("  CRS:", src.crs)
    print("  Resolution:", src.res)
    print("  Bounds:", src.bounds)

    if src.crs is None:
        raise RuntimeError(
            f"Missing CRS: {file}"
        )

    if src.crs.to_epsg() != 32644:
        raise RuntimeError(
            f"Unexpected CRS in {file}: {src.crs}"
        )

    if src.count < 3:
        raise RuntimeError(
            f"Expected RGB bands in {file}"
        )

    src_files.append(src)


# ============================================================
# MOSAIC
# ============================================================

print()
print("=" * 70)
print("MOSAICKING...")
print("=" * 70)

mosaic, transform = merge(
    src_files,
    indexes=[1, 2, 3],
    res=(0.6, 0.6)
)

print()
print("Mosaic array shape:", mosaic.shape)


# ============================================================
# OUTPUT PROFILE
# ============================================================

output_file = Path(
    "Siddipet/Damarakunta/aligned/"
    "damarakunta_esri_highres_mosaic_0p6m.tif"
)

output_file.parent.mkdir(
    parents=True,
    exist_ok=True
)

height = mosaic.shape[1]
width = mosaic.shape[2]

profile = src_files[0].profile.copy()

profile.update(
    {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 3,
        "dtype": mosaic.dtype,
        "crs": "EPSG:32644",
        "transform": transform,
        "compress": "lzw",
        "BIGTIFF": "IF_SAFER",
    }
)


# ============================================================
# WRITE MOSAIC
# ============================================================

print()
print("Writing mosaic:")
print(output_file)

with rasterio.open(
    output_file,
    "w",
    **profile
) as dst:

    dst.write(mosaic)


# ============================================================
# CLOSE INPUTS
# ============================================================

for src in src_files:
    src.close()


# ============================================================
# FINAL VERIFICATION
# ============================================================

print()
print("=" * 70)
print("FINAL MOSAIC VERIFICATION")
print("=" * 70)

with rasterio.open(output_file) as check:

    print()
    print("File:", output_file)
    print("Width:", check.width)
    print("Height:", check.height)
    print("Bands:", check.count)
    print("CRS:", check.crs)
    print("Resolution:", check.res)
    print("Bounds:", check.bounds)
    print("Dtype:", check.dtypes)
    print("Transform:", check.transform)


print()
print("=" * 70)
print("MOSAIC COMPLETED SUCCESSFULLY")
print("=" * 70)