"""economic_impact.py - ILLUSTRATIVE cost and material estimate for the baseline versus the shared network.

This is a parametric calculation, not an engineering estimate. The project has no road width, cross-section, soil or rate data, so every rate and
thickness comes from inputs/economic_assumptions.json (assumptions, editable). The routes are planning alternatives on a 10 m grid, mostly short house
lanes (about 31 m per house); a rate quoted for PMGSY habitation-connectivity roads may not apply to them, and PMGSY funds roads to unconnected habitations,
not necessarily internal village lanes (to be checked with the programme guidelines).

Two baselines are reported and kept apart:
  A  independent routes counted by UNIQUE length (6,755 m): a shared grid edge would be built once, so this is the fair baseline. The saving is the figure to quote.
  B  independent routes counted by TOTAL length (10,048 m): every house route is counted in full, so edges shared by several houses are paid for several times.
     This double-counts and is shown only because it is how the routes are listed; it is NOT a construction saving.

usage: python src/reporting/economic_impact.py --stageb-root <.../stageB> --out outputs/final_comparison
"""
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
import scenario_names as SN

import argparse, json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def per_m(a):
    p = a["pavement"]
    lf = p["loose_to_compact_factor_aggregate"]
    return {
        "aggregate_loose_m3": (p["wbm_base_thickness_m"] + p["bituminous_surface_thickness_m"]) * p["carriageway_width_m"] * lf,
        "gsb_subbase_loose_m3": p["sub_base_gsb_thickness_m"] * p["carriageway_width_m"] * lf,
        "earthwork_m3": p["formation_width_m"] * p["earthwork_average_depth_m"],
        "bitumen_t": p["bitumen_kg_per_m2_total"] * p["carriageway_width_m"] / 1000.0,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stageb-root", required=True)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "final_comparison"))
    ap.add_argument("--assumptions", default=str(ROOT / "inputs" / "economic_assumptions.json"))
    a = ap.parse_args()
    A = json.load(open(a.assumptions, encoding="utf-8"))
    ev = json.load(open(Path(a.stageb_root) / SN.PRIMARY / "evaluation_summary.json", encoding="utf-8"))   # primary, building penalty x4
    ind, prop = ev["houses_independent_baseline"], ev["houses_primary"]
    L = {"proposed": prop["unique_len_m"], "A_independent_unique": ind["unique_len_m"], "B_independent_total": ind["total_len_m"]}
    q = per_m(A)
    rate = A["rate_lakh_per_km"]
    rows = []
    for basis, key in (("A (fair): independent routes, unique length", "A_independent_unique"), ("B (double-counted): independent routes, total length", "B_independent_total")):
        d = L[key] - L["proposed"]
        row = {"baseline_basis": basis, "baseline_len_m": round(L[key], 1), "proposed_len_m": round(L["proposed"], 1), "length_saving_m": round(d, 1),
               "length_saving_pct": round(100 * d / L[key], 1)}
        for nm, r in (("low", rate["low"]), ("central", rate["central"]), ("high", rate["high"])):
            row["cost_saving_%s_Rs_lakh" % nm] = round(d / 1000 * r, 1)
        row["baseline_cost_central_Rs_lakh"] = round(L[key] / 1000 * rate["central"], 1)
        row["proposed_cost_central_Rs_lakh"] = round(L["proposed"] / 1000 * rate["central"], 1)
        for k, v in q.items():
            row["saving_" + k] = round(d * v, 1)
        rows.append(row)
    T = pd.DataFrame(rows)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    T.to_csv(Path(a.out) / "table5_economic_material_impact.csv", index=False)

    # material quantities for each length (not only savings)
    mat = []
    for nm, key in (("Proposed shared network", "proposed"), ("Independent routes, unique length (A)", "A_independent_unique"), ("Independent routes, total length (B)", "B_independent_total")):
        mat.append({"length": nm, "length_m": round(L[key], 1), **{k: round(v * L[key], 1) for k, v in q.items()}, "cost_central_Rs_lakh": round(L[key] / 1000 * rate["central"], 1)})
    M = pd.DataFrame(mat)
    M.to_csv(Path(a.out) / "table5b_material_quantities.csv", index=False)

    comb_ind, comb_prop = ev["combined_independent_baseline"], ev["combined_primary"]
    dcomb = comb_ind["unique_len_m"] - comb_prop["unique_len_m"]
    md = ["# Economic and material impact (illustrative)", "",
          "**This is a parametric estimate from assumptions in `inputs/economic_assumptions.json`; it is not an engineering estimate and it is not field-validated.** "
          "Rate: Rs %.0f lakh/km (central, supplied by the project owner as a PMGSY-based figure and not verified; Rs %.0f and %.0f lakh/km shown for sensitivity). "
          "Section: %.2f m carriageway, %.0f mm sub-base, %.0f mm WBM, %.0f mm bituminous surface, formation %.1f m wide, %.2f m average earthwork depth, loose-to-compact factor %.2f, bitumen %.1f kg/m2. "
          "All of these are assumptions." % (rate["central"], rate["low"], rate["high"], A["pavement"]["carriageway_width_m"], 1000 * A["pavement"]["sub_base_gsb_thickness_m"],
                                              1000 * A["pavement"]["wbm_base_thickness_m"], 1000 * A["pavement"]["bituminous_surface_thickness_m"], A["pavement"]["formation_width_m"],
                                              A["pavement"]["earthwork_average_depth_m"], A["pavement"]["loose_to_compact_factor_aggregate"], A["pavement"]["bitumen_kg_per_m2_total"]), "",
          "## Savings, house routes only (primary x4 plan, 163 houses)", "", T.to_markdown(index=False), "",
          "## Quantities for each length", "", M.to_markdown(index=False), "",
          "Combined with the %d facility routes the unique saving is %.0f m (%.1f%%): %.0f m independent against %.0f m shared." % (ev["n_facility_targets"], dcomb, 100 * dcomb / comb_ind["unique_len_m"], comb_ind["unique_len_m"], comb_prop["unique_len_m"]), "",
          "Reading: the quotable saving is basis A. Basis B (%.0f m, %.2f km) subtracts the shared network from routes that count shared edges several times; a shared edge would be built once even without optimisation, so basis B overstates the saving by about %.1f times. "
          "Quantities scale linearly with length because a single cross-section is assumed. Earthwork, drainage, cross-drainage works, land and utilities are not modelled." % (L["B_independent_total"] - L["proposed"], (L["B_independent_total"] - L["proposed"]) / 1000, (L["B_independent_total"] - L["proposed"]) / (L["A_independent_unique"] - L["proposed"])), ""]
    avp = Path(a.stageb_root) / SN.AVOID / "evaluation_summary.json"
    if avp.exists():
        eva = json.load(open(avp, encoding="utf-8"))
        ia, pa = eva["houses_independent_baseline"]["unique_len_m"], eva["houses_primary"]["unique_len_m"]
        extra = pa - L["proposed"]
        rowc = {"scenario": "Building-avoiding network (buffer 7.1 m, penalty x100)", "independent_unique_len_same_config_m": round(ia, 1), "network_len_m": round(pa, 1),
                "length_saving_vs_independent_m": round(ia - pa, 1), "length_saving_vs_independent_pct": round(100 * (ia - pa) / ia, 1),
                "cost_saving_central_Rs_lakh": round((ia - pa) / 1000 * rate["central"], 1), "extra_length_vs_x4_network_m": round(extra, 1),
                "extra_cost_vs_x4_network_central_Rs_lakh": round(extra / 1000 * rate["central"], 1)}
        for k, v in q.items():
            rowc["extra_" + k + "_vs_x4"] = round(extra * v, 1)
        pd.DataFrame([rowc]).to_csv(Path(a.out) / "table5c_building_avoiding_network.csv", index=False)
        md += ["## Building-avoiding network (illustrative)", "", pd.DataFrame({"item": list(rowc), "value": list(rowc.values())}).to_markdown(index=False),
               "", "The saving is against independent routes planned under the same buffer and penalty. The extra length is the price of keeping routes out of footprints compared with the x4 network.", ""]
    (Path(a.out) / "economic_impact.md").write_text("\n".join(md), encoding="utf-8")
    print(T.T.to_string()); print(M.to_string(index=False))


if __name__ == "__main__":
    main()
