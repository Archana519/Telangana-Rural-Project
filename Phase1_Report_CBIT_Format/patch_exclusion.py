"""One-off patch (kept for provenance): switches the reporting tools to the 'noang' scenario family (anganwadi excluded; inputs/EXCLUSIONS.md)
and makes the building-avoiding network the final network on Maps 4 and 5."""
ROOT = r"D:\Telangana_Rural_Project"


def patch(rel, pairs, header=None):
    path = ROOT + "\\" + rel.replace("/", "\\")
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (rel, s.count(a), a[:90])
        s = s.replace(a, b)
    if header:
        k = s.index("\nimport ") if "\nimport " in s else 0
        s = s[:k] + header + s[k:]
    open(path, "w", encoding="utf-8").write(s)


IMP = "\nimport sys as _sys\nfrom pathlib import Path as _P\n_sys.path.insert(0, str(_P(__file__).resolve().parents[1]))\nimport scenario_names as SN\n"

# ---------------------------------------------------------------- comparison_tables
patch("src/reporting/comparison_tables.py", [
    ('    prim = {"x4 (primary)": "S2_fac_C0_s25_v11", "x1 (P3 control)": "S2_fac_C0_s25_P3_none"}', '    prim = {"x4 (primary)": SN.PRIMARY, "x1 (P3 control)": SN.P3}'),
    ('        if line is not None and rk == "S2_fac_C0_s25_v11":', '        if line is not None and rk == SN.PRIMARY:'),
    ('label = {"S2_fac_C0_s25_P3_none": "x1, no penalty (P3 control)", "S2_fac_C0_s25_v11": "x4, penalty on footprint cells (primary)"}', 'label = {SN.P3: "x1, no penalty (P3 control)", SN.PRIMARY: "x4, penalty on footprint cells (primary)"}'),
    ('method="Facilities (4), network-aware"', 'method="Facilities (%d), network-aware" % ev["n_facility_targets"]'),
    ('        if "_K1_" in name or "_K3_" in name:      # C2 ablation runs are not scenarios of this table\n            continue\n',
     '        if "_K1_" in name or "_K3_" in name or "noang" not in name:      # C2 ablation and 4-facility reference runs are not scenarios of this table\n            continue\n'),
    ('        if cfg.get("perturb", "none") == "none" and cfg["building_mult"] == 4.0 and cfg["slope_limit_deg"] == 25.0 and cfg["scenario"] == "S2" and cfg["cost_scenario"] == "C0":',
     '        if "noang" not in name and cfg.get("perturb", "none") == "none" and cfg["building_mult"] == 4.0 and cfg["slope_limit_deg"] == 25.0 and cfg["scenario"] == "S2" and cfg["cost_scenario"] == "C0":'),
], IMP)

# ---------------------------------------------------------------- economic_impact
patch("src/reporting/economic_impact.py", [
    ('Path(a.stageb_root) / "S2_fac_C0_s25_v11" / "evaluation_summary.json"', 'Path(a.stageb_root) / SN.PRIMARY / "evaluation_summary.json"'),
    ('"Combined with the 4 facility routes the unique saving is %.0f m (%.1f%%): %.0f m independent against %.0f m shared." % (dcomb,', '"Combined with the %d facility routes the unique saving is %.0f m (%.1f%%): %.0f m independent against %.0f m shared." % (ev["n_facility_targets"], dcomb,'),
    ('    (Path(a.out) / "economic_impact.md").write_text("\\n".join(md), encoding="utf-8")',
     '''    avp = Path(a.stageb_root) / SN.AVOID / "evaluation_summary.json"
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
        md += ["## Building-avoiding network (illustrative)", "", pd.DataFrame([rowc]).T.to_markdown(header=False),
               "", "The saving is against independent routes planned under the same buffer and penalty. The extra length is the price of keeping routes out of footprints compared with the x4 network.", ""]
    (Path(a.out) / "economic_impact.md").write_text("\\n".join(md), encoding="utf-8")'''),
], IMP)

