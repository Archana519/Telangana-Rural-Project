r"""Create a cleaner, route-atlas Damarakunta review package (v4.0).

- Reads source GIS files only; writes to a new results folder.
- Crops the satellite raster independently for the overview and each detail tile to avoid
  zooming a globally downsampled image.
- Generates per-house route ID labels and a route-wise length/model-cost table in a multi-page atlas.
- Explicitly distinguishes source-layer facility locations from independently verified locations.
- Marks building candidates as unverified; it cannot certify semantic truth from geometry checks alone.

Run in the user's Windows project environment:
  python D:\Telangana_Rural_Project\scripts\Damarakunta_Final_Map_v4.py
"""
from pathlib import Path
import json, sys, math, textwrap, re
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds, Window, bounds as window_bounds
import fiona
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import box
from matplotlib.backends.backend_pdf import PdfPages
from pyproj import Transformer

ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
OUT = ROOT / "results" / "final_output_validation_v4"
CRS = "EPSG:32644"
WGS84 = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
P = {
    "buildings": ROOT / "results" / "v8_instances" / "buildings_v8_full.gpkg",
    "roads": ROOT / "reference" / "tgrac_road_network.gpkg",
    "facilities": ROOT / "reference" / "damarakunta_priority_facilities.gpkg",
    "boundary": ROOT / "study_area" / "damarakunta_boundary.gpkg",
    "background": ROOT / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif",
    "network_gpkg": ROOT / "results" / "individual_house_network_v1" / "individual_house_network_v1.gpkg",
    "network_summary": ROOT / "results" / "individual_house_network_v1" / "house_network_summary.json",
    "network_status": ROOT / "results" / "individual_house_network_v1" / "house_network_status.csv",
}
QCOL = {"PLAUSIBLE":"#28d17c", "REVIEW":"#ffb020", "UNRESOLVED_MERGE":"#ff5864", "UNKNOWN":"#d0b5ef"}
EXISTING = "#22c8f2"
PROPOSED = "#ff2e79"
CONTEXT = "#d7e0e7"
FAC_COL = {"SCHOOL":"#b69cff", "HEALTH":"#ff784f", "ANGANWADI":"#ffb000", "GOVERNMENT":"#ffe066", "OTHER":"#ffffff"}


def stop(msg):
    print("ERROR:", msg); raise SystemExit(1)


def read_gdf(path, layer=None, required=True):
    path = Path(path)
    if not path.exists():
        if required: stop(f"Missing input: {path}")
        return gpd.GeoDataFrame(geometry=[], crs=CRS)
    try:
        layers=fiona.listlayers(str(path)); lyr=layer if layer else (layers[0] if layers else None)
        g=gpd.read_file(path, layer=lyr) if lyr else gpd.read_file(path)
        if g.crs is None: stop(f"No CRS in {path} layer={lyr}; refusing to guess")
        return g.to_crs(CRS)
    except Exception as e:
        if required: stop(f"Cannot read {path} layer={layer}: {e}")
        print(f"WARNING optional data skipped: {path}: {e}")
        return gpd.GeoDataFrame(geometry=[], crs=CRS)


def truth(v): return str(v).strip().lower() in {"true","1","yes","y"}

def txt(row, names, default=""):
    for c in names:
        if c in row.index and pd.notna(row[c]):
            s=str(row[c]).strip()
            if s and s.lower() not in {"nan","none","null"}: return s
    return default

def norm_id(v):
    if pd.isna(v): return ""
    s=str(v).strip()
    return s[:-2] if s.endswith(".0") else s

def facility_name(row, idx=0):
    return txt(row,["facility_name","name","FACILITY_NAME","Facility_Name","facility","FAC_NAME","name_1","facility_id","id"],f"Unnamed facility {idx+1}")

def facility_type(row):
    return txt(row,["facility_type","priority_group","type","category","amenity","building","f_type"],"TYPE NOT PROVIDED")

def classify_facility(row):
    s=(facility_name(row)+" "+facility_type(row)+" "+" ".join(str(row.get(c,"")) for c in row.index)).lower()
    if any(k in s for k in ("anganwadi","angan wadi","aganwadi","awc")): return "ANGANWADI"
    if any(k in s for k in ("school","zphs","mpps","mpups","primary school","high school","educational")): return "SCHOOL"
    if any(k in s for k in ("hospital","health","clinic","sub centre","sub-centre","subcentre","phc","medical")): return "HEALTH"
    if any(k in s for k in ("government","govt","panchayat","mandal","office","public facility","secretariat")): return "GOVERNMENT"
    return "OTHER"

