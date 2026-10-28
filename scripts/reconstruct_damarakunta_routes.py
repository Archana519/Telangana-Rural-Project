from pathlib import Path
import heapq
import math
import warnings

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

# Damarakunta-only reconstruction. Existing inputs are read-only; outputs use new names.
BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
ALIGNED = BASE / "aligned"
RESULTS = BASE / "results"
IMAGERY = ALIGNED / "damarakunta_esri_highres_mosaic_0p6m.tif"
FACILITIES_FILE = REF / "damarakunta_priority_facilities.gpkg"
ROADS_FILE = REF / "tgrac_road_network.gpkg"
WORLD_FILE = ALIGNED / "damarakunta_worldcover_10m.tif"
SLOPE_FILE = ALIGNED / "damarakunta_slope_10m.tif"
COST_FILE = ALIGNED / "damarakunta_cost_surface_10m.tif"
BLOCKED_FILE = ALIGNED / "damarakunta_prohibited_mask_10m.tif"

OUT_GPKG = RESULTS / "damarakunta_reconstructed_route_alternatives.gpkg"
OUT_CSV = RESULTS / "damarakunta_reconstructed_route_comparison.csv"
OUT_FAC_CSV = RESULTS / "damarakunta_reconstructed_facility_checks.csv"
OUT_MAP = RESULTS / "damarakunta_reconstructed_routes_map.png"
OUT_NOTE = RESULTS / "damarakunta_reconstructed_routes_README.txt"

CRS = "EPSG:32644"
MAX_START_SNAP_M = 35.0
MAX_SEARCH_NODES = 300_000
N_ALTERNATIVES = 3
# WorldCover codes: 50 built-up, 80 water. WorldCover is 10 m and may miss individual roofs.
BUILT_UP_CLASS = 50
WATER_CLASS = 80
# Built-up cells are excluded from route interiors where possible. Facility start is allowed
# in built-up only if no nearby non-built traversable cell is available (flagged in report).
# Routes are planning candidates, NOT construction-ready alignments.

def require_files(paths):
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Required input file(s) missing:\n" + "\n".join(missing))

def nearest_cell(point, mask, transform, max_distance):
    row, col = rasterio.transform.rowcol(transform, point.x, point.y)
    h, w = mask.shape
    radius = int(math.ceil(max_distance / max(abs(transform.a), abs(transform.e))))
    options = []
    for r in range(max(0, row-radius), min(h, row+radius+1)):
        for c in range(max(0, col-radius), min(w, col+radius+1)):
            if not mask[r, c]:
                continue
            x, y = rasterio.transform.xy(transform, r, c, offset="center")
            d = math.hypot(x-point.x, y-point.y)
            if d <= max_distance:
                options.append((d, r, c))
    return min(options) if options else None

def dijkstra(start, traversable, cell_cost, road_cells, transform, avoid_mask=None,
             avoid_penalty=0.0, max_nodes=MAX_SEARCH_NODES):
    h, w = traversable.shape
    sr, sc = start
    dist = { (sr, sc): 0.0 }
    prev = {}
    queue = [(0.0, sr, sc)]
    neighbors = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    settled = 0
    while queue:
        d, r, c = heapq.heappop(queue)
        if d != dist.get((r,c), math.inf):
            continue
        settled += 1
        if settled > max_nodes:
            return None, None, "SEARCH_LIMIT_REACHED"
        if road_cells[r,c] and (r,c) != (sr,sc):
            path = [(r,c)]
            cur = (r,c)
            while cur != (sr,sc):
                cur = prev[cur]
                path.append(cur)
            path.reverse()
            return path, d, "ROUTE_FOUND"
        for dr, dc in neighbors:
            nr, nc = r+dr, c+dc
            if not (0 <= nr < h and 0 <= nc < w) or not traversable[nr,nc]:
                continue
            if dr and dc and (not traversable[r+dr,c] or not traversable[r,c+dc]):
                continue
            step = math.hypot(dr*transform.e, dc*transform.a)
            risk = 0.0
            if avoid_mask is not None and avoid_mask[nr,nc]:
                risk = avoid_penalty
            edge = step * ((cell_cost[r,c] + cell_cost[nr,nc]) / 2.0 + risk)
            nd = d + edge
            if nd < dist.get((nr,nc), math.inf):
                dist[(nr,nc)] = nd
                prev[(nr,nc)] = (r,c)
                heapq.heappush(queue, (nd,nr,nc))
    return None, None, "NO_PATH"

