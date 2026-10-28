r"""Create a Damarakunta final-map REVIEW package and journal figures.

Reads the project's current GIS outputs only. It does NOT modify source data or existing plans.
It deliberately marks model-derived footprints/facilities as requiring validation: an overlay alone
cannot certify that a detected polygon is a real, correctly localized individual house.

Run on the user's Windows project environment:
  python D:\Telangana_Rural_Project\scripts\create_damarakunta_final_review_package_v1.py
"""
from pathlib import Path
import json, sys, math, textwrap
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
import fiona
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, FancyBboxPatch, FancyArrowPatch

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
PROJECT = Path(r"D:\Telangana_Rural_Project")
OUT = ROOT / "results" / "final_output_validation_v1"
CRS = "EPSG:32644"

P = {
    "buildings": ROOT / "results" / "v8_instances" / "buildings_v8_full.gpkg",
    "roads": ROOT / "reference" / "tgrac_road_network.gpkg",
    "facilities": ROOT / "reference" / "damarakunta_priority_facilities.gpkg",
    "boundary": ROOT / "study_area" / "damarakunta_boundary.gpkg",
    "background": ROOT / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif",
    "network_gpkg": ROOT / "results" / "individual_house_network_v1" / "individual_house_network_v1.gpkg",
    "network_summary": ROOT / "results" / "individual_house_network_v1" / "house_network_summary.json",
    "network_status": ROOT / "results" / "individual_house_network_v1" / "house_network_status.csv",
    "plausible_summary": ROOT / "results" / "individual_house_network_plausible_only_v1" / "house_network_summary.json",
    "plausible_status": ROOT / "results" / "individual_house_network_plausible_only_v1" / "house_network_status.csv",
    "school_compounds": ROOT / "reference" / "school_compounds_utm44n.gpkg",
}

QCOL = {"PLAUSIBLE": "#62d394", "REVIEW": "#ffbc42", "UNRESOLVED_MERGE": "#f05d5e", "UNKNOWN": "#b6a6ca"}
EXISTING = "#25bde8"
PROPOSED = "#ff3d71"
FAC_COL = {"SCHOOL": "#a78bfa", "HEALTH": "#ff7043", "GOVERNMENT": "#ffd166", "OTHER": "#f1f5f9"}


def stop(msg):
    print("ERROR:", msg)
    raise SystemExit(1)


def read_gdf(path, layer=None, required=True):
    path = Path(path)
    if not path.exists():
        if required: stop(f"Missing required input: {path}")
        return gpd.GeoDataFrame(geometry=[], crs=CRS)
    try:
        layers = fiona.listlayers(str(path))
        lyr = layer if layer else (layers[0] if layers else None)
        g = gpd.read_file(path, layer=lyr) if lyr else gpd.read_file(path)
        if g.crs is None: stop(f"No CRS defined: {path} (layer {lyr}); won't guess coordinates")
        return g.to_crs(CRS)
    except Exception as e:
        if required: stop(f"Could not read {path}: {e}")
        print(f"WARNING: optional layer skipped: {path}: {e}")
        return gpd.GeoDataFrame(geometry=[], crs=CRS)


def as_bool(v):
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def get_text(row, candidates, default=""):
    for c in candidates:
        if c in row.index and pd.notna(row[c]) and str(row[c]).strip() not in ("", "nan", "None"):
            return str(row[c]).strip()
    return default


def classify_facility(row):
    s = " ".join([get_text(row, [c]) for c in row.index if c.lower() in
                   {"facility_name", "facility_type", "priority_group", "name", "type", "category", "amenity", "building"}]).lower()
    if any(k in s for k in ("school", "zphs", "primary school", "high school", "educational")):
        return "SCHOOL"
    if any(k in s for k in ("hospital", "health", "clinic", "sub centre", "sub-centre", "phc", "anganwadi", "aganwadi")):
        return "HEALTH"
    if any(k in s for k in ("government", "govt", "panchayat", "mandal", "office", "public facility")):
        return "GOVERNMENT"
    return "OTHER"