# ---------------------------------------------------------------- make_charts
patch("src/reporting/make_charts.py", [
    ('    av = t6[t6.run == "S2_fac_C0_s25_avoid_buf100"]', '    av = t6[t6.run == SN.AVOID]'),
    ('    prim = sb / "S2_fac_C0_s25_v11"\n', '    prim = sb / SN.PRIMARY\n'),
    ('    fac = gpd.read_file(V / "reference" / "damarakunta_priority_facilities.gpkg")', '    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")'),
    ('("\\n(unverified)" if str(r.facility_id) == "1702300" else "") + ', ''),
    ('Facility counts are straight-line distances and inherit the facility-coordinate uncertainty (the anganwadi coordinate is unsupported by any footprint). Planning results, not field-verified.',
     'Facility counts are straight-line distances from the three retained facilities (the anganwadi was excluded, inputs/EXCLUSIONS.md). Planning results, not field-verified.'),
    ('    fig, ax = plt.subplots(1, 3, figsize=(13, 4.3), gridspec_kw=dict(width_ratios=[1.1, 0.9, 1.1]))', '    fig, ax = plt.subplots(1, 4, figsize=(16, 4.3), gridspec_kw=dict(width_ratios=[1.1, 0.9, 1.0, 1.0]))'),
    ('    fig.suptitle("Chart 3. Cost distribution at the assumed PMGSY-based rate (illustrative)", fontsize=11, fontweight="bold")',
     '''    cx4, cav = prop / 1000 * rate["central"], (avl / 1000 * rate["central"]) if np.isfinite(avl) else np.nan
    ax[3].bar(["Shared, x4", "Shared, building-\\navoiding (x100)"], [cx4, cav], color=[BLUE, GREEN], edgecolor="k", lw=0.5)
    for i_, v_ in enumerate([cx4, cav]):
        ax[3].text(i_, v_ + 8, "%.0f" % v_, ha="center", fontsize=8)
    ax[3].set_ylabel("Rs lakh at Rs %.0f lakh/km" % rate["central"]); ax[3].set_title("Price of keeping routes out of footprints")
    ax[3].text(0.5, max(cx4, cav) * 0.5, "+Rs %.0f lakh" % (cav - cx4), ha="center", color=RED, fontweight="bold", fontsize=9); ax[3].set_ylim(0, max(cx4, cav) * 1.2)
    fig.suptitle("Chart 3. Cost distribution at the assumed PMGSY-based rate (illustrative)", fontsize=11, fontweight="bold")'''),
], IMP)

