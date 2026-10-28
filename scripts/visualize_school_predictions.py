
import os
import numpy as np
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
from rasterio.features import geometry_mask
from matplotlib.colors import ListedColormap

# --------------------------------------------------
# PATHS
# --------------------------------------------------
BASE = r"D:\Telangana_Rural_Project\Siddipet\Damarakunta"

REF = os.path.join(
    BASE, "reference", "school_compounds_utm44n.gpkg"
)
TILES = os.path.join(
    BASE, "predictions", "school_diagnostic_tiles"
)
MASKS = os.path.join(
    BASE, "predictions", "school_diagnostic_masks"
)

# Primary and fallback output paths
OUT = os.path.join(
    BASE, "results", "school_prediction_comparison.png"
)
FALLBACK_OUT = (
    r"D:\new_MPS\remoteSensingWebApp\project"
    r"\school_prediction_comparison.png"
)

BUILDING_ID = 2

schools = [
    (
        "MPPS DAMARAKUNTA",
        "mpps_school_tile.tif",
        "mpps_school_tile_mask.tif",
    ),
    (
        "ZPHS DAMARAKUNTA",
        "zphs_school_tile.tif",
        "zphs_school_tile_mask.tif",
    ),
]

# --------------------------------------------------
# LOAD REFERENCE POLYGONS
# --------------------------------------------------
if not os.path.isfile(REF):
    raise FileNotFoundError(f"Reference file not found: {REF}")

refs = gpd.read_file(REF)

if refs.crs is None:
    raise ValueError("School reference layer has no CRS.")

if "School_Name" not in refs.columns:
    raise ValueError(
        "School_Name column missing. Available columns: "
        + str(list(refs.columns))
    )

# --------------------------------------------------
# CREATE FIGURE
# --------------------------------------------------
fig, axes = plt.subplots(2, 3, figsize=(16, 10))

try:
    for r, (name, tile_name, mask_name) in enumerate(schools):
        match = refs[refs["School_Name"] == name]

        if match.empty:
            raise ValueError(f"Reference polygon missing: {name}")

        geom = match.iloc[0].geometry

        if geom is None or geom.is_empty:
            raise ValueError(f"Empty school polygon: {name}")

        tile_path = os.path.join(TILES, tile_name)
        mask_path = os.path.join(MASKS, mask_name)

        if not os.path.isfile(tile_path):
            raise FileNotFoundError(f"Tile not found: {tile_path}")

        if not os.path.isfile(mask_path):
            raise FileNotFoundError(f"Mask not found: {mask_path}")

        with rasterio.open(tile_path) as src:
            image = src.read([1, 2, 3]).transpose(1, 2, 0)
            image_transform = src.transform
            image_crs = src.crs
            image_bounds = src.bounds

        with rasterio.open(mask_path) as src:
            pred = src.read(1)
            mask_transform = src.transform
            mask_crs = src.crs
            mask_bounds = src.bounds

        if image_crs is None or mask_crs is None:
            raise ValueError(f"Missing raster CRS for {name}")

        if image_crs != mask_crs:
            raise ValueError(f"Image/mask CRS mismatch for {name}")

        if (
            image.shape[:2] != pred.shape
            or image_transform != mask_transform
            or image_bounds != mask_bounds
        ):
            raise ValueError(
                f"Image and mask grids do not align for {name}"
            )

        # Reproject the compound geometry when necessary.
        if refs.crs != mask_crs:
            geom_raster = (
                gpd.GeoSeries([geom], crs=refs.crs)
                .to_crs(mask_crs)
                .iloc[0]
            )
        else:
            geom_raster = geom

        compound = geometry_mask(
            [geom_raster],
            transform=mask_transform,
            out_shape=pred.shape,
            invert=True,
        )

        # Display-only contrast enhancement.
        display = image.astype(np.float32)
        lo, hi = np.percentile(display, [2, 98])
        display = np.clip(
            (display - lo) / max(float(hi - lo), 1e-6),
            0, 1,
        )

        building = pred == BUILDING_ID

        # Panel 1: Original image.
        axes[r, 0].imshow(display)
        axes[r, 0].set_title(f"{name}: Original")

        # Panel 2: Building predictions blended in red.
        overlay = display.copy()
        overlay[building] = (
            0.55 * overlay[building]
            + 0.45 * np.array([1.0, 0.0, 0.0])
        )

        axes[r, 1].imshow(overlay)
        axes[r, 1].set_title("Building predictions in red")

        # Panel 3: Prediction pixels and compound boundary.
        axes[r, 2].imshow(display)
        axes[r, 2].imshow(
            np.ma.masked_where(~building, building),
            cmap=ListedColormap(["red"]),
            vmin=0,
            vmax=1,
            alpha=0.65,
            interpolation="nearest",
        )

        if compound.any() and (~compound).any():
            axes[r, 2].contour(
                compound.astype(float),
                levels=[0.5],
                colors=["cyan"],
                linewidths=1.5,
            )

        axes[r, 2].set_title(
            "Red: building | Cyan: compound boundary"
        )

        # Report compound coverage, not accuracy.
        inside = int(np.count_nonzero(building & compound))
        compound_pixels = int(np.count_nonzero(compound))
        coverage = (
            100.0 * inside / compound_pixels
            if compound_pixels else 0.0
        )

        print(f"\n{name}")
        print("Predicted building pixels inside compound:", inside)
        print("Compound raster pixels:", compound_pixels)
        print(f"Compound coverage by predictions: {coverage:.2f}%")
        print("Coverage is not building accuracy or IoU.")

        for ax in axes[r]:
            ax.axis("off")

    fig.tight_layout()

    # --------------------------------------------------
    # SAVE WITH FALLBACK
    # --------------------------------------------------
    saved_path = None
    errors = []

    for output_path in [OUT, FALLBACK_OUT]:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.savefig(
                output_path,
                dpi=150,
                format="png",
                bbox_inches="tight",
            )
            saved_path = output_path
            break
        except OSError as exc:
            errors.append(f"{output_path}: {exc}")

    if saved_path is None:
        raise OSError(
            "Could not save the comparison image.\n"
            + "\n".join(errors)
        )

    print("\nVisual comparison saved successfully:")
    print(saved_path)

finally:
    plt.close(fig)
