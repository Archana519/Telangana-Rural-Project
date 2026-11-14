"""Synthetic multi-village worlds for Levels 2-4 (fallback when real GP/Mandal/District data are not yet downloaded).

Everything is deterministic in `seed`, lives in the Siddipet UTM zone (EPSG:32644) and is clearly flagged
`synthetic` in every output. These worlds make the full Level 2 -> 4 pipeline executable and testable without
external data; they are NOT evidence about Siddipet.
"""
from __future__ import annotations

import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Point, box

from .hierarchical_router import (DistrictInputs, GPInputs, MandalInputs, Node, hamlet_hubs)
from .layers import SyntheticLayerProvider

CRS = "EPSG:32644"
ORIGIN = (258000.0, 1950000.0)           # south-west corner, near Damarakunta


def _roads(lines):
    return gpd.GeoDataFrame({"road_id": range(len(lines))}, geometry=lines, crs=CRS)


def _ensure_land(nodes, prov, step_m=200.0, max_steps=40):
    """Move any node that falls in water (WorldCover class 80) in 200 m steps until it is on land."""
    for n in nodes:
        for _ in range(max_steps):
            L = prov.layers((n.x - 45, n.y - 45, n.x + 45, n.y + 45), 30.0)
            if int(L.landcover[1, 1]) != 80:
                break
            n.y += step_m
    return nodes


def make_synthetic_gp(seed: int = 7, n_hamlets: int = 6, size_m: float = 4000.0, cfg: dict | None = None) -> GPInputs:
    """A GP of ~size_m x size_m: a main road, a branch, hamlets 150-900 m off the roads, house footprints, and three
    amenities (school, sub-centre, panchayat office) whose points sit on the edge of their own footprints."""
    rng = np.random.default_rng(seed)
    x0, y0 = ORIGIN
    bounds = (x0, y0, x0 + size_m, y0 + size_m)
    roads = _roads([
        LineString([(x0, y0 + 0.45 * size_m), (x0 + size_m, y0 + 0.5 * size_m)]),
        LineString([(x0 + 0.55 * size_m, y0 + 0.48 * size_m), (x0 + 0.6 * size_m, y0 + size_m)]),
    ])
    houses, foot, nodes_extra = [], [], []
    for h in range(n_hamlets):
        for _ in range(60):
            cx, cy = x0 + rng.uniform(0.1, 0.9) * size_m, y0 + rng.uniform(0.08, 0.92) * size_m
            if min(Point(cx, cy).distance(r) for r in roads.geometry) > 250.0:
                break
        k = int(rng.integers(6, 26))
        pts = np.column_stack([cx + rng.normal(0, 45, k), cy + rng.normal(0, 45, k)])
        houses.append(pts)
    houses = np.vstack(houses)
    prov = SyntheticLayerProvider(bounds, seed=seed, n_rivers=1, ford_every_m=2500.0, forest_threshold=0.7,
                                  max_slope_deg=14.0)
    lay = prov.layers(bounds, 10.0)                       # keep houses on land: drop any that fall in the river
    cols = np.clip(((houses[:, 0] - bounds[0]) / 10.0).astype(int), 0, lay.shape[1] - 1)
    rows = np.clip(((bounds[3] - houses[:, 1]) / 10.0).astype(int), 0, lay.shape[0] - 1)
    houses = houses[lay.landcover[rows, cols] != 80]
    for (hx, hy) in houses:
        foot.append(box(hx - 5, hy - 5, hx + 5, hy + 5))
    amenity_specs = [("SCHOOL1", "school", 0.30, 0.62), ("SUBCENTRE1", "healthcare", 0.55, 0.40),
                     ("GPOFFICE1", "panchayat_office", 0.52, 0.55)]
    facs = []
    for fid, kind, fx, fy in amenity_specs:
        px, py = x0 + fx * size_m, y0 + fy * size_m
        foot.append(box(px - 12, py - 9, px + 12, py + 9))           # amenity building
        facs.append(Node(fid, px + 12.0, py, 1.0, kind, exempt=True))  # point on the building's edge (as at Damarakunta)
    nodes = hamlet_hubs(houses, 150.0) + facs
    fp = gpd.GeoDataFrame({"b_id": range(len(foot))}, geometry=foot, crs=CRS)
    boundary = box(*bounds)
    _ensure_land(nodes, prov, step_m=60.0)
    gp = GPInputs("SYNTH_GP", roads, nodes, boundary, fp, prov, ["synthetic world (seeded)"])
    gp.houses_xy = houses                      # kept for the omission analysis of raw house targets
    return gp