def path_geometry(path, transform):
    coords = [rasterio.transform.xy(transform, r, c, offset="center") for r,c in path]
    if len(coords) == 1:
        return None, coords
    return LineString(coords), coords

def safe_read_vector(path):
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError(f"Missing CRS in {path}")
    return gdf.to_crs(CRS)

def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    require_files([FACILITIES_FILE, ROADS_FILE, WORLD_FILE, SLOPE_FILE, COST_FILE, BLOCKED_FILE, IMAGERY])
    # Never overwrite outputs from earlier runs.
    outputs = [OUT_GPKG, OUT_CSV, OUT_FAC_CSV, OUT_MAP, OUT_NOTE]
    existing = [str(p) for p in outputs if p.exists()]
    if existing:
        raise FileExistsError("To preserve previous results, rename/remove these output files before rerunning:\n" + "\n".join(existing))

    facilities = safe_read_vector(FACILITIES_FILE)
    roads = safe_read_vector(ROADS_FILE)
    if "facility_name" not in facilities.columns:
        raise ValueError("Facility layer lacks 'facility_name'.")
    if "facility_id" not in facilities.columns:
        facilities["facility_id"] = [f"FAC_{i+1}" for i in range(len(facilities))]

    with rasterio.open(COST_FILE) as src:
        base_cost = src.read(1).astype(np.float32)
        transform, crs, nodata = src.transform, src.crs, src.nodata
        profile = src.profile.copy()
    if crs is None or crs.to_string() != CRS:
        raise ValueError(f"Expected cost raster CRS {CRS}; got {crs}")

    with rasterio.open(BLOCKED_FILE) as src:
        blocked = src.read(1)
        if (src.crs != crs or src.transform != transform or
            src.width != base_cost.shape[1] or src.height != base_cost.shape[0]):
            raise ValueError("Blocked mask is not aligned with cost raster.")
    with rasterio.open(WORLD_FILE) as src:
        world = src.read(1)
        if (src.crs != crs or src.transform != transform or
            src.width != base_cost.shape[1] or src.height != base_cost.shape[0]):
            raise ValueError("WorldCover is not aligned with cost raster.")
    with rasterio.open(SLOPE_FILE) as src:
        slope = src.read(1).astype(np.float32)
        if (src.crs != crs or src.transform != transform or
            src.width != base_cost.shape[1] or src.height != base_cost.shape[0]):
            raise ValueError("Slope is not aligned with cost raster.")

    valid = np.isfinite(base_cost) & (base_cost > 0) & (blocked == 0)
    if nodata is not None:
        valid &= base_cost != nodata
    # For route interiors, conservatively avoid WorldCover built-up and water.
    water = world == WATER_CLASS
    built = world == BUILT_UP_CLASS
    traversable = valid & ~water & ~built
    if not traversable.any():
        raise ValueError("No traversable cells remain after excluding water/built-up.")

    road_shapes = [(g, 1) for g in roads.geometry if g is not None and not g.is_empty]
    road_cells = rasterize(road_shapes, out_shape=base_cost.shape, transform=transform,
                           fill=0, all_touched=True, dtype="uint8").astype(bool)
    road_targets = road_cells & traversable
    if not road_targets.any():
        raise ValueError("No existing road cells overlap traversable cells. Check inputs/alignment.")

    # Approximate building conflict layer from WorldCover built-up class only.
    # It is not a roof footprint dataset and cannot confirm individual house boundaries.
    records, facility_rows = [], []
    union_roads = unary_union([g for g in roads.geometry if g is not None and not g.is_empty])
    height, width = base_cost.shape
    x_centres = transform.c + (np.arange(width) + 0.5) * transform.a
    y_centres = transform.f + (np.arange(height) + 0.5) * transform.e

    for _, fac in facilities.iterrows():
        geom = fac.geometry
        if geom is None or geom.is_empty or geom.geom_type != "Point":
            facility_rows.append({"facility_id": str(fac["facility_id"]), "facility_name": fac["facility_name"],
                                 "status": "INVALID_POINT"})
            continue
        road_dist = float(geom.distance(union_roads))
        # Prefer non-built traversable start cells; if none nearby, use valid cells and flag.
        snap = nearest_cell(geom, traversable, transform, MAX_START_SNAP_M)
        start_in_built = False
        if snap is None:
            snap = nearest_cell(geom, valid & ~water, transform, MAX_START_SNAP_M)
            start_in_built = snap is not None
        if snap is None:
            facility_rows.append({"facility_id": str(fac["facility_id"]), "facility_name": fac["facility_name"],
                                  "facility_to_nearest_road_m": round(road_dist,2),
                                  "status": "NO_START_CELL_WITHIN_35M"})
            continue
        snap_m, sr, sc = snap
        start_point = Point(rasterio.transform.xy(transform, sr, sc, offset="center"))
        # Each alternative discourages reusing the prior route corridor; costs remain positive.
        used_cells = np.zeros(base_cost.shape, dtype=bool)
        alternatives_for_fac = 0
        for alt in range(1, N_ALTERNATIVES+1):
            route_mask = road_targets.copy()
            # First route uses base cost. Later alternatives penalize a 3-cell corridor around
            # previously found route cells so search can find a different feasible corridor.
            avoid_mask = used_cells.copy() if alt > 1 else None
            penalty = 25.0 if alt > 1 else 0.0
            path, accumulated, status = dijkstra(
                (sr,sc), traversable, base_cost, route_mask, transform,
                avoid_mask=avoid_mask, avoid_penalty=penalty)
            if path is None:
                records.append({"facility_id": str(fac["facility_id"]), "facility_name": fac["facility_name"],
                                "facility_type": fac.get("facility_type","Unknown"), "alternative": alt,
                                "status": status, "start_snap_m": round(snap_m,2),
                                "facility_to_nearest_road_m": round(road_dist,2), "geometry": None})
                break
            geom_line, coords = path_geometry(path, transform)
            if geom_line is None:
                records.append({"facility_id": str(fac["facility_id"]), "facility_name": fac["facility_name"],
                                "facility_type": fac.get("facility_type","Unknown"), "alternative": alt,
                                "status": "ALREADY_ON_ROAD_OR_ZERO_LENGTH", "start_snap_m": round(snap_m,2),
                                "facility_to_nearest_road_m": round(road_dist,2), "geometry": None})
                break
            length_m = float(geom_line.length)
            built_count = sum(bool(built[r,c]) for r,c in path)
            water_count = sum(bool(water[r,c]) for r,c in path)
            max_slope = float(np.nanmax([slope[r,c] for r,c in path if np.isfinite(slope[r,c])])) if path else np.nan
            end_pt = Point(coords[-1])
            start_to_road = float(start_point.distance(union_roads))
            end_to_road = float(end_pt.distance(union_roads))
            # Only raster-level check: road endpoint should be close to source road geometry.
            endpoint_ok = end_to_road <= 15.0
            records.append({
                "facility_id": str(fac["facility_id"]), "facility_name": fac["facility_name"],
                "facility_type": fac.get("facility_type","Unknown"), "alternative": alt,
                "status": "CANDIDATE_REQUIRES_VISUAL_REVIEW",
                "route_length_m": round(length_m,2), "accumulated_cost": round(float(accumulated),2),
                "start_snap_m": round(float(snap_m),2), "facility_to_nearest_road_m": round(road_dist,2),
                "start_cell_to_road_m": round(start_to_road,2), "end_cell_to_road_m": round(end_to_road,2),
                "endpoint_within_15m_of_road": endpoint_ok, "worldcover_builtup_cells": built_count,
                "water_cells": water_count, "max_sampled_slope_deg": round(max_slope,2) if np.isfinite(max_slope) else None,
                "start_snap_used_builtup_fallback": bool(start_in_built), "geometry": geom_line
            })
            alternatives_for_fac += 1
            for r,c in path:
                # Penalize this path and a 3x3 corridor around it for the next alternative.
                for rr in range(max(0,r-1), min(height,r+2)):
                    for cc in range(max(0,c-1), min(width,c+2)):
                        used_cells[rr,cc] = True
        facility_rows.append({
            "facility_id": str(fac["facility_id"]), "facility_name": fac["facility_name"],
            "facility_type": fac.get("facility_type","Unknown"),
            "facility_easting": round(geom.x,2), "facility_northing": round(geom.y,2),
            "facility_to_nearest_road_m": round(road_dist,2), "selected_start_snap_m": round(float(snap_m),2),
            "start_cell_easting": round(start_point.x,2), "start_cell_northing": round(start_point.y,2),
            "status": "REFERENCE_POINT_NOT_FIELD_VERIFIED",
            "note": "Check point against imagery and official records; nearest-road distance is straight-line."
        })

    # Write reports even if some facilities could not be routed.
    pd.DataFrame(facility_rows).to_csv(OUT_FAC_CSV, index=False)
    report = pd.DataFrame([{k:v for k,v in row.items() if k != "geometry"} for row in records])
    report.to_csv(OUT_CSV, index=False)
    valid_geoms = [r for r in records if r.get("geometry") is not None]
    if valid_geoms:
        out_gdf = gpd.GeoDataFrame(valid_geoms, geometry="geometry", crs=CRS)
        out_gdf.to_file(OUT_GPKG, layer="route_alternatives", driver="GPKG")

    # Create an automatic PNG map using the existing satellite mosaic and overlays.
    with rasterio.open(IMAGERY) as src:
        # Downsample for plotting to avoid loading the full high-resolution mosaic into RAM.
        scale = min(1.0, 2400.0 / max(src.width, src.height))
        out_h = max(1, int(src.height * scale))
        out_w = max(1, int(src.width * scale))
        image = src.read(
            [1, 2, 3],
            out_shape=(3, out_h, out_w),
            resampling=rasterio.enums.Resampling.bilinear
        )
        image_crs = src.crs
        if image_crs is None or image_crs.to_string() != CRS:
            raise ValueError(f"Imagery CRS must be {CRS}; got {image_crs}")
        img_extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]
    img = np.moveaxis(image, 0, -1)
    # Stretch only for display; source raster remains unchanged.
    lo, hi = np.percentile(img, [2,98])
    if hi > lo:
        img = np.clip((img.astype(float)-lo)/(hi-lo),0,1)
    fig, ax = plt.subplots(figsize=(13,10))
    ax.imshow(img, extent=img_extent, origin="upper")
    roads.plot(ax=ax, color="cyan", linewidth=0.65, alpha=0.85, label="Existing TGRAC roads")
    facilities.plot(ax=ax, color="yellow", edgecolor="black", markersize=45, zorder=5, label="Reference facilities")
    if valid_geoms:
        route_gdf = gpd.GeoDataFrame(valid_geoms, geometry="geometry", crs=CRS)
        for _, row in route_gdf.iterrows():
            ax.plot(*row.geometry.xy, linewidth=1.8, alpha=0.9,
                    label=f"{row['facility_name']} alt {row['alternative']}")
    ax.set_title("Damarakunta: reconstructed access-route candidates\nNot construction-ready; inspect building/entrance conflicts")
    ax.set_xlabel("Easting (m, EPSG:32644)")
    ax.set_ylabel("Northing (m, EPSG:32644)")
    ax.legend(loc="best", fontsize=7)
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    fig.savefig(OUT_MAP, dpi=220, bbox_inches="tight")
    plt.close(fig)

    OUT_NOTE.write_text(
        "Damarakunta reconstructed route alternatives\n\n"
        "Outputs were generated from the existing raster cost surface, WorldCover, slope, road layer, "
        "and facility reference points. Existing input files were not modified.\n\n"
        "Important limitations:\n"
        "- WorldCover is 10 m and its built-up class is not a building-footprint dataset.\n"
        "- Individual house roofs and facility entrances are not verified by this script.\n"
        "- The alternatives are algorithmic candidates, not surveyed or construction-ready roads.\n"
        "- Facility coordinates are reference records, not field-verified locations.\n"
        "- Slope and land-cover inputs have their own resolution/classification limitations.\n"
        "- Inspect every route against the high-resolution imagery and authoritative facility records.\n",
        encoding="utf-8"
    )
    print("\nRECONSTRUCTION COMPLETE")
    print("Route comparison CSV:", OUT_CSV)
    print("Facility checks CSV:", OUT_FAC_CSV)
    print("Route alternatives GeoPackage:", OUT_GPKG if OUT_GPKG.exists() else "No line geometries written")
    print("Automatic map PNG:", OUT_MAP)
    print("Limitations note:", OUT_NOTE)
    print("\nThis is a candidate-generation and screening tool; do not treat its outputs as construction plans.")

if __name__ == "__main__":
    main()
