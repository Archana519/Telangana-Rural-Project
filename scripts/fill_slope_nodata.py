import rasterio
import numpy as np
from pathlib import Path
from scipy.ndimage import distance_transform_edt

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Angadi_Kistapur")

INPUT_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_slope_utm44n_10m.tif"
)

OUTPUT_PATH = (
    BASE / "aligned" /
    "angadi_kistapur_slope_filled_10m.tif"
)

with rasterio.open(INPUT_PATH) as src:

    slope = src.read(1).astype(np.float32)
    profile = src.profile.copy()

    nodata = src.nodata

    print("=" * 80)
    print("FILLING SLOPE NODATA")
    print("=" * 80)

    print("Input:", INPUT_PATH)
    print("Size:", slope.shape)
    print("NoData value:", nodata)

    valid_mask = (
        np.isfinite(slope) &
        (slope != nodata)
    )

    nodata_mask = ~valid_mask

    print()
    print("Valid pixels:", int(valid_mask.sum()))
    print("NoData pixels:", int(nodata_mask.sum()))

    # Nearest-neighbour filling.
    # distance_transform_edt returns the nearest valid pixel
    # index for every NoData pixel.
    _, indices = distance_transform_edt(
        nodata_mask,
        return_distances=True,
        return_indices=True
    )

    filled = slope.copy()

    nearest_rows = indices[0]
    nearest_cols = indices[1]

    filled[nodata_mask] = slope[
        nearest_rows[nodata_mask],
        nearest_cols[nodata_mask]
    ]

    profile.update(
        dtype="float32",
        nodata=-9999.0,
        compress="lzw"
    )

    with rasterio.open(
        OUTPUT_PATH,
        "w",
        **profile
    ) as dst:

        dst.write(filled, 1)

    print()
    print("Output:", OUTPUT_PATH)

    print()
    print("Filled slope statistics:")

    valid = filled[
        np.isfinite(filled)
    ]

    print("Minimum:", float(np.min(valid)))
    print("Maximum:", float(np.max(valid)))
    print("Mean:", float(np.mean(valid)))
    print("Median:", float(np.median(valid)))

    remaining_nodata = np.sum(
        ~np.isfinite(filled)
    )

    print("Remaining invalid pixels:", int(remaining_nodata))

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)