def draw_facilities(ax, facilities, label=True, zorder=9):
    if facilities.empty: return
    for idx, row in facilities.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty: continue
        cat = classify_facility(row)
        pt = geom if geom.geom_type == "Point" else geom.representative_point()
        marker = {"SCHOOL": "*", "HEALTH": "P", "GOVERNMENT": "s", "OTHER": "D"}[cat]
        ax.scatter([pt.x], [pt.y], marker=marker, s=100 if cat != "OTHER" else 65,
                   c=FAC_COL[cat], edgecolors="black", linewidths=0.55, zorder=zorder)
        name = get_text(row, ["facility_name", "name", "facility_id", "id"], f"Facility {idx+1}")
        typ = get_text(row, ["facility_type", "priority_group", "type", "category"], cat.title())
        if label:
            lab = f"{name}\n[{typ}]"
            ax.annotate(lab, (pt.x, pt.y), xytext=(5, 5), textcoords="offset points", fontsize=6.2,
                        color="white", ha="left", va="bottom",
                        bbox=dict(boxstyle="round,pad=0.2", fc="#15212b", ec=FAC_COL[cat], alpha=0.88, lw=0.5), zorder=zorder+1)


def load_satellite(path, max_dim=3000):
    with rasterio.open(path) as src:
        if src.crs is None or src.crs.to_epsg() != 32644:
            stop(f"Satellite background CRS should be EPSG:32644; got {src.crs}")
        scale = min(1.0, max_dim / max(src.width, src.height))
        oh, ow = max(1, int(src.height * scale)), max(1, int(src.width * scale))
        count = min(3, src.count)
        arr = src.read(list(range(1, count+1)), out_shape=(count, oh, ow), resampling=Resampling.average)
        bounds = src.bounds
    if arr.shape[0] == 1: arr = np.repeat(arr, 3, axis=0)
    arr = np.moveaxis(arr[:3], 0, -1)
    if arr.dtype != np.uint8:
        finite = arr[np.isfinite(arr)]
        lo, hi = np.percentile(finite, [2, 98]) if finite.size else (0, 1)
        arr = np.clip((arr.astype(float)-lo)/max(float(hi-lo), 1e-9), 0, 1)
    return arr, bounds


def plot_background(ax, img, bounds):
    ax.imshow(img, extent=(bounds.left, bounds.right, bounds.bottom, bounds.top), origin="upper", zorder=0)


