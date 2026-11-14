"""Run the hierarchical routing levels (Level 2 GP, Level 3 Mandal, Level 4 District) and log metrics.

    python -m src.routing.run_hierarchy --levels 2 3 4 --data auto --out outputs/hierarchy

--data auto       use REAL inputs where the files named in configs/hierarchy_levels.yaml exist, else the SYNTHETIC world
--data real       real only (levels without inputs are skipped and reported)
--data synthetic  synthetic worlds for every level (executable anywhere; NOT evidence about Siddipet)
Every output carries provenance (data source, fallbacks used) so synthetic and real runs cannot be confused.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.evaluation.hierarchy_metrics import evaluate_level, write_hierarchy_summary  # noqa: E402
from src.routing import data_hooks as dh  # noqa: E402
from src.routing import synthetic_world as sw  # noqa: E402
from src.routing.hierarchical_router import (build_district_problem, build_gp_problem, build_mandal_problem,  # noqa: E402
                                              hamlet_hubs, load_config)


def gp_omit_fn(gp, cfg):
    """False negatives at GP level act on HOUSES: drop a fraction, re-aggregate the hamlets, keep the amenities."""
    eps = float(cfg["levels"]["gp"]["hamlet_eps_m"])
    fac = [n for n in gp.nodes if n.kind != "hamlet"]
    houses = np.asarray(gp.houses_xy, float)

    def fn(frac, seed):
        rng = np.random.default_rng(seed)
        k = int(round(frac * len(houses)))
        drop = set(rng.choice(len(houses), size=k, replace=False).tolist()) if k else set()
        keep = np.array([i for i in range(len(houses)) if i not in drop], dtype=int)
        return hamlet_hubs(houses[keep], eps) + fac, k
    return fn


def run(levels, data_mode, out_dir, cfg, log=print):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    crs = cfg["crs"]
    inv = dh.inventory(cfg)
    (out / "data_inventory.json").write_text(json.dumps(inv, indent=2), encoding="utf-8")
    log("data fallback plan: " + json.dumps(inv["_fallback"]))
    summaries = []
    for lvl in levels:
        t0 = time.time()
        lv_cfg = cfg["levels"][{2: "gp", 3: "mandal", 4: "district"}[lvl]]
        fr, sd = lv_cfg["omission_fractions"], lv_cfg["omission_seeds"]
        if lvl == 2:
            gp, rep = (dh.load_gp_real(cfg) if data_mode in ("auto", "real") else (None, {}))
            source = "real" if gp is not None else "synthetic"
            if gp is None:
                if data_mode == "real":
                    log("Level 2: real inputs missing -> skipped " + str(rep.get("missing")))
                    continue
                gp = sw.make_synthetic_gp()
            prob = build_gp_problem(gp, cfg)
            prov = dict(data_source=source, notes=prob.meta["notes"], layer_source=prob.meta["layer_source"],
                        resolution_m=prob.meta["resolution_m"])
            s = evaluate_level("gp", prob, gp.nodes, out, crs, fr, sd, prov, omit_fn=gp_omit_fn(gp, cfg))
        elif lvl == 3:
            m, rep = (dh.load_mandal_real(cfg) if data_mode in ("auto", "real") else (None, {}))
            source = "real" if m is not None else "synthetic"
            if m is None:
                if data_mode == "real":
                    log("Level 3: real inputs missing -> skipped")
                    continue
                m = sw.make_synthetic_mandal()
            prob = build_mandal_problem(m, cfg)
            prov = dict(data_source=source, notes=prob.meta["notes"], layer_source=prob.meta["layer_source"],
                        resolution_m=prob.meta["resolution_m"])
            s = evaluate_level("mandal", prob, m.nodes, out, crs, fr, sd, prov)
        else:
            d, rep = (dh.load_district_real(cfg) if data_mode in ("auto", "real") else (None, {}))
            source = "real" if d is not None else "synthetic"
            if d is None:
                if data_mode == "real":
                    log("Level 4: real inputs missing -> skipped")
                    continue
                d = sw.make_synthetic_district()
            prob = build_district_problem(d, cfg)
            prov = dict(data_source=source, notes=prob.notes, layer_source=type(d.provider).__name__,
                        coarse_resolution_m=prob.coarse_res, fine_resolution_m=prob.fine_res)
            s = evaluate_level("district", prob, d.nodes, out, crs, fr, sd, prov)
        s["runtime_s"] = round(time.time() - t0, 1)
        log(f"Level {lvl} [{source}] nodes={s['n_nodes']} routed={s['n_routed_shared']} "
            f"shared={s['shared_unique_length_m']:.0f} m independent={s['independent_unique_length_m']:.0f} m "
            f"saving={s['saving_vs_independent_unique_pct']:.1f}% ({s['runtime_s']} s)")
        summaries.append(s)
    if summaries:
        write_hierarchy_summary(out, summaries)
    return summaries


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", nargs="+", type=int, default=[2, 3, 4], choices=[2, 3, 4])
    ap.add_argument("--data", default="auto", choices=["auto", "real", "synthetic"])
    ap.add_argument("--out", default=str(REPO / "outputs" / "hierarchy"))
    ap.add_argument("--config", default=None)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    run(a.levels, a.data, a.out, cfg)


if __name__ == "__main__":
    main()
