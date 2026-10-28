from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]

gpkg = (
    root / "Siddipet" / "Damarakunta" / "results"
    / "connectivity_audit_v1" / "ca1"
    / "connectivity_audit.gpkg"
)

out = gpkg.parent.parent / "maps_ca1"
out.mkdir(parents=True, exist_ok=True)

if not gpkg.exists():
    raise FileNotFoundError(f"GeoPackage not found: {gpkg}")

names = [
    "candidates",
    "facilities",
    "road_segments",
    "dangling_ends",
    "inferred_bridges",
    "routes_at_attach_tol",
]

layers = {
    name: gpd.read_file(gpkg, layer=name)
    for name in names
}

crs = layers["road_segments"].crs

for name in names:
    if crs and layers[name].crs and layers[name].crs != crs:
        layers[name] = layers[name].to_crs(crs)

def draw(filename, title, show_candidates=True,
         show_facilities=True, show_routes=True,
         show_ends=False, show_bridges=False):

    fig, ax = plt.subplots(figsize=(12, 10))

    def plot_layer(name, **kwargs):
        data = layers[name]
        if not data.empty:
            data.plot(ax=ax, **kwargs)

    if show_candidates:
        plot_layer(
            "candidates", facecolor="none",
            edgecolor="darkorange", linewidth=0.6,
            label="Candidate polygons"
        )

    plot_layer(
        "road_segments", color="dimgray",
        linewidth=1.0, label="Mapped road segments"
    )

    if show_routes:
        plot_layer(
            "routes_at_attach_tol", color="royalblue",
            linewidth=1.8, label="Routes at attachment tolerance"
        )

    if show_facilities:
        plot_layer(
            "facilities", color="purple",
            markersize=35, marker="^", label="Facility records"
        )

    if show_ends:
        plot_layer(
            "dangling_ends", color="red",
            markersize=18, label="Dangling endpoints"
        )

    if show_bridges:
        plot_layer(
            "inferred_bridges", color="magenta",
            linewidth=2.5, linestyle="--",
            label="Inferred bridge candidates"
        )

    ax.set_title(title, fontsize=14)
    ax.set_axis_off()
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    path = out / filename
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")

draw(
    "01_study_area_overview.png",
    "Damarakunta - GIS Layer Overview"
)

draw(
    "02_building_road_connectivity.png",
    "Candidate Buildings and Mapped Road Connectivity",
    show_routes=False
)

draw(
    "03_proposed_road_routes.png",
    "Mapped Roads and Routes at Attachment Tolerance"
)

draw(
    "04_connectivity_audit.png",
    "Connectivity Audit - Endpoints and Inferred Bridges",
    show_ends=True,
    show_bridges=True
)

print(f"\nFigures saved in: {out}")
print("Note: these are GIS maps, not satellite-background maps.")