def read_satellite_crop(path, bounds, max_dim=6500):
    """Read only the requested raster window; detail tiles therefore retain local pixels."""
    with rasterio.open(path) as src:
        if src.crs is None or src.crs.to_epsg()!=32644: stop(f"Satellite CRS must be EPSG:32644; got {src.crs}")
        win=from_bounds(*bounds, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
        win=win.intersection(Window(0,0,src.width,src.height))
        if win.width < 2 or win.height < 2: stop(f"Satellite crop is empty for bounds {bounds}; check CRS/extent")
        scale=min(1.0, max_dim/max(win.width,win.height))
        oh=max(1,int(win.height*scale)); ow=max(1,int(win.width*scale))
        count=min(3,src.count)
        arr=src.read(list(range(1,count+1)), window=win, out_shape=(count,oh,ow), resampling=Resampling.average)
        win_bounds=window_bounds(win,src.transform)
    if arr.shape[0]==1: arr=np.repeat(arr,3,axis=0)
    arr=np.moveaxis(arr[:3],0,-1)
    if arr.dtype != np.uint8:
        f=arr[np.isfinite(arr)]
        lo,hi=np.percentile(f,[2,98]) if f.size else (0,1)
        arr=np.clip((arr.astype(float)-lo)/max(float(hi-lo),1e-9),0,1)
    else:
        # Stretch mildly if image is washed out while preserving uint8 relative colour.
        x=arr.astype(float); lo,hi=np.percentile(x[np.isfinite(x)],[1,99])
        arr=np.clip((x-lo)/max(hi-lo,1),0,1)
    return arr, win_bounds

def show_bg(ax, img, b): ax.imshow(img,extent=(b[0],b[2],b[1],b[3]),origin="upper",zorder=0,interpolation="nearest")

def get_point(g):
    if g is None or g.is_empty: return None
    return g if g.geom_type=="Point" else g.representative_point()

def draw_facilities(ax, facs, fontsize=7):
    for i,r in facs.iterrows():
        p=get_point(r.geometry)
        if p is None: continue
        cat=r["facility_category_map"]
        marker={"SCHOOL":"*","HEALTH":"P","ANGANWADI":"^","GOVERNMENT":"s","OTHER":"D"}.get(cat,"D")
        ax.scatter([p.x],[p.y],s=125 if cat in ("SCHOOL","ANGANWADI") else 90,marker=marker,c=FAC_COL[cat],edgecolors="#111827",linewidths=0.85,zorder=12)
        name=r["facility_name_map"]
        lab=f"{name}\n[{cat}; source location unverified]"
        ax.annotate(lab,(p.x,p.y),xytext=(5,6),textcoords="offset points",fontsize=fontsize,color="white",zorder=13,
                    bbox=dict(boxstyle="round,pad=0.25",fc="#101923",ec=FAC_COL[cat],alpha=.94,lw=.7))

def legend_handles():
    return [
        Line2D([0],[0],color=EXISTING,lw=2.7,label="Existing TGRAC reference road"),
        Line2D([0],[0],color=PROPOSED,lw=2.5,label="Proposed access route (planning alternative)"),
        Patch(facecolor="none",edgecolor=QCOL["PLAUSIBLE"],lw=1.7,label="Footprint candidate: PLAUSIBLE"),
        Patch(facecolor="none",edgecolor=QCOL["REVIEW"],lw=1.7,label="Footprint candidate: REVIEW"),
        Patch(facecolor="none",edgecolor=QCOL["UNRESOLVED_MERGE"],lw=1.7,label="Candidate built-up extent: UNRESOLVED_MERGE"),
        Line2D([0],[0],marker="*",color="w",markerfacecolor=FAC_COL["SCHOOL"],markeredgecolor="black",markersize=10,label="School (source record)"),
        Line2D([0],[0],marker="P",color="w",markerfacecolor=FAC_COL["HEALTH"],markeredgecolor="black",markersize=8,label="Health facility (source record)"),
        Line2D([0],[0],marker="^",color="w",markerfacecolor=FAC_COL["ANGANWADI"],markeredgecolor="black",markersize=9,label="Anganwadi (only if named in source data)"),
        Line2D([0],[0],marker="s",color="w",markerfacecolor=FAC_COL["GOVERNMENT"],markeredgecolor="black",markersize=7,label="Government/public facility (source record)"),
    ]

def fmt_num(x,d=1):
    try:
        if pd.isna(x): return "—"
        return f"{float(x):,.{d}f}"
    except Exception: return "—"

def save_overview(out, boundary, roads, bld, facilities, routes, route_table, img_path, school_comp, summary):
    xmin,ymin,xmax,ymax=boundary.bounds
    pad_x=max((xmax-xmin)*.025,45); pad_y=max((ymax-ymin)*.025,45)
    bounds=(xmin-pad_x,ymin-pad_y,xmax+pad_x,ymax+pad_y)
    img,ib=read_satellite_crop(img_path,bounds,max_dim=7000)
    fig,ax=plt.subplots(figsize=(18,14))
    show_bg(ax,img,ib)
    gpd.GeoSeries([boundary],crs=CRS).boundary.plot(ax=ax,color="white",lw=1.6,zorder=2)
    if not roads.empty: roads.plot(ax=ax,color=EXISTING,lw=1.6,alpha=.97,zorder=3)
    for q in ("PLAUSIBLE","REVIEW","UNRESOLVED_MERGE","UNKNOWN"):
        ss=bld[bld.quality_class==q]
        if not ss.empty: ss.boundary.plot(ax=ax,color=QCOL[q],lw=.8,alpha=1,zorder=5)
    if not routes.empty: routes.plot(ax=ax,color=PROPOSED,lw=1.3,alpha=.95,zorder=7)
    if not school_comp.empty: school_comp.boundary.plot(ax=ax,color="#ed70ff",lw=1.5,linestyle="--",zorder=8)
    draw_facilities(ax,facilities,fontsize=7)
    ax.set_xlim(bounds[0],bounds[2]); ax.set_ylim(bounds[1],bounds[3]); ax.set_aspect("equal",adjustable="box")
    ax.set_title("DAMARAKUNTA — Rural access-planning overview\nSatellite crop read from the high-resolution mosaic; every candidate footprint and selected network route shown",fontsize=15,fontweight="bold",pad=12)
    ax.set_xlabel("Easting (m), EPSG:32644"); ax.set_ylabel("Northing (m), EPSG:32644"); ax.tick_params(labelsize=8); ax.grid(alpha=.14,lw=.4)
    uniq=float(summary.get("unique_grid_edge_length_network_aware_m",np.nan))
    total=float(pd.to_numeric(route_table.get("route_cost_score_model_units_not_INR", pd.Series(dtype=float)), errors="coerce").sum())
    note=(f"Routes: {len(routes)} | unique grid-edge length: {uniq/1000:.2f} km | Σ raster model-cost score: {total:,.2f} (NOT INR).\n"
          "DRAFT: model-derived footprints and route proposals are unverified. Red = proposed; cyan = existing reference roads. See route atlas for each ID, length and cost score.")
    ax.text(.012,.012,note,transform=ax.transAxes,fontsize=8,color="white",va="bottom",bbox=dict(boxstyle="round,pad=.4",fc="#101820",ec="white",alpha=.93))
    fig.legend(handles=legend_handles(),loc="lower center",ncol=3,fontsize=8.2,frameon=True,bbox_to_anchor=(.5,.015),framealpha=.98)
    fig.subplots_adjust(bottom=.16,top=.91,left=.07,right=.985)
    for ext,kw in (("png",{"dpi":600}),("pdf",{"format":"pdf"})):
        fn=out/f"final_satellite_overview_v4.{ext}"; fig.savefig(fn,bbox_inches="tight",pad_inches=.18,facecolor="white",**kw); print("Wrote:",fn)
    plt.close(fig)

def recursive_tiles(bounds, target_pts, max_ids=10, depth=0, max_depth=8):
    """Partition spatially so every tile's route table stays readable; IDs assigned by house centroid."""
    ids=list(target_pts.keys())
    if len(ids)<=max_ids or depth>=max_depth or len(ids)<2:
        return [(bounds,ids)] if ids else []
    xmin,ymin,xmax,ymax=bounds
    xs=xmax-xmin; ys=ymax-ymin
    # split longest dimension at median of target point coordinates, away from extremes
    split_x=xs>=ys
    vals=sorted([target_pts[i][0] if split_x else target_pts[i][1] for i in ids])
    split=float(vals[len(vals)//2])
    lo,hi=(xmin,xmax) if split_x else (ymin,ymax)
    if split<=lo+1e-6 or split>=hi-1e-6: return [(bounds,ids)]
    if split_x:
        b1=(xmin,ymin,split,ymax); b2=(split,ymin,xmax,ymax)
        ids1=[i for i in ids if target_pts[i][0] < split]; ids2=[i for i in ids if target_pts[i][0] >= split]
    else:
        b1=(xmin,ymin,xmax,split); b2=(xmin,split,xmax,ymax)
        ids1=[i for i in ids if target_pts[i][1] < split]; ids2=[i for i in ids if target_pts[i][1] >= split]
    if not ids1 or not ids2: return [(bounds,ids)]
    return recursive_tiles(b1,target_pts,max_ids,depth+1,max_depth)+recursive_tiles(b2,target_pts,max_ids,depth+1,max_depth)

def save_atlas(out,boundary,roads,bld,facilities,routes,targets,route_table,img_path,school_comp):
    """One target per sheet: readable, locally cropped, full-route evidence atlas.
    All geometries are model/source-derived and explicitly remain unverified.
    Includes every inside-village candidate; filtered-out targets get a no-route sheet.
    """
    route_schedule = route_table.copy()
    route_schedule["cand_key"] = route_schedule["cand_id"].map(norm_id)
    rt_by_cand = {norm_id(r.cand_id): r for _, r in route_schedule.iterrows()}
    route_by_hid = {str(r.house_route_id): r for _, r in routes.iterrows()}
    bld2 = bld.copy()
    bld2["cand_key"] = bld2.cand_id.map(norm_id)
    pdf_path = out / "individual_house_route_atlas_v4.pdf"
    png_previews=[]
    preview_ids={"H0001","H0002","H0004","H0107","H0114","H0118","H0163"}
    # A3 landscape makes map, metadata and a small local route schedule legible when printed.
    with PdfPages(pdf_path) as pdf:
        total=len(bld2)
        for page_no, (_, b) in enumerate(bld2.sort_values("cand_id",key=lambda z:z.map(lambda x:int(x) if str(x).isdigit() else 10**9)).iterrows(), start=1):
            cand=norm_id(b.cand_id)
            tr=rt_by_cand.get(cand)
            if tr is not None:
                hid=str(tr.house_route_id)
                rr=route_by_hid.get(hid)
            else:
                hid="NO_ROUTE_FILTERED_OUT"
                rr=None
            target_geom=b.geometry
            # Use the full route bounds to avoid clipping the selected route; include target roof and nearby context.
            if rr is not None and rr.geometry is not None and not rr.geometry.is_empty:
                gx0,gy0,gx1,gy1=rr.geometry.bounds
            else:
                gx0,gy0,gx1,gy1=target_geom.bounds
            bx0,by0,bx1,by1=target_geom.bounds
            gx0=min(gx0,bx0); gy0=min(gy0,by0); gx1=max(gx1,bx1); gy1=max(gy1,by1)
            spanx=max(gx1-gx0, 30); spany=max(gy1-gy0,30)
            pad=max(55.0, min(110.0, .18*max(spanx,spany)))
            view=[gx0-pad,gy0-pad,gx1+pad,gy1+pad]
            # Add local context around source features, without distorting coordinates.
            try:
                img,ib=read_satellite_crop(img_path,tuple(view),max_dim=5000)
            except Exception as e:
                print(f"WARNING satellite crop failed for {hid}: {e}")
                img=None; ib=tuple(view)
            fig=plt.figure(figsize=(16.54,11.69)) # A3 landscape in inches
            ax=fig.add_axes([.045,.105,.655,.79])
            side=fig.add_axes([.725,.09,.25,.82]); side.axis("off")
            if img is not None: show_bg(ax,img,ib)
            # Only local context is plotted; layer CRS is the common projected CRS EPSG:32644.
            vbox=box(*view)
            rb=roads[roads.intersects(vbox)] if not roads.empty else roads
            bb=bld2[bld2.intersects(vbox)] if not bld2.empty else bld2
            if boundary is not None:
                gpd.GeoSeries([boundary],crs=CRS).boundary.plot(ax=ax,color="white",lw=1.15,zorder=2)
            if not rb.empty: rb.plot(ax=ax,color=EXISTING,lw=2.1,alpha=.98,zorder=3)
            for q in ("PLAUSIBLE","REVIEW","UNRESOLVED_MERGE","UNKNOWN"):
                ss=bb[bb.quality_class==q]
                if not ss.empty: ss.boundary.plot(ax=ax,color=QCOL[q],lw=.95,alpha=1,zorder=5)
            if rr is not None:
                # All other planned routes in view are faint context; focal route is highlighted.
                ctx=routes[(routes.house_route_id.astype(str)!=hid) & routes.intersects(vbox)]
                if not ctx.empty: ctx.plot(ax=ax,color=CONTEXT,lw=.8,alpha=.78,zorder=6)
                gpd.GeoSeries([rr.geometry],crs=CRS).plot(ax=ax,color=PROPOSED,lw=3.25,alpha=1,zorder=9)
                rp=rr.geometry.interpolate(.5,normalized=True)
                ax.scatter([rp.x],[rp.y],s=45,c=PROPOSED,edgecolors="white",linewidths=.8,zorder=11)
            # Highlight the candidate polygon with thick outline and label its ID.
            q=str(b.quality_class) if pd.notna(b.get("quality_class")) else "UNKNOWN"
            edge=QCOL.get(q,QCOL["UNKNOWN"])
            gpd.GeoSeries([target_geom],crs=CRS).boundary.plot(ax=ax,color=edge,lw=2.7,zorder=12)
            p=target_geom.representative_point()
            ax.annotate(f"{hid}\nCAND {cand}",(p.x,p.y),xytext=(4,4),textcoords="offset points",fontsize=9.3,fontweight="bold",color="#111827",bbox=dict(boxstyle="round,pad=.25",fc="white",ec=edge,lw=1.5,alpha=.98),zorder=14)
            # Locally visible facility markers. Labels always state source-only/unverified.
            ff=facilities[facilities.intersects(vbox)] if not facilities.empty else facilities
            for _,fr in ff.iterrows():
                fp=get_point(fr.geometry)
                if fp is None: continue
                cat=str(fr.get("facility_category_map","OTHER")); marker={"SCHOOL":"*","HEALTH":"P","ANGANWADI":"^","GOVERNMENT":"s"}.get(cat,"D")
                col=FAC_COL.get(cat,FAC_COL["OTHER"])
                ax.scatter([fp.x],[fp.y],marker=marker,s=150,c=[col],edgecolors="#111111",linewidths=.9,zorder=15)
                ax.annotate(f"{fr.get('facility_name_map','Facility')}\nSOURCE LOCATION — UNVERIFIED",(fp.x,fp.y),xytext=(5,7),textcoords="offset points",fontsize=7.5,color="white",bbox=dict(boxstyle="round,pad=.2",fc="#17212b",ec=col,alpha=.95),zorder=16)
            if not school_comp.empty:
                sc=school_comp[school_comp.intersects(vbox)]
                if not sc.empty: sc.boundary.plot(ax=ax,color="#d58bff",lw=1.7,linestyle="--",zorder=10)
            # Extend view to display exact local crop and preserve map scale.
            ax.set_xlim(view[0],view[2]); ax.set_ylim(view[1],view[3]); ax.set_aspect("equal",adjustable="box")
            ax.set_title(f"DAMARAKUNTA — {hid} | Candidate {cand} | Sheet {page_no:03d}/{total}",fontsize=14,fontweight="bold",pad=10)
            ax.set_xlabel("Easting (m), EPSG:32644",fontsize=9); ax.set_ylabel("Northing (m), EPSG:32644",fontsize=9)
            ax.tick_params(labelsize=8); ax.grid(alpha=.16,lw=.4)
            # Scale bar sized to current extent.
            x0,x1=ax.get_xlim(); y0,y1=ax.get_ylim(); bar=max(10, round((x1-x0)*.15/10)*10)
            sx=x0+.05*(x1-x0); sy=y0+.06*(y1-y0)
            ax.plot([sx,sx+bar],[sy,sy],color="white",lw=5,solid_capstyle="butt",zorder=20)
            ax.plot([sx,sx+bar],[sy,sy],color="#111827",lw=2,solid_capstyle="butt",zorder=21)
            ax.text(sx+bar/2,sy+.018*(y1-y0),f"{bar:g} m",ha="center",va="bottom",fontsize=8,color="white",bbox=dict(fc="#111827",ec="none",alpha=.85,pad=1.5),zorder=22)
            # Right panel: metrics large and readable; no overloaded multi-target table.
            side.text(0,1.00,"TARGET & ROUTE RECORD",fontsize=13.5,fontweight="bold",va="top")
            side.text(0,.955,f"House route ID: {hid if rr is not None else 'NO ROUTE'}\nCandidate ID: {cand}\nDetection class: {q}",fontsize=11,va="top",linespacing=1.45)
            if tr is not None:
                attach=txt(tr,["network_attach_to","attach_to"],"NOT RECORDED")
                metric_rows=[
                    ["Proposed route length",f"{fmt_num(tr.network_route_length_m,2)} m"],
                    ["Raster-model cost score (not INR)",fmt_num(tr.network_route_cost,4)],
                    ["Connection target",attach],
                    ["Nearest TGRAC-road gap",f"{fmt_num(tr.nearest_road_gap_m,2)} m"],
                    ["Endpoint distance",f"{fmt_num(tr.network_endpoint_dist_m,2)} m"],
                    ["Independent-route length",f"{fmt_num(tr.get('independent_route_length_m',np.nan),2)} m"],
                    ["Independent cost score",fmt_num(tr.get("independent_route_cost",np.nan),4)],
                ]
            else:
                metric_rows=[["Proposed route","NOT GENERATED"],["Reason","Filtered by min-area threshold (<10 m²)"],["Footprint area",f"{fmt_num(target_geom.area,2)} m²"]]
            side.text(0,.855,"ROUTE METRICS",fontsize=10.5,fontweight="bold",va="top")
            mt=side.table(cellText=metric_rows,colLabels=["Metric","Value"],cellLoc="left",colLoc="left",bbox=[0,.425,1,.395])
            mt.auto_set_font_size(False); mt.set_fontsize(8.2); mt.scale(1,1.25)
            for (ri,ci),cell in mt.get_celld().items():
                cell.set_edgecolor("#cbd5e1"); cell.set_linewidth(.5)
                if ri==0: cell.set_facecolor("#dbeafe"); cell.set_text_props(weight="bold")
                elif ri%2: cell.set_facecolor("#f8fafc")
                else: cell.set_facecolor("#ffffff")
            side.text(0,.395,"MAP LEGEND",fontsize=10.1,fontweight="bold",va="top")
            leg_items=[(EXISTING,"Existing TGRAC reference road"),(PROPOSED,"Proposed planning route"),(QCOL["PLAUSIBLE"],"PLAUSIBLE footprint"),(QCOL["REVIEW"],"REVIEW footprint"),(QCOL["UNRESOLVED_MERGE"],"UNRESOLVED_MERGE extent")]
            ly=.36
            for c,label in leg_items:
                side.plot([0,.11],[ly,ly],color=c,lw=3 if c in (EXISTING,PROPOSED) else 2,clip_on=False)
                side.text(.15,ly,label,fontsize=8.0,va="center"); ly-=.033
            side.text(0,.185,"EVIDENCE NOTES",fontsize=10.1,fontweight="bold",va="top")
            side.text(0,.15,
                "• Planning alternative — not a confirmed road.\n"
                "• Candidate quality is not proof of a separate house.\n"
                "• Facility markers use source coordinates; verify independently.\n"
                "• Cost score is raster-model units, NOT Indian Rupees.\n"
                "• A route that attaches to another route reuses a planned segment.",
                fontsize=7.8,va="top",linespacing=1.35,wrap=True)
            fig.text(.045,.035,"Review sheet only — compare footprint against roof imagery and authoritative facility records before marking CONFIRMED.",fontsize=8.2,color="#7f1d1d")
            pdf.savefig(fig,bbox_inches="tight",pad_inches=.12,facecolor="white")
            if hid in preview_ids or (rr is None):
                png=out/f"detail_{hid.replace('/','_')}_candidate_{cand}_v4.png"
                fig.savefig(png,dpi=450,bbox_inches="tight",pad_inches=.12,facecolor="white"); png_previews.append(png)
            plt.close(fig)
            print(f"Atlas page {page_no}/{total}: {hid} candidate={cand}")
    print("Wrote complete one-candidate-per-page atlas:",pdf_path)
    print("Preview sheets written:",len(png_previews))
    return total,png_previews

def draw_journal_figures(out, summary, quality):
    # Architecture diagram
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    fig,ax=plt.subplots(figsize=(12,12)); ax.set_xlim(0,12); ax.set_ylim(0,12); ax.axis("off")
    boxes=[(2.4,10.6,7.2,.65,"Rural satellite imagery + village boundary","#e0f2fe"),(2.4,9.55,7.2,.65,"AI feature extraction: building/road candidates + land cover","#e0f2fe"),(2.4,8.5,7.2,.65,"Candidate and facility QA; preserve uncertainty labels","#fff1d6"),(2.4,7.45,7.2,.65,"GIS alignment, cost surface and hard constraints","#e8f5e9"),(2.4,6.4,7.2,.65,"House candidates + named facilities + existing road network","#f3e8ff"),(2.4,5.35,7.2,.65,"Stage A: generate feasible route alternatives","#e0f2fe"),(2.4,4.3,7.2,.65,"Stage B: select routes with shared-edge credit","#e0f2fe"),(2.4,3.25,7.2,.65,"Compare against independent and straight-line baselines","#f3e8ff")]
    for x,y,w,h,t,c in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.04",fc=c,ec="#365a7a",lw=1.2)); ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=8.7)
    for i in range(len(boxes)-1):
        x,y,w,h,_,_=boxes[i]; nx,ny,nw,nh,_,_=boxes[i+1]; ax.add_patch(FancyArrowPatch((x+w/2,y),(nx+nw/2,ny+nh),arrowstyle="-|>",mutation_scale=12,lw=1.1,color="#475569"))
    cboxes=[(.35,1.35,3.5,1.05,"C1 — Perturb segmentation; measure downstream route impact","#fff1d6"),(4.25,1.35,3.5,1.05,"C2 — Unique network length/cost, connectivity and sensitivity","#e8f5e9"),(8.15,1.35,3.5,1.05,"C3 — Evaluate transfer across rural villages","#fff1d6")]
    for x,y,w,h,t,c in cboxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.04",fc=c,ec="#365a7a",lw=1.2)); ax.text(x+w/2,y+h/2,t,ha="center",va="center",fontsize=7.8,wrap=True)
    for x in (2.1,6,9.9): ax.add_patch(FancyArrowPatch((6,3.25),(x,2.4),arrowstyle="-|>",mutation_scale=12,lw=1.0,color="#475569"))
    ax.text(6,.65,"Outputs: validated satellite map • route-wise schedule • QA evidence • journal figures",ha="center",fontsize=9,weight="bold")
    ax.set_title("Research architecture — AI/GIS rural infrastructure planning",fontsize=14,weight="bold")
    for ext,kw in (("png",{"dpi":600}),("pdf",{"format":"pdf"}),("svg",{"format":"svg"})):
        fn=out/f"journal_project_architecture_flowchart_v4.{ext}"; fig.savefig(fn,bbox_inches="tight",pad_inches=.15,facecolor="white",**kw); print("Wrote:",fn)
    plt.close(fig)
    # quality chart
    labs=["PLAUSIBLE","REVIEW","UNRESOLVED_MERGE"]; vals=[quality.get(x,0) for x in labs]
    fig,ax=plt.subplots(figsize=(8.5,5.2)); bars=ax.bar(labs,vals,color=[QCOL[x] for x in labs]); ax.bar_label(bars,padding=3,fontsize=10)
    ax.set_ylabel("Candidate polygons (count)"); ax.set_title("Building-candidate quality classes (inside village, n=165)\nNot ground-truth confirmation of house identity")
    ax.grid(axis="y",alpha=.25); fig.tight_layout()
    for ext,kw in (("png",{"dpi":600}),("pdf",{"format":"pdf"}),("svg",{"format":"svg"})):
        fn=out/f"journal_building_quality_distribution_v4.{ext}"; fig.savefig(fn,bbox_inches="tight",pad_inches=.12,facecolor="white",**kw); print("Wrote:",fn)
    plt.close(fig)
    # comparison chart based on current recorded summaries only
    fig,ax=plt.subplots(figsize=(8.7,5.2)); vals=[float(summary.get("unique_grid_edge_length_independent_m",np.nan))/1000,float(summary.get("unique_grid_edge_length_network_aware_m",np.nan))/1000]
    bars=ax.bar(["Independent routes","Network-aware shared network"],vals,color=["#4b91d1","#ff6384"]); ax.bar_label(bars,fmt="%.2f km",padding=3,fontsize=9)
    ax.set_ylabel("Unique grid-edge length (km)"); ax.set_title("Damarakunta shared-network experiment — preliminary\nModel-derived targets; no field validation")
    ax.grid(axis="y",alpha=.25); fig.tight_layout()
    for ext,kw in (("png",{"dpi":600}),("pdf",{"format":"pdf"}),("svg",{"format":"svg"})):
        fn=out/f"journal_shared_network_length_comparison_v4.{ext}"; fig.savefig(fn,bbox_inches="tight",pad_inches=.12,facecolor="white",**kw); print("Wrote:",fn)
    plt.close(fig)

def main():
    if OUT.exists() and any(OUT.iterdir()): stop(f"Output folder not empty: {OUT}. Use --out-dir for a new path; no files overwritten.")
    OUT.mkdir(parents=True,exist_ok=True)
    required=["buildings","roads","facilities","boundary","background","network_gpkg","network_summary","network_status"]
    for k in required:
        if not P[k].exists(): stop(f"Required input missing ({k}): {P[k]}")
    print("Reading GIS layers and route schedule; all source data will remain read-only...")
    b_all=read_gdf(P["buildings"],"buildings");
    if "inside_village" in b_all.columns: bld=b_all[b_all.inside_village.map(truth)].copy()
    else: stop("Building layer has no inside_village flag; refusing to infer unverified subset silently")
    bld=bld[bld.geometry.notna() & ~bld.geometry.is_empty].copy()
    if "cand_id" not in bld.columns: stop("Building layer has no cand_id field")
    bld["cand_id"]=bld.cand_id.map(norm_id)
    if "quality_class" not in bld.columns: bld["quality_class"]="UNKNOWN"
    bld["quality_class"]=bld.quality_class.fillna("UNKNOWN").astype(str)
    bld["geometry_valid"]=bld.geometry.is_valid
    bld["area_calc_m2"]=bld.geometry.area
    roads=read_gdf(P["roads"])
    fac=read_gdf(P["facilities"],"priority_facilities",required=False)
    if fac.empty: fac=read_gdf(P["facilities"],required=False)
    boundary_gdf=read_gdf(P["boundary"]); boundary=boundary_gdf.geometry.union_all()
    school_comp=read_gdf(ROOT/"reference"/"school_compounds_utm44n.gpkg",required=False)
    with open(P["network_summary"],encoding="utf-8") as f: summary=json.load(f)
    status=pd.read_csv(P["network_status"],dtype=str)
    status["cand_id"]=status.cand_id.map(norm_id)
    status["house_route_id"]=status.house_route_id.astype(str)
    layers=fiona.listlayers(str(P["network_gpkg"]))
    if not {"house_target_status","routes_network_aware"}.issubset(set(layers)): stop(f"Required network layers absent: {layers}")
    routes=read_gdf(P["network_gpkg"],"routes_network_aware")
    targets=read_gdf(P["network_gpkg"],"house_target_status")
    routes["house_route_id"]=routes.house_route_id.astype(str); targets["house_route_id"]=targets.house_route_id.astype(str); targets["cand_id"]=targets.cand_id.map(norm_id)
    # Take field metrics from status table and geometry from GPKG.
    route_schedule=status.copy()
    # normalize column names in case scripts used slightly different aliases
    length_col=next((c for c in ["network_route_length_m","route_length_m","length_m"] if c in route_schedule.columns),None)
    cost_col=next((c for c in ["network_route_cost","route_cost","cost"] if c in route_schedule.columns),None)
    if length_col is None or cost_col is None: stop(f"Expected route length/cost fields missing. Available columns: {list(route_schedule.columns)}")
    route_schedule["network_route_length_m"]=pd.to_numeric(route_schedule[length_col],errors="coerce")
    route_schedule["network_route_cost"]=pd.to_numeric(route_schedule[cost_col],errors="coerce")
    route_schedule["nearest_road_gap_m"]=pd.to_numeric(route_schedule.get("nearest_road_gap_m",pd.Series(np.nan,index=route_schedule.index)),errors="coerce")
    route_schedule["network_endpoint_dist_m"]=pd.to_numeric(route_schedule.get("network_endpoint_dist_m",pd.Series(np.nan,index=route_schedule.index)),errors="coerce")
    route_schedule=route_schedule.merge(targets[["house_route_id","geometry"]].rename(columns={"geometry":"target_geometry"}),on="house_route_id",how="left")
    # Footprint review evidence and route IDs
    by_cand={norm_id(r.cand_id):r for _,r in route_schedule.iterrows()}
    bld["house_route_id"]=bld.cand_id.map(lambda x: by_cand[x].house_route_id if x in by_cand else "NO_ROUTE_FILTERED_OUT")
    # Two different checks: representative point containment is weaker than full-polygon containment.
    bld["representative_point_inside_boundary_check"] = bld.geometry.apply(
        lambda g: bool(boundary.covers(g.representative_point())) if g is not None and not g.is_empty else False)
    bld["full_footprint_covered_by_boundary"] = bld.geometry.apply(
        lambda g: bool(boundary.covers(g)) if g is not None and not g.is_empty and g.is_valid else False)
    # Keep the earlier column name for downstream compatibility, but define it honestly as point check.
    bld["inside_boundary_geometry_check"] = bld["representative_point_inside_boundary_check"]
    bld["nearest_tgrac_road_distance_m"] = bld.geometry.distance(roads.geometry.union_all()).round(2)
    bld["centroid_x_utm_m"]=bld.geometry.centroid.x; bld["centroid_y_utm_m"]=bld.geometry.centroid.y
    ll=[WGS84.transform(x,y) for x,y in zip(bld.centroid_x_utm_m,bld.centroid_y_utm_m)]
    bld["centroid_longitude"]= [x[0] for x in ll]; bld["centroid_latitude"]=[x[1] for x in ll]
    bld["visual_review_status"]="NOT_YET_VISUALLY_VERIFIED"
    bld["verification_note"]="Geometry/boundary checks do not prove this is a real individual house; visually compare polygon outline with the roof and update review status."
    bcols=[c for c in ["cand_id","bld_id","house_route_id","quality_class","status","area_m2","area_calc_m2","mean_prob","max_prob","inside_village","geometry_valid","representative_point_inside_boundary_check","full_footprint_covered_by_boundary","inside_boundary_geometry_check","nearest_tgrac_road_distance_m","centroid_x_utm_m","centroid_y_utm_m","centroid_latitude","centroid_longitude","visual_review_status","verification_note"] if c in bld.columns]
    bld[bcols].to_csv(OUT/"building_footprint_verification_checklist.csv",index=False)
    # facility details + coordinate evidence; no silently invented facility.
    facility_source_records = int(len(fac))
    facility_records_missing_geometry = int(fac.geometry.isna().sum() + fac.geometry.is_empty.sum()) if "geometry" in fac else facility_source_records
    if not fac.empty:
        fac=fac[fac.geometry.notna() & ~fac.geometry.is_empty].copy()
        fac["facility_name_map"]=[facility_name(r,i) for i,(_,r) in enumerate(fac.iterrows())]
        fac["facility_type_map"]=fac.apply(facility_type,axis=1)
        fac["facility_category_map"]=fac.apply(classify_facility,axis=1)
        fac["source_geometry_valid"]=fac.geometry.is_valid
        fac["location_validation_status"]="SOURCE_LAYER_LOCATION_NOT_INDEPENDENTLY_VERIFIED"
        fxs=[]; fys=[]; flons=[]; flats=[]; nearest_ids=[]; nearest_dist=[]; nearest_quals=[]; mapsurls=[]
        for _,r in fac.iterrows():
            p=get_point(r.geometry); x,y=p.x,p.y; lon,lat=WGS84.transform(x,y)
            fxs.append(x); fys.append(y); flons.append(lon); flats.append(lat)
            mapsurls.append(f"https://www.google.com/maps/search/?api=1&query={lat:.7f}%2C{lon:.7f}")
            if len(bld):
                ds=bld.geometry.distance(r.geometry); ix=ds.idxmin(); nearest_ids.append(norm_id(bld.loc[ix,"cand_id"])); nearest_dist.append(float(ds.loc[ix])); nearest_quals.append(str(bld.loc[ix,"quality_class"]))
            else: nearest_ids.append(""); nearest_dist.append(np.nan); nearest_quals.append("")
        fac["source_x_utm_m"]=fxs; fac["source_y_utm_m"]=fys; fac["source_longitude"]=flons; fac["source_latitude"]=flats
        fac["source_coordinate_map_link"]=mapsurls; fac["nearest_candidate_id"]=nearest_ids; fac["nearest_candidate_distance_m"]=nearest_dist; fac["nearest_candidate_quality"]=nearest_quals
        fac["nearest_candidate_association_status"]=np.where(pd.to_numeric(fac.nearest_candidate_distance_m,errors="coerce")<=30,"POTENTIAL_NEARBY_FOOTPRINT_NOT_CONFIRMED","NO_CANDIDATE_WITHIN_30M_OR_REVIEW_REQUIRED")
        cols=[c for c in fac.columns if c!="geometry"]
        fac[cols].to_csv(OUT/"public_facility_verification_checklist.csv",index=False)
        fac.to_file(OUT/"public_facilities_for_review.gpkg",layer="facilities",driver="GPKG")
    else:
        print("WARNING: No usable facility geometries were found in the configured priority-facility layer.")
        print("WARNING: School/health/Anganwadi/government facility markers will not be invented or plotted.")
        # Still create an explicit empty checklist so absence is documented rather than silently ignored.
        fac = gpd.GeoDataFrame({
            "facility_name_map": pd.Series(dtype="object"),
            "facility_type_map": pd.Series(dtype="object"),
            "facility_category_map": pd.Series(dtype="object"),
            "location_validation_status": pd.Series(dtype="object"),
            "source_geometry_valid": pd.Series(dtype="bool"),
            "source_latitude": pd.Series(dtype="float"),
            "source_longitude": pd.Series(dtype="float"),
        }, geometry=gpd.GeoSeries([], crs=CRS), crs=CRS)
        fac.to_csv(OUT/"public_facility_verification_checklist.csv", index=False)
    # Route-wise schedule with unambiguous fields and target coords.
    target_geom_by_id={r.house_route_id:r.geometry for _,r in targets.iterrows()}
    rows=[]
    for _,r in route_schedule.iterrows():
        g=target_geom_by_id.get(str(r.house_route_id)); p=get_point(g) if g is not None else None
        lon=lat=np.nan
        if p is not None: lon,lat=WGS84.transform(p.x,p.y)
        rows.append({
            "house_route_id":r.house_route_id,"cand_id":norm_id(r.cand_id),"quality_class":r.get("quality_class","UNKNOWN"),
            "network_status":r.get("network_status","NOT PROVIDED"),"attach_to":r.get("network_attach_to",""),
            "route_length_m":r.network_route_length_m,"route_cost_score_model_units_not_INR":r.network_route_cost,
            "nearest_road_gap_m":r.nearest_road_gap_m,"endpoint_distance_m":r.network_endpoint_dist_m,
            "independent_route_length_m":pd.to_numeric(r.get("independent_route_length_m",np.nan),errors="coerce"),
            "independent_route_cost_score":pd.to_numeric(r.get("independent_route_cost",np.nan),errors="coerce"),
            "target_longitude":lon,"target_latitude":lat,
            "financial_construction_cost_INR":pd.NA,
            "note":"Cost is raster-model score, not currency; candidate house identity and road access remain unverified."
        })
    schedule=pd.DataFrame(rows)
    schedule.to_csv(OUT/"proposed_route_length_and_cost_schedule.csv",index=False)
    # Merge schedule onto route features; routes plotted as selected proposals only.
    route_meta=schedule.set_index("house_route_id")
    routes["cand_key"]=routes.cand_id.map(norm_id)
    routes["schedule_length_m"]=routes.house_route_id.map(route_meta.route_length_m.to_dict())
    routes["schedule_cost_score"]=routes.house_route_id.map(route_meta.route_cost_score_model_units_not_INR.to_dict())
    # Create explicit evidence audit / summary
    facility_names=fac.facility_name_map.astype(str).tolist()
    ang_mask=(fac.get("facility_category_map",pd.Series("",index=fac.index)).astype(str).eq("ANGANWADI") | \
              fac.get("facility_type_map",pd.Series("",index=fac.index)).astype(str).str.contains(r"angan\s*wadi|anganwadi|aganwadi|\bawc\b",case=False,regex=True,na=False) | \
              fac.get("facility_name_map",pd.Series("",index=fac.index)).astype(str).str.contains(r"angan\s*wadi|anganwadi|aganwadi|\bawc\b",case=False,regex=True,na=False))
    ang=fac.loc[ang_mask,"facility_name_map"].astype(str).tolist() if not fac.empty else []
    qcounts=bld.quality_class.value_counts().to_dict()
    audit={
        "package_status":"REVIEW_DRAFT_NOT_GROUND_TRUTH_VERIFIED",
        "project":"Damarakunta, Markook, Siddipet, Telangana",
        "crs":"EPSG:32644",
        "source_buildings_inside_village":len(bld),
        "footprint_geometry_invalid_count":int((~bld.geometry_valid).sum()),
        "representative_points_outside_boundary_count":int((~bld.representative_point_inside_boundary_check).sum()),
        "full_footprints_not_completely_covered_by_boundary_count":int((~bld.full_footprint_covered_by_boundary).sum()),
        "footprints_not_fully_covered_by_boundary_ids":bld.loc[~bld.full_footprint_covered_by_boundary,"cand_id"].astype(str).tolist(),
        "quality_classes":{str(k):int(v) for k,v in qcounts.items()},
        "targets_with_route_geometry":len(routes),
        "target_ids_without_network_route_geometry":sorted(set(route_schedule.house_route_id.astype(str))-set(routes.house_route_id.astype(str))),
        "inside_village_candidates_filtered_out_of_routing_by_area":int((~bld.cand_id.isin(route_schedule.cand_id.map(norm_id))).sum()),
        "route_schedule_rows":len(schedule),
        "route_length_sum_m":float(pd.to_numeric(schedule.route_length_m,errors="coerce").sum()),
        "unique_network_grid_edge_length_m":summary.get("unique_grid_edge_length_network_aware_m"),
        "raster_model_cost_score_sum_not_INR":float(pd.to_numeric(schedule.route_cost_score_model_units_not_INR,errors="coerce").sum()),
        "financial_construction_cost_INR":None,
        "facility_source_records_total_before_geometry_filter":facility_source_records,
        "facility_source_records_with_missing_or_empty_geometry":facility_records_missing_geometry,
        "facility_source_records_with_usable_geometry":len(fac),
        "facility_names_as_in_source_layer":facility_names,
        "anganwadi_records_found_by_source_name_or_type":ang,
        "anganwadi_location_status":"PRESENT_IN_SOURCE_LAYER_BUT_NOT_INDEPENDENTLY_VERIFIED" if ang else "NO_ANGANWADI_NAME_IN_CURRENT_PRIORITY_FACILITY_LAYER; LOCATION_NOT_INVENTED",
        "semantic_building_accuracy":"NOT_VERIFIED; visual/authoritative review required",
        "source_raster_note":"Each map crop is read independently from the high-resolution mosaic; no zooming a globally downsampled backdrop.",
        "facility_warning":"Only features with usable coordinates in the configured facility source layer are mapped; missing facilities are not guessed.",
        "map_design":"Cyan=existing TGRAC reference roads; pink/red=proposed network-aware route; footprint outlines encode detection quality.",
        "constraints":"Current network experiment uses slope threshold 25 degrees plus the planner's configured water/prohibited constraints.",
        "limitations":["PLAUSIBLE/REVIEW/UNRESOLVED_MERGE are model quality classes, not proof of house identity.","A line ending near a reference road is a model planning alternative, not a field-confirmed usable road.","Raster cost score is not INR. Construction cost requires design width/specification, quantity takeoff and local unit rates.","Official facility source layer locations must be checked against authoritative records/on-ground evidence."],
        "review_files":["final_satellite_overview_v4.png","individual_house_route_atlas_v4.pdf","building_footprint_verification_checklist.csv","public_facility_verification_checklist.csv","proposed_route_length_and_cost_schedule.csv"]
    }
    (OUT/"final_output_automated_audit_v4.json").write_text(json.dumps(audit,indent=2,default=str),encoding="utf-8")
    # Spatial QA GPKG (new file in new output folder)
    bld.to_file(OUT/"candidate_footprints_for_review_v4.gpkg",layer="candidate_footprints",driver="GPKG")
    routes.to_file(OUT/"proposed_routes_with_metrics_v4.gpkg",layer="network_aware_routes",driver="GPKG")
    # Clear full-village map and adaptive route atlas with per-route table
    save_overview(OUT,boundary,roads,bld,fac,routes,schedule,P["background"],school_comp,summary)
    ntiles,pngs=save_atlas(OUT,boundary,roads,bld,fac,routes,targets,schedule,P["background"],school_comp)
    qc={k:int(qcounts.get(k,0)) for k in ("PLAUSIBLE","REVIEW","UNRESOLVED_MERGE","UNKNOWN")}
    draw_journal_figures(OUT,summary,qc)
    print("\n=== FACILITY SOURCE RECORDS (NOT INDEPENDENTLY VERIFIED) ===")
    for _,r in fac.iterrows(): print(f"{r.facility_name_map} | type={r.facility_type_map} | category={r.facility_category_map} | lon={r.source_longitude:.7f}, lat={r.source_latitude:.7f} | closest candidate={r.nearest_candidate_id} ({r.nearest_candidate_distance_m:.1f} m)")
    if ang:
        print("\nANGANWADI SOURCE MATCHES (matched using category, source name, OR source type):")
        for _,r in fac.loc[ang_mask].iterrows():
            print(f"  {r.facility_name_map} | type={r.facility_type_map} | source-layer lon={r.source_longitude:.7f}, lat={r.source_latitude:.7f}; independently confirm this coordinate before accepting it")
    else:
        print("\nWARNING: No Anganwadi/AWC match found in source name, type, or category. A location will NOT be guessed.")
    print("\n=== FINAL REVIEW V4.0 SUMMARY ===")
    print(json.dumps(audit,indent=2,default=str))
    print(f"\nDetail atlas pages: {ntiles}; one candidate per page; route metrics appear beside the local map.")
    print("Folder:",OUT)

if __name__=="__main__":
    ap=None
    # Optional output-folder override to keep every prior folder immutable.
    import argparse
    _ap=argparse.ArgumentParser(add_help=True)
    _ap.add_argument("--out-dir",default=None,help="new output folder; default final_output_validation_v4")
    _args=_ap.parse_args()
    if _args.out_dir: OUT=Path(_args.out_dir)
    main()