def add_legend(fig):
    handles = [
        Line2D([0],[0], color=EXISTING, lw=2.4, label="Existing TGRAC reference roads"),
        Line2D([0],[0], color=PROPOSED, lw=2.4, label="Proposed new/access routes (planning only)"),
        Patch(facecolor="none", edgecolor=QCOL["PLAUSIBLE"], lw=1.4, label="Building candidate: PLAUSIBLE"),
        Patch(facecolor="none", edgecolor=QCOL["REVIEW"], lw=1.4, label="Building candidate: REVIEW"),
        Patch(facecolor="none", edgecolor=QCOL["UNRESOLVED_MERGE"], lw=1.4, label="Built-up candidate: UNRESOLVED_MERGE"),
        Line2D([0],[0], marker="*", color="w", markerfacecolor=FAC_COL["SCHOOL"], markeredgecolor="black", markersize=10, label="School / education facility"),
        Line2D([0],[0], marker="P", color="w", markerfacecolor=FAC_COL["HEALTH"], markeredgecolor="black", markersize=8, label="Health facility"),
        Line2D([0],[0], marker="s", color="w", markerfacecolor=FAC_COL["GOVERNMENT"], markeredgecolor="black", markersize=7, label="Government / public facility"),
        Line2D([0],[0], color="#e879f9", lw=1.5, linestyle="--", label="School-compound reference boundary (if available)"),
        Line2D([0],[0], color="#111827", lw=2.4, label="Potential facility-linked footprint (verify visually)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=7.8, frameon=True,
               bbox_to_anchor=(0.5, 0.005), framealpha=0.96)


def save_map(path_stem, bounds, img, img_bounds, boundary, roads, bld, facilities, routes, meta, detail=False, school_comp=None, facility_links=None):
    fig, ax = plt.subplots(figsize=(15, 11 if not detail else 12))
    plot_background(ax, img, img_bounds)
    if boundary is not None and not boundary.is_empty:
        gpd.GeoSeries([boundary], crs=CRS).boundary.plot(ax=ax, color="white", linewidth=1.3, zorder=2)
    if not roads.empty:
        roads.plot(ax=ax, color=EXISTING, linewidth=1.1 if detail else 0.85, alpha=0.98, zorder=3)
    # Every in-boundary candidate footprint is drawn and quality-coded, not just routed targets.
    for q in ("PLAUSIBLE", "REVIEW", "UNRESOLVED_MERGE"):
        if "quality_class" in bld.columns:
            ss = bld[bld.quality_class.astype(str) == q]
        else: ss = bld.iloc[0:0]
        if not ss.empty:
            ss.boundary.plot(ax=ax, color=QCOL[q], linewidth=0.8 if detail else 0.55, alpha=0.98, zorder=5)
    # Plot selected network-aware connector geometries only; independent routes are the comparison baseline, not final proposal.
    if not routes.empty:
        routes.plot(ax=ax, color=PROPOSED, linewidth=1.6 if detail else 1.1, alpha=0.95, zorder=7)
    if school_comp is not None and not school_comp.empty:
        school_comp.boundary.plot(ax=ax, color="#e879f9", linewidth=1.5 if detail else 1.0,
                                  linestyle="--", alpha=0.95, zorder=8)
    if facility_links is not None and not facility_links.empty:
        # Highlight the model-derived candidate nearest to a listed facility; this is a candidate association, not confirmation.
        facility_links.boundary.plot(ax=ax, color="#ffffff", linewidth=2.0 if detail else 1.4, alpha=0.95, zorder=9)
        facility_links.boundary.plot(ax=ax, color="#111827", linewidth=0.65, alpha=1.0, zorder=9.2)
    draw_facilities(ax, facilities, label=True, zorder=10)
    ax.set_xlim(bounds[0], bounds[2]); ax.set_ylim(bounds[1], bounds[3]); ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Easting (m), EPSG:32644", fontsize=8); ax.set_ylabel("Northing (m), EPSG:32644", fontsize=8)
    ax.tick_params(labelsize=7); ax.grid(alpha=0.12, linewidth=0.3)
    label = "DETAIL REVIEW VIEW" if detail else "VILLAGE OVERVIEW"
    ax.set_title(f"Damarakunta Rural Access Planning — {label}\n"
                 f"{meta['route_count']} proposed route geometries | unique planned edge length {meta['network_unique_m']/1000:.2f} km | "
                 f"model cost score Σ(route_cost) = {meta['cost_score']:,.2f} (not ₹)", fontsize=13, fontweight="bold", pad=10)
    ax.text(0.01, 0.015,
            "REVIEW DRAFT — model-derived footprints/routes are NOT yet ground-truth verified. "
            "Financial construction cost (₹) is not estimated; required road-width/specification/unit-rate inputs are absent.",
            transform=ax.transAxes, fontsize=7.1, color="white", va="bottom",
            bbox=dict(boxstyle="round,pad=0.3", fc="#121a22", ec="white", alpha=0.88))
    add_legend(fig)
    fig.subplots_adjust(bottom=0.14, top=0.91, left=0.07, right=0.98)
    for ext, kwargs in (("png", {"dpi":600}), ("pdf", {"format":"pdf"})):
        fn = OUT / f"{path_stem}.{ext}"
        fig.savefig(fn, bbox_inches="tight", pad_inches=0.15, facecolor="white", **kwargs)
        print("Wrote:", fn)
    plt.close(fig)


def draw_flowchart():
    fig, ax = plt.subplots(figsize=(12, 13))
    ax.set_xlim(0, 12); ax.set_ylim(0, 13); ax.axis("off")
    def box(x,y,w,h,text,fc="#eef5ff",ec="#274c77",fs=9):
        p = FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.05,rounding_size=0.12",fc=fc,ec=ec,lw=1.4)
        ax.add_patch(p); ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,wrap=True)
    def arrow(a,b):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=13,lw=1.25,color="#44546a"))
    # Main end-to-end planning workflow.
    main_boxes = [
        (3.0,11.45,6.0,0.75,"Rural satellite imagery + village boundary", "#e0f2fe"),
        (3.0,10.25,6.0,0.75,"AI feature extraction: building footprints, road features, land cover", "#e0f2fe"),
        (3.0,9.05,6.0,0.75,"Feature QA: geometry, detection-quality labels, facility/source checks", "#fff1d6"),
        (3.0,7.85,6.0,0.75,"GIS alignment + cost surface + hard constraints\n(water / prohibited areas / slope threshold)", "#e8f5e9"),
        (3.0,6.65,6.0,0.75,"Targets + existing reference-road network\n(candidate footprints + named public facilities)", "#f3e8ff"),
        (3.0,5.45,6.0,0.75,"Stage A — Generate multiple feasible route alternatives", "#e0f2fe"),
        (3.0,4.25,6.0,0.75,"Stage B — Select routes using network-aware shared-edge credit", "#e0f2fe"),
        (3.0,3.05,6.0,0.75,"Evaluate against independent least-cost and straight-line baselines", "#f3e8ff"),
    ]
    for x,y,w,h,t,c in main_boxes: box(x,y,w,h,t,fc=c,fs=8.8)
    for i in range(len(main_boxes)-1):
        x,y,w,h,_,_=main_boxes[i]; nx,ny,nw,nh,_,_=main_boxes[i+1]
        arrow((x+w/2,y),(nx+nw/2,ny+nh))
    # Research contributions are experiments/evaluations, not extra software modules.
    box(0.35,1.15,3.55,1.0,"C1 — Segmentation-error\nperturbation + downstream\nroute-impact measurement",fc="#fff1d6",ec="#9a6700",fs=7.5)
    box(4.22,1.15,3.55,1.0,"C2 — Unique network length/cost,\nconnectivity + parameter-\nsensitivity evaluation",fc="#e8f5e9",ec="#2e7d32",fs=7.5)
    box(8.1,1.15,3.55,1.0,"C3 — Transfer evaluation\non additional suitable\nrural villages",fc="#fff1d6",ec="#9a6700",fs=7.5)
    arrow((6,3.05),(2.1,2.15)); arrow((6,3.05),(6,2.15)); arrow((6,3.05),(9.9,2.15))
    ax.text(6,0.55,"Outputs: satellite planning map • route-wise length/cost-score table • validation audit • journal figures",
            ha="center",fontsize=9.4,fontweight="bold")
    ax.set_title("Research Architecture — AI/GIS-Based Rural Village Infrastructure Planning",fontsize=14,fontweight="bold",pad=15)
    for ext, kw in (("png",{"dpi":600}),("pdf",{"format":"pdf"}),("svg",{"format":"svg"})):
        fn=OUT/f"journal_project_architecture_flowchart.{ext}"; fig.savefig(fn,bbox_inches="tight",pad_inches=0.15,facecolor="white",**kw); print("Wrote:",fn)
    plt.close(fig)