def make_synthetic_mandal(seed: int = 11, n_gps: int = 9, size_m: float = 20000.0) -> MandalInputs:
    rng = np.random.default_rng(seed)
    x0, y0 = ORIGIN
    bounds = (x0, y0, x0 + size_m, y0 + size_m)
    spine = LineString([(x0, y0 + 0.5 * size_m), (x0 + 0.4 * size_m, y0 + 0.55 * size_m),
                        (x0 + size_m, y0 + 0.48 * size_m)])
    branch = LineString([(x0 + 0.4 * size_m, y0 + 0.55 * size_m), (x0 + 0.45 * size_m, y0 + size_m)])
    branch2 = LineString([(x0 + 0.7 * size_m, y0 + 0.5155 * size_m), (x0 + 0.78 * size_m, y0)])
    roads = _roads([spine, branch, branch2])
    nodes = []
    for g in range(n_gps):
        for _ in range(80):
            x, y = x0 + rng.uniform(0.06, 0.94) * size_m, y0 + rng.uniform(0.06, 0.94) * size_m
            if min(Point(x, y).distance(r) for r in roads.geometry) > 1500.0:
                break
        nodes.append(Node(f"GP_{g + 1:02d}", x, y, float(rng.integers(80, 400)), "gp_hub"))
    nodes += [Node("MANDAL_HQ", x0 + 0.42 * size_m, y0 + 0.56 * size_m, 30.0, "mandal_hq"),
              Node("PHC_1", x0 + 0.25 * size_m, y0 + 0.40 * size_m, 20.0, "phc"),
              Node("PHC_2", x0 + 0.80 * size_m, y0 + 0.70 * size_m, 20.0, "phc"),
              Node("MARKET_1", x0 + 0.62 * size_m, y0 + 0.35 * size_m, 10.0, "market")]
    prov = SyntheticLayerProvider(bounds, seed=seed, n_rivers=2, ford_every_m=5000.0, max_slope_deg=18.0)
    _ensure_land(nodes, prov)
    return MandalInputs("SYNTH_MANDAL", roads, nodes, bounds, prov, box(*bounds), ["synthetic world (seeded)"])


def make_synthetic_district(seed: int = 21, n_mandals: int = 12, size_m: float = 60000.0) -> DistrictInputs:
    rng = np.random.default_rng(seed)
    x0, y0 = ORIGIN
    bounds = (x0, y0, x0 + size_m, y0 + size_m)
    nh = LineString([(x0, y0 + 0.3 * size_m), (x0 + 0.5 * size_m, y0 + 0.5 * size_m), (x0 + size_m, y0 + 0.62 * size_m)])
    sh = LineString([(x0 + 0.5 * size_m, y0 + 0.5 * size_m), (x0 + 0.55 * size_m, y0 + size_m)])
    roads = _roads([nh, sh])
    nodes = [Node("DISTRICT_HQ", x0 + 0.5 * size_m, y0 + 0.5 * size_m, 100.0, "district_hq")]
    for m in range(n_mandals):
        x, y = x0 + rng.uniform(0.05, 0.95) * size_m, y0 + rng.uniform(0.05, 0.95) * size_m
        nodes.append(Node(f"MANDAL_{m + 1:02d}", x, y, float(rng.integers(20, 60)), "mandal_hq"))
    prov = SyntheticLayerProvider(bounds, seed=seed, n_rivers=3, ford_every_m=9000.0, max_slope_deg=20.0)
    _ensure_land(nodes, prov, step_m=500.0)
    return DistrictInputs("SYNTH_DISTRICT", roads, nodes, bounds, prov, box(*bounds), ["synthetic world (seeded)"])
