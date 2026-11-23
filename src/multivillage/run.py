"""Run the shared Phase 1 / Stage B workflow for ONE study area and write its deliverables.

    python -m src.multivillage.run --village adilabad_urban --steps acquire prepare extract
    python -m src.multivillage.run --village adilabad_urban --steps route          # parallel, ~1 h
    python -m src.multivillage.run --village adilabad_urban --steps report      # Adilabad only (its report text is Adilabad-specific); other villages: --variant segmentation, or the generic tables below

Steps (identical for every village):
  acquire   1. study-area boundary, existing roads, facilities, building footprints   -> data/villages/<id>/ (git-ignored, regenerable)
  prepare   2. land cover, DEM, slope on the 10 m grid; 4. cost surface
  extract   3. footprints -> house targets and verified facilities (open-footprint method; see the audit for why StrongDINOv2Seg is not run)
  route     5. Stage A/B planner (scripts/plan_network_v2.py), five strategies, penalty sweep, omission scenarios, target-definition sensitivity
  report    tables, maps, audit and the comparison with Damarakunta (src/multivillage/report.py)
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import pickle
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from src.multivillage import acquire as A, facilities as FAC, pipeline as PL, prepare as P
from src.multivillage.sources import Source, write_manifest

REPO = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE"
FOLDERS = {"adilabad_urban": "01_ADILABAD", "aswaraopeta": "02_ASWARAOPETA"}      # = `folder:` in each village config
CTX: dict = {}                              # shared with forked workers


def out_dir(cfg, variant: str | None = None) -> Path:
    d = OUT_ROOT / (FOLDERS[cfg["village"]["id"]] + (f"_{variant.upper()}" if variant else ""))
    (d / "figures").mkdir(parents=True, exist_ok=True)
    return d


# ------------------------------------------------------------------------------------------------ step 3: targets
def classify(b: gpd.GeoDataFrame, v: dict) -> gpd.GeoDataFrame:
    """Open footprints -> house candidates. Quality classes mirror the Stage B vocabulary but are heuristics on area / confidence, not verified."""
    b = b.copy()
    small, conf = v["min_house_area_m2"], v["min_conf"]
    b["quality_class"] = np.where(b.area_m2 < small, "SMALL_EXCLUDED", np.where(b.confidence < conf, "LOWCONF_EXCLUDED",
                          np.where(b.area_m2 > 300, "LARGE_POSSIBLE_MERGE", np.where((b.dataset != "OpenStreetMap") & (b.confidence < 0.75), "REVIEW", "PLAUSIBLE"))))
    return b


def split_targets(b: gpd.GeoDataFrame, roads_union, min_dist: float):
    h = b[~b.quality_class.isin(["SMALL_EXCLUDED", "LOWCONF_EXCLUDED"])].copy().reset_index(drop=True)
    h["hid"] = np.arange(1, len(h) + 1)
    h["dist_to_road_m"] = h.geometry.representative_point().distance(roads_union)
    return h, h[h.dist_to_road_m > min_dist].copy().reset_index(drop=True)


# ------------------------------------------------------------------------------------------------ step 5: jobs
def _world(mu, footprints, buffer_m=0.0):
    c = CTX
    return PL.World(c["cost"], c["transform"], c["shape"], c["roads"], [g.buffer(buffer_m) if buffer_m else g for g in footprints], mu)


def _targets(hids):
    """HOUSE phase only: Stage B plans facilities and houses in separate phases, so house metrics never include facility routes."""
    return PL.make_targets(CTX["houses"][CTX["houses"].hid.isin(hids)], None)


def _plan_metrics(world, targets, p, houses_all):
    P_ = PL.pn()
    res = P_.plan(world.grid, world.road_union, world.road_cells, targets, p, log=lambda *a: None)
    tmap = {t["id"]: t for t in targets}
    two = PL.metrics("two-stage", list(res["sel"].values()), tmap, len(targets), houses_all)
    ind = PL.metrics("independent", list(res["indep"].values()), tmap, len(targets), houses_all)
    rho = 100 * (ind["unique_len_m"] - two["unique_len_m"]) / ind["unique_len_m"] if ind["unique_len_m"] else float("nan")
    return res, two, ind, rho


def _init_worker(ctx):
    CTX.update(ctx)


def job(spec: dict) -> dict:
    t0 = time.time()
    c, p = CTX, CTX["p"]
    allf = list(c["houses_all"].geometry)
    kind = spec["kind"]
    if kind == "main":
        w = _world(c["mu"], allf)
        tg = _targets(set(c["gap"].hid))
        out = PL.run_all_strategies(w, tg, p, c["houses_all"])
        # ---- facility phase (Stage B: facilities are planned first, on their own, with the same planner and constraints)
        ftg = PL.make_targets(c["houses"].iloc[0:0], c["fac"])
        fres = PL.pn().plan(w.grid, w.road_union, w.road_cells, ftg, p, log=lambda *a: None)
        ftmap = {t["id"]: t for t in ftg}
        out["facility_rows"] = [PL.metrics("Facilities: independent", list(fres["indep"].values()), ftmap, len(ftg), c["houses_all"]),
                                PL.metrics("Facilities: two-stage", list(fres["sel"].values()), ftmap, len(ftg), c["houses_all"])]
        out["facility_fails"] = dict(fres["fails"])
        out["facility_geoms"] = [(r["target"], r["geom"], r["own_len_m"], r["cost"]) for r in fres["sel"].values()]
        out["combined_unique_len_m"] = round(PL.pn().unique_edge_metrics(list(out["two"]["sel"].values()) + list(fres["sel"].values()))["unique_len_m"], 1)
        two, ind = out["two"], out["two"]["indep"]
        out["geoms"] = dict(two=[(r["target"], r["geom"], r["own_len_m"], r["cost"]) for r in two["sel"].values()],
                            indep=[(r["target"], r["geom"], r["own_len_m"], r["cost"]) for r in ind.values()],
                            roads_only=[(r["target"], r["geom"], r["own_len_m"], r["cost"]) for r in out["roads_only"]["sel"].values()])
        out["fails"] = dict(two["fails"])
        out["targets"] = [dict(id=t["id"], kind=t["kind"], x=t["pt"].x, y=t["pt"].y, weight=t["weight"], name=t["name"], ftype=t["ftype"]) for t in tg]
        for k in ("two", "roads_only", "length_only"):
            out.pop(k)
        out["seconds_total"] = round(time.time() - t0, 1)
        return dict(spec=spec, out=out)
    if kind == "penalty":
        w = _world(spec["mu"], allf, spec["buffer_m"])
        tg = _targets(set(c["gap"].hid))
        res, two, ind, rho = _plan_metrics(w, tg, p, c["houses_all"])
        return dict(spec=spec, row=dict(penalty_mode=spec["mode"], mu=spec["mu"], targets=len(tg), routed=two["targets_routed"], unique_len_m=two["unique_len_m"],
                    independent_unique_len_m=ind["unique_len_m"], saving_vs_independent_pct=round(rho, 1), routes_crossing=two["routes_crossing"],
                    len_in_footprints_m=two["len_in_footprints_m"], failed=len(res["fails"])), seconds=round(time.time() - t0, 1))
    if kind == "omit":
        omit = set(spec["omit_hids"])
        keep = set(c["gap"].hid) - omit
        foot = [g for g, hid in zip(c["houses_all"].geometry, c["houses_all"].hid) if hid not in omit]       # omitted houses leave the penalty layer too
        w = _world(c["mu"], foot)
        tg = _targets(keep)
        res, two, ind, rho = _plan_metrics(w, tg, p, c["houses_all"])
        n_house_targets = len(keep)
        n0 = len(c["gap"])
        routed_houses = sum(1 for k in res["sel"] if str(k).startswith("H"))
        return dict(spec=spec, row=dict(scenario=spec["label"], group=spec["group"], house_targets=n_house_targets, routed_houses=routed_houses,
                    unserved_vs_all_gap_houses=n0 - routed_houses, coverage_pct=round(100 * routed_houses / n0, 1), unique_len_m=two["unique_len_m"],
                    saving_vs_independent_pct=round(rho, 1), routes_crossing=two["routes_crossing"]), seconds=round(time.time() - t0, 1))
    if kind == "def":
        h = c["houses_all"]
        gap = h[h.dist_to_road_m > spec["min_dist"]]
        w = _world(c["mu"], allf)
        tg = PL.make_targets(gap, None)
        res, two, ind, rho = _plan_metrics(w, tg, p, h)
        return dict(spec=spec, row=dict(min_dist_to_road_m=spec["min_dist"], house_targets=len(gap), routed=two["targets_routed"], unique_len_m=two["unique_len_m"],
                    independent_unique_len_m=ind["unique_len_m"], saving_vs_independent_pct=round(rho, 1), routes_crossing=two["routes_crossing"],
                    len_in_footprints_m=two["len_in_footprints_m"], failed=len(res["fails"]), unique_len_per_house_m=round(two["unique_len_m"] / max(len(gap), 1), 1)),
                    seconds=round(time.time() - t0, 1))
    raise ValueError(kind)


def make_jobs(cfg, gap: pd.DataFrame) -> list:
    S = cfg["sensitivity"]
    jobs = [dict(kind="def", min_dist=20.0), dict(kind="main")]                    # the 20 m definition is the slowest: start it first
    for mode, buf in (("centre-in-footprint", 0.0), ("buffered 7.1 m", 7.1)):
        for mu in S["penalties"]:
            if mu == cfg["planner"]["building_mult"] and buf == 0.0:
                continue                                                          # mu = 4 is the main run
            if buf and mu < 20:
                continue
            jobs.append(dict(kind="penalty", mode=mode, mu=mu, buffer_m=buf))
    n = len(gap)
    for f in S["omit_fractions"]:
        for s in S["omit_seeds"]:
            om = np.random.default_rng(s).choice(gap.hid.values, size=int(round(f * n)), replace=False)
            jobs.append(dict(kind="omit", label=f"omit {int(f * 100)}% (random, seed {s})", group=f"omit {int(f * 100)}% (random)", omit_hids=list(map(int, om))))
    for q in (10, 25):
        thr = np.percentile(gap.area_m2, q)
        jobs.append(dict(kind="omit", label=f"omit smallest {q}%", group=f"omit smallest {q}%", omit_hids=list(map(int, gap.hid[gap.area_m2 <= thr]))))
    jobs.append(dict(kind="def", min_dist=50.0))
    return jobs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", required=True)
    ap.add_argument("--steps", nargs="+", default=["acquire", "prepare", "extract", "route", "report"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--variant", default=None, choices=[None, "segmentation"], help="segmentation = footprints from StrongDINOv2Seg (needs --footprints); outputs go to <folder>_SEGMENTATION")
    ap.add_argument("--footprints", default=None, help="buildings_v8_*.gpkg written by scripts/extract_buildings_v8.py (layer 'buildings')")
    ap.add_argument("--mosaic", default=None, help="Esri 0.6 m mosaic GeoTIFF for the satellite overlay figures (report step, segmentation variant)")
    ap.add_argument("--from-cache", action="store_true", help="acquire: reuse data/villages/<id>/{boundary,roads,buildings,places_4km}.gpkg; only missing layers are queried from Overture")
    ap.add_argument("--skip-buildings", action="store_true", help="acquire: never run the slow Overture buildings query (segmentation variant only; implies --from-cache)")
    ap.add_argument("--limit-targets", type=int, default=None, help="DEBUG ONLY: keep the first N road-gap targets (code-path tests; never use for results)")
    ap.add_argument("--quick", action="store_true", help="route step: run only the main strategy comparison (skips the penalty / omission / target-definition sweeps)")
    a = ap.parse_args(argv)
    cfg = A.load_cfg(a.village)
    v = cfg["village"]
    if a.variant == "segmentation" and not a.footprints and any(x in a.steps for x in ("extract",)):
        ap.error("--variant segmentation needs --footprints")
    ddir, odir = A.data_dir(cfg), out_dir(cfg, a.variant)
    base_state = ddir / "state.pkl"
    state = ddir / (f"state_{a.variant}.pkl" if a.variant else "state.pkl")
    if a.variant and not state.exists():
        if not base_state.exists():
            ap.error("run the open-data acquire/prepare/extract steps first (state.pkl missing)")
        S = pickle.load(open(base_state, "rb"))           # boundary, roads, places, layers: identical to the open-data run
    else:
        S = pickle.load(open(state, "rb")) if state.exists() else {}
    if "acquire" in a.steps:
        cached = a.from_cache or a.skip_buildings
        if cached and (ddir / "boundary.gpkg").exists():
            cell, rec = A.cached_boundary(ddir)
        else:
            cell, rec = A.boundary(cfg)
        L = A.cached_layers(cfg, cell, ddir, a.skip_buildings) if cached else A.fetch_layers(cfg, cell)
        S.update(cell=cell, rec=rec, layers=L)
        for name, gdf in (("roads", L["roads"]), ("buildings", L["buildings"]), ("places_4km", L["places_4km"])):
            if cached and ((ddir / f"{name}.gpkg").exists() or (name == "buildings" and a.skip_buildings)):
                continue                                    # never overwrite a cached layer, never write the empty placeholder
            gdf.to_file(ddir / f"{name}.gpkg", driver="GPKG")
        if not (cached and (ddir / "boundary.gpkg").exists()):
            gpd.GeoDataFrame({"name": [v["name"]]}, geometry=[cell], crs=A.CRS_WORK).to_file(ddir / "boundary.gpkg", driver="GPKG")
        pickle.dump(S, open(state, "wb"))
    cell, rec, L = S["cell"], S["rec"], S["layers"]
    if "prepare" in a.steps or "extract" in a.steps or "route" in a.steps:
        prep = P.prepare_rasters(cfg, cell, ddir)
        cost, inside = P.cost_surface(cfg, prep, cell)
        S.update(prep_meta=dict(shape=prep["shape"], bounds=prep["bounds"], transform=tuple(prep["transform"]), sources=prep["sources"],
                                inside_cells=int(inside.sum()), blocked_inside=float(np.isnan(cost[inside]).mean())))
    if "extract" in a.steps:
        if a.variant == "segmentation":
            from src.multivillage import segmentation_variant as SV
            b = SV.load_footprints(a.footprints, cell, v)
        else:
            b = classify(L["buildings"], v)
        roads_u = L["roads"].geometry.intersection(cell).union_all()
        houses_all, gap = split_targets(b, roads_u, v["min_dist_to_road_m"])
        if a.limit_targets:
            gap = gap.iloc[: a.limit_targets].copy()
        excl = pd.read_csv(REPO / f"configs/multivillage/villages/{v['id']}_facility_exclusions.csv")
        fac_all = FAC.candidates(L["places_4km"], cell, b, excl)
        fac = fac_all[fac_all.status == "VERIFIED_USED"].reset_index(drop=True)
        fac = fac.assign(fid=range(1, len(fac) + 1), facility_type=fac.facility_type)
        lc = prep["landcover"]
        S.update(classified=b, houses_all=houses_all, gap=gap, fac_all=fac_all, fac=fac)
        pickle.dump(S, open(state, "wb"))
        print(f"houses {len(houses_all)}, gap houses (> {v['min_dist_to_road_m']} m from road) {len(gap)}, verified facilities {len(fac)}/{int(fac_all.inside_window.sum())} candidates in window")
    if "route" in a.steps:
        if a.variant == "segmentation" and not (S["classified"].dataset == "StrongDINOv2Seg").all():
            raise SystemExit("segmentation variant: targets are not from StrongDINOv2Seg footprints - run the 'extract' step with --footprints first")
        S["prep_arrays"] = dict()
        houses_all, gap, fac = S["houses_all"], S["gap"], S["fac"]
        CTX.update(cost=cost, transform=prep["transform"], shape=prep["shape"], roads=[g.intersection(cell) for g in L["roads"].geometry], houses_all=houses_all, gap=gap,
                   houses=houses_all, fac=fac.rename(columns={"name": "name"})[["fid", "name", "facility_type", "geometry"]], p=PL.planner_params(cfg), mu=cfg["planner"]["building_mult"])
        jobs = make_jobs(cfg, gap) if not a.quick else [dict(kind="main")]
        print(len(jobs), "jobs on", a.workers, "workers", flush=True)
        t0 = time.time()
        results = []
        if "fork" in mp.get_all_start_methods():
            pool = mp.get_context("fork").Pool(a.workers)                       # workers inherit CTX
        else:                                                                   # Windows: no fork -> pass CTX through an initializer
            pool = mp.get_context("spawn").Pool(a.workers, initializer=_init_worker, initargs=(CTX,))
        with pool:
            for r in pool.imap_unordered(job, jobs):
                results.append(r)
                print(f"  done {r['spec'].get('label') or r['spec'].get('mode') or r['spec']['kind']} {r['spec'].get('mu', '')} ({len(results)}/{len(jobs)}, {round(time.time() - t0)} s)", flush=True)
                S["results"] = results
                pickle.dump(S, open(state, "wb"))
        S["runtime_s"] = round(time.time() - t0, 1)
        pickle.dump(S, open(state, "wb"))
    if "report" in a.steps and (a.variant == "segmentation" or v["id"] != "adilabad_urban"):
        from src.multivillage import segmentation_variant as SV              # generic tables (Adilabad's open-footprint report is report.py, with Adilabad-specific text)
        res = S["results"]
        summ = SV.write_tables(S, res, odir, cfg, a.quick)
        print("tables written to", odir, "|", {k: summ[k] for k in ("gap_targets", "unique_len_two_stage_m", "saving_vs_independent_pct")})
        if a.mosaic and a.variant == "segmentation":
            main_out = next(r for r in res if r["spec"]["kind"] == "main")["out"]
            for p in SV.satellite_overlays(S, main_out, Path(a.mosaic), odir):
                print("  figure", p)
    print("steps done:", a.steps)


if __name__ == "__main__":
    main()
