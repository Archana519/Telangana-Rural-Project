
from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from rasterio.plot import show
from shapely.geometry import box

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
ALIGNED = BASE / "aligned"
OUT = BASE / "results"
OUT.mkdir(parents=True, exist_ok=True)

imagery_path = ALIGNED / "damarakunta_esri_highres_mosaic_0p6m.tif"
health_path = REF / "tgrac_health.gpkg"
subcentre_path = REF / "tgrac_sub_centres.gpkg"
facilities_path = REF / "damarakunta_priority_facilities.gpkg"
roads_path = REF / "tgrac_road_network.gpkg"

CRS = "EPSG:32644"

health = gpd.read_file(health_path).to_crs(CRS)
subcentres = gpd.read_file(subcentre_path).to_crs(CRS)
facilities = gpd.read_file(facilities_path).to_crs(CRS)
roads = gpd.read_file(roads_path).to_crs(CRS)

health_point = health.iloc[0].geometry
subcentre_point = subcentres.iloc[0].geometry

# Create a local comparison extent around both candidate locations.
minx = min(health_point.x, subcentre_point.x)
miny = min(health_point.y, subcentre_point.y)
maxx = max(health_point.x, subcentre_point.x)
maxy = max(health_point.y, subcentre_point.y)

margin = 180
extent = box(
    minx - margin, miny - margin,
    maxx + margin, maxy + margin
)

roads_clip = roads[roads.intersects(extent)].copy()
facilities_clip = facilities[
    facilities.geometry.intersects(extent)
].copy()

fig, ax = plt.subplots(figsize=(12, 10))

with rasterio.open(imagery_path) as src:
    show(
        src,
        ax=ax,
        extent=src.bounds,
        transform=src.transform
    )

# Restrict the display to the area containing both candidate points.
ax.set_xlim(minx - margin, maxx + margin)
ax.set_ylim(miny - margin, maxy + margin)

if not roads_clip.empty:
    roads_clip.plot(
        ax=ax,
        color="cyan",
        linewidth=2,
        label="Mapped existing roads",
        zorder=3
    )

if not facilities_clip.empty:
    facilities_clip.plot(
        ax=ax,
        color="white",
        edgecolor="black",
        markersize=65,
        label="Other priority facilities",
        zorder=4
    )

ax.scatter(
    [health_point.x],
    [health_point.y],
    s=180,
    marker="o",
    color="magenta",
    edgecolor="white",
    linewidth=1.5,
    label="Health dataset location",
    zorder=6
)

ax.scatter(
    [subcentre_point.x],
    [subcentre_point.y],
    s=180,
    marker="s",
    color="yellow",
    edgecolor="black",
    linewidth=1.5,
    label="Sub-centre dataset location",
    zorder=6
)

ax.annotate(
    "Health record\nNIN 8734223673",
    (health_point.x, health_point.y),
    xytext=(10, 12),
    textcoords="offset points",
    color="white",
    fontsize=9,
    bbox=dict(facecolor="black", alpha=0.75)
)

ax.annotate(
    "Sub-centre record\nSame NIN",
    (subcentre_point.x, subcentre_point.y),
    xytext=(10, -35),
    textcoords="offset points",
    color="black",
    fontsize=9,
    bbox=dict(facecolor="yellow", alpha=0.9)
)

distance = health_point.distance(subcentre_point)

ax.set_title(
    "Damarakunta: Duplicate Health-Record Location Check\n"
    f"Distance between source coordinates: {distance:.2f} m"
)
ax.set_xlabel("Easting (m) — EPSG:32644")
ax.set_ylabel("Northing (m) — EPSG:32644")
ax.legend(loc="best")
ax.set_aspect("equal", adjustable="box")
ax.grid(alpha=0.2)

output_path = OUT / "damarakunta_health_location_comparison.png"
fig.tight_layout()
fig.savefig(output_path, dpi=220, bbox_inches="tight")
plt.close(fig)

print("LOCATION COMPARISON MAP CREATED")
print(output_path)
print(f"Distance between records: {distance:.2f} m")
print("The map does not establish which source coordinate is correct.")