# ---------------------------------------------------------------- make_final_maps
patch("src/reporting/make_final_maps.py", [
    ('    fac = gpd.read_file(V / "reference" / "damarakunta_priority_facilities.gpkg")', '    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")'),
    ('    zext = (min(fx) - 220, max(fx) + 220, min(fy) - 220, max(fy) + 220)          # main settlement: the four facilities plus 220 m',
     '    zext = (min(fx) - 330, max(fx) + 330, min(fy) - 300, max(fy) + 300)          # main settlement: the three retained facilities plus 300 m'),
    ('label="Priority facility (4)")', 'label="Priority facility (%d)" % len(fac))'),
    ('"HEALTH_8734223673": "Sub Centre Damarakunta", "1702300": "Anganwadi Damarakunt-I"}', '"HEALTH_8734223673": "Sub Centre Damarakunta"}'),
    (', "1702300": (22, -46)}', '}'),
    ('    OFF = {"36181600902": (-175, -48), "36181600903": (-235, 12), "HEALTH_8734223673": (-60, 64), "1702300": (22, -40)}', '    OFF = {"36181600902": (-175, -48), "36181600903": (-235, 12), "HEALTH_8734223673": (-60, 64)}'),
    ('                un = fid == "1702300"\n', '                un = False\n'),
    ('            lead = gob.assign(d=gob.geometry.distance(names["1702300"].geometry)).sort_values("d").iloc[0]\n            ax.scatter([lead.geometry.centroid.x], [lead.geometry.centroid.y], marker="D", s=70, facecolors="none", edgecolors="#00e5ff", linewidths=1.8, zorder=12)\n', ''),
    ('                               Line2D([], [], marker="*", color="w", mfc="#ffd600", mec="k", ms=13, label="Priority facility (model coordinate)"),\n                               Line2D([], [], marker="D", color="w", mfc="none", mec="#00e5ff", ms=8, label="Nearest Open Buildings polygon to the anganwadi (lead, unverified)")],',
     '                               Line2D([], [], marker="*", color="w", mfc="#ffd600", mec="k", ms=13, label="Priority facility (TGRAC coordinate)")],'),
    ('"The anganwadi coordinate is unverified and was NOT moved; the cyan diamond is only a lead for the visual audit. Footprints are automatic detections (not a census). Routes enter touching clusters only where a target starts among adjacent buildings. "',
     '"The anganwadi (unverified coordinate) is excluded from the planning layers and maps at the project owner\'s request (inputs/EXCLUSIONS.md); the plan serves the 3 retained facilities. Footprints are automatic detections (not a census). Routes enter touching clusters only where a target starts among adjacent buildings. "'),
    ('    net_h, net_f, alts = rg("routes_network_houses"), rg("routes_network_facilities"), rg("stageA_alternatives_houses")',
     '    _fr = Path(a.avoid_run_dir) if a.avoid_run_dir else run       # Map 4 shows the FINAL network: the building-avoiding scenario when given\n    rgf = lambda l: gpd.read_file(_fr / "routes.gpkg", layer=l)\n    net_h, net_f, alts = rgf("routes_network_houses"), rgf("routes_network_facilities"), rgf("stageA_alternatives_houses")'),
    ('fig.suptitle("Map 4. Alternative candidate routes versus the final shared network (%s)" % run.name, fontsize=10)',
     'fig.suptitle("Map 4. Alternative candidate routes versus the final shared network (%s)" % _fr.name, fontsize=10)'),
], IMP)

# ---------------------------------------------------------------- verify_detections
patch("src/validation/verify_detections.py", [
    ('    fac = gpd.read_file(V / "reference" / "damarakunta_priority_facilities.gpkg")', '    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")\n    fac_all = gpd.read_file(SN.FAC_LAYER_ORIGINAL, layer="priority_facilities")'),
    ('    ang = gpd.read_file(V / "reference" / "tgrac_anganwadi.gpkg")\n    attr_ll = {}\n    for r in ang.itertuples():\n        if str(getattr(r, "Anganwadi_Code", "")) == "1702300":\n            attr_ll["1702300"] = (getattr(r, "Latitude", np.nan), getattr(r, "Longitude", np.nan))\n', '    attr_ll = {}\n'),
    ('    F.to_csv(out / "facility_verification.csv", index=False)',
     '''    F.to_csv(out / "facility_verification.csv", index=False)
    # audit trail of the exclusion (inputs/EXCLUSIONS.md): the only place the excluded record is kept
    ex = fac_all[fac_all.facility_id.astype(str) == SN.EXCLUDED_FACILITY_ID].geometry.iloc[0]
    exll = gpd.GeoSeries([ex], crs=32644).to_crs(4326).iloc[0]
    pd.DataFrame([dict(facility_id=SN.EXCLUDED_FACILITY_ID, name="Damarakunt-I (anganwadi)", lat=round(exll.y, 6), lon=round(exll.x, 6),
                       nearest_footprint_m=round(float(ex.distance(bg[int(bt.nearest(ex))])), 1), nearest_open_buildings_m=round(float(ex.distance(gg[int(gt.nearest(ex))])), 1),
                       status="EXCLUDED from planning layers, CSVs and maps at the project owner's request; see inputs/EXCLUSIONS.md")]).to_csv(out / "excluded_facilities.csv", index=False)'''),
], IMP)

# ---------------------------------------------------------------- visual_audit_protocol
patch("src/validation/visual_audit_protocol.py", [
    ('    fac = gpd.read_file(V / "reference" / "damarakunta_priority_facilities.gpkg")', '    fac = gpd.read_file(SN.FAC_LAYER, layer="priority_facilities")'),
    ('        print(T.loc[T.facility_id == "1702300", "leads_to_inspect_open_buildings_within_200m"].iloc[0])\n', ''),
    ('    print(T.loc[T.facility_id == "1702300", "leads_to_inspect_open_buildings_within_200m"].iloc[0])\n', ''),
], IMP)