def draw_bar_figures(all_summary, plausible_summary, quality_counts, route_status):
    # Figure 1: comparable independent-vs-network unique edge length at each target set.
    groups = [
        ("All eligible candidates\n(n=163)", float(all_summary["unique_grid_edge_length_independent_m"]), float(all_summary["unique_grid_edge_length_network_aware_m"])),
        ("PLAUSIBLE-only subset\n(n=71)", float(plausible_summary["unique_grid_edge_length_independent_m"]), float(plausible_summary["unique_grid_edge_length_network_aware_m"])),
    ]
    fig, ax = plt.subplots(figsize=(9.5,5.6))
    x=np.arange(len(groups)); w=0.32
    base=[g[1]/1000 for g in groups]; nw=[g[2]/1000 for g in groups]
    b1=ax.bar(x-w/2,base,w,label="Independent routes — unique grid-edge length")
    b2=ax.bar(x+w/2,nw,w,label="Network-aware — unique grid-edge length")
    ax.bar_label(b1,fmt="%.2f km",padding=3,fontsize=8); ax.bar_label(b2,fmt="%.2f km",padding=3,fontsize=8)
    ax.set_xticks(x,[g[0] for g in groups]); ax.set_ylabel("Unique grid-edge length (km)")
    ax.set_title("Shared-network planning comparison — Damarakunta\nPreliminary model-derived candidates; not field-validated")
    ax.legend(fontsize=8); ax.grid(axis="y",alpha=0.25); fig.tight_layout()
    for ext,kw in (("png",{"dpi":600}),("pdf",{"format":"pdf"}),("svg",{"format":"svg"})):
        fn=OUT/f"journal_shared_network_length_comparison.{ext}"; fig.savefig(fn,bbox_inches="tight",pad_inches=0.12,facecolor="white",**kw); print("Wrote:",fn)
    plt.close(fig)
    # Figure 2: quality mix and transparency about unresolved footprints.
    labels=["PLAUSIBLE","REVIEW","UNRESOLVED_MERGE"]
    vals=[int(quality_counts.get(k,0)) for k in labels]
    fig, ax=plt.subplots(figsize=(8.8,5.2))
    bars=ax.bar(labels,vals,color=[QCOL[k] for k in labels])
    ax.bar_label(bars,padding=3,fontsize=10)
    ax.set_ylabel("Building-candidate polygons (count)")
    ax.set_title("Detection-quality composition of routed targets (n=163)\nQuality classes indicate model confidence/review status, not confirmed house identity")
    ax.grid(axis="y",alpha=0.25); fig.tight_layout()
    for ext,kw in (("png",{"dpi":600}),("pdf",{"format":"pdf"}),("svg",{"format":"svg"})):
        fn=OUT/f"journal_building_quality_distribution.{ext}"; fig.savefig(fn,bbox_inches="tight",pad_inches=0.12,facecolor="white",**kw); print("Wrote:",fn)
    plt.close(fig)


