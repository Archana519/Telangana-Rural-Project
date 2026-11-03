"""One-off patch (kept for provenance): roads clipped to the village boundary with gpd.clip() before routing (inputs/road_clip_report.csv);
the 961 slope and 178 land-cover gaps documented as a spatial limitation of the 30 m DEM and land-cover grid, not interpolated."""
R = r"D:\Telangana_Rural_Project"
TEX = R + r"\Phase1_Report_CBIT_Format\source_tex\A_Dissertation_Phase_I_Review_1_Report_Final.tex"


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert s.count(a) == 1, (path[-30:], s.count(a), a[:70])
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


CLIP = ("the TGRAC road lines were clipped to the village boundary with \\texttt{gpd.clip()} before routing: of 93,496.76~m (43 lines), 41,789.51~m (44.70~percent; 20 lines reached outside) lay outside the boundary and was removed, "
        "leaving 51,707.25~m in 50 line parts that lie entirely inside the boundary; only these are used as road goals and for connectivity")
GAPS = ("Inside the boundary, 961 cells have no slope value and 178 cells have no land-cover value because of the coarse 30~m DEM and land-cover source; these gaps are a spatial limitation of the source data. "
        "They were not filled by interpolation or any other synthetic estimate: the planner treats them as invalid cells that routes cannot cross")

patch(TEX, [
    ("\\textbf{Environment.} Python 3.10, projected CRS EPSG:32644, 10~m grid. The 10~m slope is interpolated from about 30~m DEM data and does not contain true 10~m terrain detail.",
     "\\textbf{Boundary clipping.} In the final scenarios " + CLIP + " (\\texttt{src/preprocessing/clip\\_roads.py}, \\texttt{inputs/road\\_clip\\_report.csv}). The original road file is not edited.\n\n"
     "\\textbf{Environment.} Python 3.10, projected CRS EPSG:32644, 10~m grid. The 10~m slope is resampled from about 30~m DEM data and does not contain true 10~m terrain detail. " + GAPS + "."),
    ("\\item The 30~m DEM interpolated to 10~m slope has no true 10~m terrain detail.",
     "\\item The 30~m DEM resampled to a 10~m slope grid has no true 10~m terrain detail. The 961 slope gaps and 178 land-cover gaps inside the boundary are a spatial limitation of the 30~m source data and are not interpolated."),
])
patch(R + r"\Phase1_Report_CBIT_Format\content_v2.py", [
    ("Slope is computed from the 30 m DEM and interpolated to 10 m.", "Slope is computed from the 30 m DEM and resampled to 10 m."),
    ("Resampling a 30 m DEM does not give 10 m terrain accuracy.", "Resampling a 30 m DEM does not give 10 m terrain accuracy. These gaps are a spatial limitation of the 30 m source data and were not filled by interpolation; the planner treats them as invalid cells."),
    ("43 line features, 93,496.76 m; 41,789.51 m (44.70 percent) lies outside the polygon; 20 of 43 features reach outside",
     "43 line features, 93,496.76 m; 41,789.51 m (44.70 percent) lies outside the polygon and 20 of 43 features reach outside; clipped with gpd.clip() to 50 line parts, 51,707.25 m, all inside, which are the roads routed in the final scenarios"),
    ("slope on the 10 m grid (interpolated); 961 invalid slope cells inside the polygon", "slope resampled to the 10 m grid; 961 slope gaps inside the polygon, not interpolated (limitation of the 30 m DEM)"),
    ("178 land-cover and 961 slope gaps inside the polygon;", "178 land-cover and 961 slope gaps inside the polygon, a limitation of the 30 m source data, not interpolated;"),
    ("44.70 percent of road length lies outside the polygon; the earlier statement that all roads were inside is contradicted.", "44.70 percent of the raw road length lies outside the polygon (the earlier statement that all roads were inside is contradicted); the layer was clipped with gpd.clip() and only the 51,707.25 m inside the boundary is routed."),
])
patch(R + r"\src\reporting\limitations_text.py", [
    ("- 44.7% of the TGRAC road length lies outside the village polygon; the polygon clips the planning grid, and the boundary has not been independently validated.",
     "- 44.7% of the raw TGRAC road length lies outside the village polygon. The road layer was clipped to the boundary with gpd.clip() (51,707 m of 93,497 m remain, in 50 parts) and only the clipped roads are routed; the boundary itself has not been independently validated.\n"
     "- 961 slope cells and 178 land-cover cells inside the boundary have no value because of the coarse 30 m DEM and land-cover source. This is a spatial limitation: the gaps are not filled by interpolation, and the planner treats them as invalid cells."),
])
print("patched")
