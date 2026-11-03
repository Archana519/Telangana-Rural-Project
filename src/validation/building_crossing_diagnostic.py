"""building_crossing_diagnostic.py - where do routes still cross other buildings' footprints? (read-only)

For each Stage B run folder given, every house route is intersected with the detected footprints OTHER than the route's own building, and the
position of each crossing along the route (metres from the start point, which lies inside the target's own footprint) is recorded.
A crossing in the first few metres is the exit from a cluster of touching buildings; one further along is a real detour decision.

Outputs: building_crossings_by_route.csv (one row per crossing route per run) and building_crossings_summary.csv (one row per run).
usage: python src/validation/building_crossing_diagnostic.py --runs <run folder> [<run folder> ...] --out outputs/final_comparison
"""
import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "Siddipet" / "Damarakunta"
EXIT_M = 20.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "final_comparison"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    b = gpd.read_file(V / "results" / "v8_instances" / "buildings_v8_full.gpkg", layer="buildings")
    rows, summ = [], []
    for rd in map(Path, a.runs):
        r = gpd.read_file(rd / "routes.gpkg", layer="routes_network_houses")
        n_cross, cross_len, n_exit, n_later = 0, 0.0, 0, 0
        for x in r.itertuples():
            cid = int(float(x.cand_id))
            g = x.geometry
            inter = g.intersection(b[b.cand_id != cid].geometry.unary_union)
            if inter.length <= 0.01:
                continue
            parts = [p for p in (list(inter.geoms) if hasattr(inter, "geoms") else [inter]) if p.length > 0]
            pos = [g.project(p.interpolate(0.5, normalized=True)) for p in parts]
            n_cross += 1
            cross_len += inter.length
            exit_only = max(pos) <= EXIT_M
            n_exit += int(exit_only); n_later += int(not exit_only)
            rows.append(dict(run=rd.name, target_id=x.target_id, quality_class=x.quality_class, route_len_m=round(g.length, 1), crossing_len_m=round(inter.length, 1),
                             first_crossing_at_m=round(min(pos), 1), last_crossing_at_m=round(max(pos), 1), only_within_first_20m=exit_only))
        summ.append(dict(run=rd.name, house_routes=len(r), routes_crossing_other_footprints=n_cross, crossing_len_m=round(cross_len, 1),
                         crossing_only_in_first_20m=n_exit, crossing_beyond_first_20m=n_later))
    pd.DataFrame(rows).to_csv(out / "building_crossings_by_route.csv", index=False)
    S = pd.DataFrame(summ)
    S.to_csv(out / "building_crossings_summary.csv", index=False)
    print(S.to_string(index=False))


if __name__ == "__main__":
    main()