def main():
    if OUT.exists() and any(OUT.iterdir()):
        stop(f"Output folder already contains files; choose a new output folder or move it first: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    for k in ("buildings","roads","facilities","background","network_gpkg","network_summary","network_status","plausible_summary","plausible_status"):
        if not P[k].exists(): stop(f"Required input missing ({k}): {P[k]}")

    print("Reading project data; source files remain read-only...")
    bld_all=read_gdf(P["buildings"],"buildings")
    if "inside_village" in bld_all.columns:
        bld=bld_all[bld_all.inside_village.map(as_bool)].copy()
    else:
        boundary_gdf=read_gdf(P["boundary"],required=False)
        bu=boundary_gdf.geometry.union_all() if not boundary_gdf.empty else None
        bld=bld_all[bld_all.geometry.intersects(bu)].copy() if bu is not None else bld_all.copy()
    bld=bld[bld.geometry.notna() & ~bld.geometry.is_empty].copy()
    bld["geometry_valid"] = bld.geometry.is_valid
    bld["quality_class"] = bld.get("quality_class", pd.Series("UNKNOWN",index=bld.index)).fillna("UNKNOWN").astype(str)
    bld["area_calc_m2"] = bld.geometry.area
    if "cand_id" not in bld.columns: bld["cand_id"] = bld.index.astype(str)

    roads=read_gdf(P["roads"])
    facilities=read_gdf(P["facilities"], "priority_facilities", required=False)
    if facilities.empty:
        facilities=read_gdf(P["facilities"],required=True)
    boundary_gdf=read_gdf(P["boundary"],required=False)
    boundary=boundary_gdf.geometry.union_all() if not boundary_gdf.empty else None
    school_comp=read_gdf(P["school_compounds"], required=False)
    if school_comp.empty and P["school_compounds"].exists(): school_comp=read_gdf(P["school_compounds"],required=False)

    gpkg_layers=fiona.listlayers(str(P["network_gpkg"]))
    if "routes_network_aware" not in gpkg_layers or "house_target_status" not in gpkg_layers:
        stop(f"Network GPKG missing required layers; found {gpkg_layers}")
    routes=read_gdf(P["network_gpkg"],"routes_network_aware")
    targets=read_gdf(P["network_gpkg"],"house_target_status")
    independent=read_gdf(P["network_gpkg"],"routes_independent",required=False)
    with open(P["network_summary"],encoding="utf-8") as f: summ=json.load(f)
    with open(P["plausible_summary"],encoding="utf-8") as f: psumm=json.load(f)
    status=pd.read_csv(P["network_status"],dtype={"cand_id":str})
    pstatus=pd.read_csv(P["plausible_status"],dtype={"cand_id":str})

    # Spatial/attribute QA—not ground-truth certification.
    bu=boundary if boundary is not None else (bld.geometry.union_all().convex_hull if not bld.empty else None)
    if bu is not None:
        bld["inside_boundary_geometry_check"] = bld.geometry.apply(lambda g: bool(bu.covers(g.representative_point())) if g and not g.is_empty else False)
    else: bld["inside_boundary_geometry_check"] = pd.NA
    review_cols=[c for c in ["cand_id","bld_id","quality_class","status","area_m2","area_calc_m2","mean_prob","max_prob","inside_village","geometry_valid","inside_boundary_geometry_check"] if c in bld.columns]
    review=bld[review_cols].copy()
    review["visual_review_status"]="NOT_YET_VISUALLY_VERIFIED"
    review["review_instruction"]="Compare footprint outline with satellite roof; mark CONFIRMED / FALSE_POSITIVE / MERGED / SPLIT / UNCLEAR in a copy of this table. Do not treat model quality class as ground truth."
    review.to_csv(OUT/"building_footprint_verification_checklist.csv",index=False)

    # Facility audit with source labels preserved. This checks geometry and proximity only; does not assert semantic truth.
    facility_links = gpd.GeoDataFrame(geometry=[], crs=CRS)
    if not facilities.empty:
        facilities["facility_category_map"] = facilities.apply(classify_facility,axis=1)
        facilities["geometry_valid"] = facilities.geometry.is_valid
        facilities["facility_name_map"] = facilities.apply(lambda r:get_text(r,["facility_name","name","facility_id","id"],"UNNAMED FACILITY"),axis=1)
        facilities["facility_type_map"] = facilities.apply(lambda r:get_text(r,["facility_type","priority_group","type","category"],"TYPE NOT PROVIDED"),axis=1)
        if not bld.empty:
            nearest_ids=[]; nearest_dist=[]; nearest_quality=[]; linked_geoms=[]
            for _, fr in facilities.iterrows():
                ds=bld.geometry.distance(fr.geometry)
                ix=ds.idxmin()
                nearest_ids.append(str(bld.loc[ix,"cand_id"]))
                nearest_dist.append(float(ds.loc[ix]))
                nearest_quality.append(str(bld.loc[ix,"quality_class"]))
                linked_geoms.append(bld.loc[ix].geometry)
            facilities["nearest_candidate_id"] = nearest_ids
            facilities["nearest_candidate_quality"] = nearest_quality
            facilities["nearest_candidate_footprint_m"] = nearest_dist
            facilities["potential_footprint_association"] = np.where(facilities["nearest_candidate_footprint_m"] <= 30,
                "POTENTIAL_LINK_WITHIN_30M_REQUIRES_VISUAL_CONFIRMATION", "NO_CANDIDATE_WITHIN_30M_REQUIRES_REVIEW")
            facility_links = gpd.GeoDataFrame({
                "facility_name": facilities["facility_name_map"].astype(str).to_list(),
                "facility_type": facilities["facility_type_map"].astype(str).to_list(),
                "facility_category": facilities["facility_category_map"].astype(str).to_list(),
                "candidate_id": facilities["nearest_candidate_id"].to_list(),
                "distance_m": facilities["nearest_candidate_footprint_m"].to_list(),
                "association_status": facilities["potential_footprint_association"].to_list(),
                "geometry": linked_geoms
            }, geometry="geometry", crs=CRS)
            facility_links.to_file(OUT/"potential_facility_linked_footprints.gpkg",layer="potential_links",driver="GPKG")
        else:
            facilities["nearest_candidate_id"] = ""
            facilities["nearest_candidate_quality"] = ""
            facilities["nearest_candidate_footprint_m"] = np.nan
            facilities["potential_footprint_association"] = "NO_BUILDING_CANDIDATES"
        facilities["location_semantics_status"]="SOURCE_LAYER_LOCATION_NOT_INDEPENDENTLY_VERIFIED"
        facilities[[c for c in facilities.columns if c!="geometry"]].to_csv(OUT/"public_facility_verification_checklist.csv",index=False)
    else:
        facilities=pd.DataFrame(columns=["geometry"])
        (OUT/"public_facility_verification_checklist.csv").write_text("No facility features were read; check source layer/path.\n",encoding="utf-8")

    # Route-by-route schedule: output IDs and cost score. This is NOT rupees.
    route_status = status.copy()
    if "house_route_id" not in route_status.columns and "target" in route_status.columns: route_status=route_status.rename(columns={"target":"house_route_id"})
    keep=[c for c in ["house_route_id","cand_id","bld_id","quality_class","network_status","network_attach_to","network_route_length_m","network_route_cost","network_endpoint_dist_m","nearest_road_gap_m","network_failure_reason","independent_route_length_m","independent_route_cost","interpretation"] if c in route_status.columns]
    routes_table=route_status[keep].copy()
    routes_table["financial_cost_INR"] = pd.NA
    routes_table["cost_note"]="network_route_cost is a raster-based model cost score, not currency. INR estimate needs validated road width/specification and unit rates."
    routes_table.to_csv(OUT/"proposed_route_length_and_cost_schedule.csv",index=False)

    # Build map bounding boxes.
    if boundary is not None and not boundary.is_empty: xmin,ymin,xmax,ymax=boundary.bounds
    else:
        bounds=np.vstack([bld.total_bounds,roads.total_bounds,routes.total_bounds]); xmin,ymin=np.nanmin(bounds[:,0]),np.nanmin(bounds[:,1]); xmax,ymax=np.nanmax(bounds[:,2]),np.nanmax(bounds[:,3])
    padx=max((xmax-xmin)*0.045,35); pady=max((ymax-ymin)*0.045,35)
    full=(xmin-padx,ymin-pady,xmax+padx,ymax+pady)
    img,img_bounds=load_satellite(P["background"])
    # cost score from route table; route costs may be null.
    costcol=pd.to_numeric(route_status.get("network_route_cost",pd.Series(dtype=float)),errors="coerce")
    cost_score=float(costcol.sum(skipna=True)) if len(costcol) else 0.0
    meta={"route_count":len(routes),"network_unique_m":float(summ.get("unique_grid_edge_length_network_aware_m",routes.geometry.length.sum())),"cost_score":cost_score}
    save_map("final_review_satellite_overview",full,img,img_bounds,boundary,roads,bld,facilities,routes,meta,detail=False,school_comp=school_comp,facility_links=facility_links)
    # Focus on route/building extent; keep same aspect with a bounded scale.
    bb=routes.total_bounds
    cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2
    hx=min(max((bb[2]-bb[0])*0.4,250),900); hy=min(max((bb[3]-bb[1])*0.4,250),900)
    focus=(cx-hx,cy-hy,cx+hx,cy+hy)
    save_map("final_review_satellite_detail",focus,img,img_bounds,boundary,roads,bld,facilities,routes,meta,detail=True,school_comp=school_comp,facility_links=facility_links)

    # Source/facility compound layer overlay as a separate optional layer export for checking in GIS.
    # Candidate polygons and route lines are not written into source GPKGs.
    if not school_comp.empty:
        school_comp.to_file(OUT/"school_compounds_for_review.gpkg",layer="school_compounds",driver="GPKG")

    # Flowchart and journal diagrams.
    draw_flowchart()
    # Quality distribution in the bar chart must match the 163 routed targets, not all 165 footprints.
    qc=status["quality_class"].astype(str).value_counts().to_dict() if "quality_class" in status.columns else {}
    draw_bar_figures(summ,psumm,qc,status)

    # Automated integrity report.
    missing_route_ids=sorted(set(targets.get("house_route_id",pd.Series(dtype=str)).astype(str))-set(routes.get("house_route_id",pd.Series(dtype=str)).astype(str)))
    duplicated_routes=int(routes.house_route_id.duplicated().sum()) if "house_route_id" in routes.columns else -1
    report={
        "package_status":"REVIEW_DRAFT_NOT_FINAL_VERIFIED",
        "project_area":"Damarakunta, Siddipet, Telangana",
        "crs_expected":"EPSG:32644",
        "building_candidates_inside_village":int(len(bld)),
        "candidate_quality_counts":{str(k):int(v) for k,v in qc.items()},
        "invalid_footprint_geometries":int((~bld.geometry.is_valid).sum()),
        "footprint_points_outside_boundary_check":int((~bld.inside_boundary_geometry_check.fillna(False)).sum()),
        "facility_feature_count":int(len(facilities)) if hasattr(facilities,"geometry") else 0,
        "facility_category_counts":({str(k):int(v) for k,v in facilities["facility_category_map"].value_counts().items()} if hasattr(facilities,"columns") and "facility_category_map" in facilities.columns else {}),
        "facility_source_layer_semantics":"NOT independently verified; source data and imagery overlay need review",
        "routes_count":int(len(routes)),
        "route_features_missing_for_target_ids":missing_route_ids,
        "duplicated_route_id_records":duplicated_routes,
        "route_length_sum_m":float(pd.to_numeric(route_status.get("network_route_length_m",pd.Series(dtype=float)),errors="coerce").sum()),
        "unique_network_edge_length_m":meta["network_unique_m"],
        "sum_route_cost_score_model_units_not_INR":cost_score,
        "financial_construction_cost_inr":None,
        "financial_cost_reason":"No verified road-width, road-surface/design specification, quantity schedule, or unit rates were supplied.",
        "geometry_correctness_caveat":"Geometry validity, boundary and proximity checks are not semantic ground truth. Review footprints against high-resolution imagery and authoritative facility records before calling them confirmed.",
        "manual_validation_required":True,
        "validation_checklist":"building_footprint_verification_checklist.csv and public_facility_verification_checklist.csv"
    }
    (OUT/"final_output_automated_audit.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    with open(OUT/"README_review_before_final.txt","w",encoding="utf-8") as f:
        f.write("DAMARAKUNTA FINAL OUTPUT PACKAGE — REVIEW DRAFT\n\n")
        f.write("Color legend: existing TGRAC roads=cyan/blue; proposed network-aware access routes=magenta; candidate footprint outlines: green PLAUSIBLE, orange REVIEW, red UNRESOLVED_MERGE. Facility marker types are shown in the map legend and label their source-layer name/type.\n\n")
        f.write("Outputs include overview/detail satellite maps (PNG/PDF), workflow architecture (PNG/PDF/SVG), shared-network comparison bars (PNG/PDF/SVG), candidate-quality bars (PNG/PDF/SVG), route-level length/cost-score table, building verification checklist, facility verification checklist, and automated integrity report.\n\n")
        f.write("IMPORTANT: The output is NOT yet final/ground-truth verified. Model predictions and source facilities must be visually checked against imagery and/or authoritative records. Facility categories are keyword-based labels from supplied source attributes. Per-route raster cost is a model cost score, not Indian Rupees. Financial cost cannot be estimated responsibly without route width, construction specification and local unit rates.\n")
    print("\n=== FINAL OUTPUT REVIEW PACKAGE ===")
    print(json.dumps(report,indent=2,default=str))
    print("\nOutput folder:",OUT)
    print("Review these files first: final_review_satellite_overview.png; final_review_satellite_detail.png; building_footprint_verification_checklist.csv; public_facility_verification_checklist.csv; proposed_route_length_and_cost_schedule.csv; final_output_automated_audit.json")

if __name__ == "__main__":
    main()