# ---------------------------------------------------------------- make_chapter (names and anganwadi text)
s = open(ROOT + r"\src\reporting\make_chapter.py", encoding="utf-8").read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('    ev = json.load(open(sb / "S2_fac_C0_s25_v11" / "evaluation_summary.json"))', '    ev = json.load(open(sb / SN.PRIMARY / "evaluation_summary.json"))')
rep('    ev3 = json.load(open(sb / "S2_fac_C0_s25_P3_none" / "evaluation_summary.json"))', '    ev3 = json.load(open(sb / SN.P3 / "evaluation_summary.json"))')
rep('"_route_explanations" / "S2_fac_C0_s25_v11" / "route_explanations.csv"', '"_route_explanations" / SN.PRIMARY / "route_explanations.csv"')
rep('    k4 = t6[t6.run == "S2_fac_C0_s25_v11"].iloc[0]', '    k4 = t6[t6.run == SN.PRIMARY].iloc[0]')
rep('    kb = t6[t6.run == "S2_fac_C0_s25_avoid_buf100"].iloc[0]', '    kb = t6[t6.run == SN.AVOID].iloc[0]')
rep('    A("Only schools, a health sub-centre and an anganwadi exist as priority facilities in the data (TGRAC layers). No government-building layer exists, so no such class is detected or prioritised.")',
    '    exf = pd.read_csv(ver / "excluded_facilities.csv").iloc[0]\n    A("The TGRAC layers hold four priority facilities: two schools, a health sub-centre and an anganwadi. The anganwadi was excluded from the planning layers, CSVs and maps at the project owner\'s request (`inputs/EXCLUSIONS.md`), so the deliverables cover three. No government-building layer exists, so no such class is detected or prioritised.")')
a = s.index('    A("**Finding.** %d of the 4 priority facilities')
b = s.index('    A("Building candidates inside the boundary against Google Open Buildings v3')
s = s[:a] + '''    A("**Finding.** All %d retained facilities are supported by a detected footprint and corroborated by an independent Open Buildings polygon. "
      "The anganwadi (Damarakunt-I) was excluded because its TGRAC coordinate lies %.0f m from the nearest detected footprint and %.0f m from the nearest Open Buildings polygon (record kept in `excluded_facilities.csv`); "
      "this does not show the anganwadi is absent from the village, only that its position is unsupported. Until a verified location exists the plan serves 3 of the 4 priority facilities. "
      "The sub-centre has two TGRAC records %.0f m apart; the position in the priority layer is the health-layer record, and both records are near a footprint, so proximity alone cannot say which is right." % (
          nsup, float(exf.nearest_footprint_m), float(exf.nearest_open_buildings_m), 235.7))
    A("")
''' + s[b:]
a = s.index('    A("A first look at the project\'s own Esri crop')
b = s.index('    A("## 4. Road connectivity and the C0002 exception")')
s = s[:a] + '    A("The excluded anganwadi is not part of this audit; its record and the reason are in `inputs/EXCLUSIONS.md`.")\n    A("")\n' + s[b:]
rep('"(ii) *Anganwadi correction:* no verified corrected location exists. The coordinate is flagged unsupported and was left unchanged; Map 5 marks the nearest Open Buildings polygon only as a lead for the visual audit. "',
    '"(ii) *Anganwadi:* excluded from the planning layers and maps at the project owner\'s request (`inputs/EXCLUSIONS.md`), not corrected; no verified location exists. "')
rep('anganwadi coordinate off; 163 targets', 'anganwadi excluded (unsupported coordinate); 163 targets')
rep('| Anganwadi flagged unsupported; open |', '| Anganwadi excluded; verified location still needed |')
k = s.index("\nimport ") if "\nimport " in s else 0
s = s[:k] + IMP + s[k:]
open(ROOT + r"\src\reporting\make_chapter.py", "w", encoding="utf-8").write(s)
print("patched")
