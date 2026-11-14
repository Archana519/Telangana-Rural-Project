"""Footprint-penalty sensitivity sweep (decision U02): how the penalty mu trades network length against exposure
(route length passing through building footprints). Works on any grid RoutingProblem that carries footprints (Level 2).

    python -m src.evaluation.penalty_sweep --out docs/results/U02_penalty_sweep_gp.csv

Exposure ignores the first `start_exempt_m` of every route (the start point sits inside / next to its own footprint).
"""
from __future__ import annotations

import argparse
import copy
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from shapely.ops import unary_union  # noqa: E402

from src.routing import data_hooks as dh  # noqa: E402
from src.routing.hierarchical_router import build_gp_problem, load_config  # noqa: E402


def exposure(result, footprints, start_exempt_m=20.0):
    """(routes crossing footprints, route length inside footprints) outside the start-exempt radius."""
    fp = unary_union(list(footprints.geometry))
    n, total = 0, 0.0
    for r in result.routes.values():
        from shapely.geometry import Point
        start = Point(*r.geometry.coords[0])
        inside = r.geometry.difference(start.buffer(start_exempt_m)).intersection(fp).length
        if inside > 0.5:
            n += 1
        total += inside
    return n, total


def sweep(problem, footprints, mus=(1.0, 2.0, 4.0, 8.0, 20.0, 100.0), start_exempt_m=20.0):
    rows = []
    for mu in mus:
        p = copy.copy(problem)
        p.mu = float(mu)
        shared = p.solve(mode="shared")
        indep = p.solve(mode="independent")
        n, L = exposure(shared, footprints, start_exempt_m)
        rows.append(dict(mu=mu, shared_unique_length_m=round(shared.unique_length_m, 1),
                         independent_unique_length_m=round(indep.unique_length_m, 1),
                         saving_vs_independent_pct=round(100 * (indep.unique_length_m - shared.unique_length_m) / indep.unique_length_m, 2),
                         shared_unique_cost=round(shared.unique_cost, 1), routes_crossing_footprints=n,
                         length_in_footprints_m=round(L, 1), routed=len(shared.routes), failed=len(shared.failures)))
    base = rows[0]
    for r in rows:
        r["length_increase_vs_mu1_pct"] = round(100 * (r["shared_unique_length_m"] - base["shared_unique_length_m"]) / base["shared_unique_length_m"], 2)
        r["exposure_reduction_vs_mu1_pct"] = round(100 * (base["length_in_footprints_m"] - r["length_in_footprints_m"]) / base["length_in_footprints_m"], 2) \
            if base["length_in_footprints_m"] else 0.0
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "docs" / "results" / "U02_penalty_sweep_gp.csv"))
    a = ap.parse_args(argv)
    cfg = load_config()
    gp, rep = dh.load_gp_real(cfg)
    if gp is None:
        raise SystemExit(f"real Damarakunta inputs missing: {rep['missing']}")
    prob = build_gp_problem(gp, cfg)
    rows = sweep(prob, gp.footprints)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
