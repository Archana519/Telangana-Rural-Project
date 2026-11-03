
from pathlib import Path
import geopandas as gpd
import pandas as pd

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
OUT = REF / "damarakunta_priority_facilities.gpkg"

# Use verified school compound polygons and derive representative points.
schools = gpd.read_file(REF / "school_compounds_utm44n.gpkg")
schools = schools.to_crs("EPSG:32644")

school_rows = []
for _, row in schools.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue

    p = geom.representative_point()
    name = str(row.get("School_Name", "Unknown school")).strip().title()

    school_rows.append({
        "facility_id": str(row.get("School_Code", name)),
        "facility_name": name,
        "facility_type": "School",
        "priority_group": 1,
        "source": "school_compounds_utm44n.gpkg",
        "geometry": p,
    })

# Select one health-centre record only.
health = gpd.read_file(REF / "tgrac_health.gpkg").to_crs("EPSG:32644")
if len(health) != 1:
    raise ValueError(f"Expected one health record, found {len(health)}")

health_row = health.iloc[0]
health_geom = health_row.geometry
if health_geom is None or health_geom.is_empty:
    raise ValueError("Health-centre geometry is empty.")

facility_rows = school_rows + [{
    "facility_id": "HEALTH_8734223673",
    "facility_name": "Sub Centre, Damarakunta",
    "facility_type": "Healthcare",
    "priority_group": 1,
    "source": "tgrac_health.gpkg",
    "geometry": health_geom,
}]

# Select only the Anganwadi explicitly named Damarakunt-I in Damarakunta.
anganwadi = gpd.read_file(REF / "tgrac_anganwadi.gpkg").to_crs("EPSG:32644")
required = anganwadi[
    anganwadi["Anganwadi_Name"].astype(str).str.strip().str.casefold().eq("damarakunt-i")
    & anganwadi["Village_Name"].astype(str).str.strip().str.casefold().eq("damarakunta")
]

if len(required) != 1:
    raise ValueError(
        "Expected exactly one Damarakunt-I record for Damarakunta; "
        f"found {len(required)}. Inspect source coordinates before proceeding."
    )

aw = required.iloc[0]
aw_geom = aw.geometry
if aw_geom is None or aw_geom.is_empty:
    raise ValueError("Anganwadi geometry is empty.")

facility_rows.append({
    "facility_id": str(aw.get("Anganwadi_Code", "ANGANWADI")),
    "facility_name": "Damarakunt-I",
    "facility_type": "Anganwadi",
    "priority_group": 1,
    "source": "tgrac_anganwadi.gpkg",
    "geometry": aw_geom,
})

facilities = gpd.GeoDataFrame(facility_rows, geometry="geometry", crs="EPSG:32644")

# Do not overwrite an earlier result.
if OUT.exists():
    raise FileExistsError(
        f"{OUT} already exists. Rename or review it before recreating."
    )

OUT.parent.mkdir(parents=True, exist_ok=True)
facilities.to_file(OUT, layer="priority_facilities", driver="GPKG")

print("=" * 60)
print("DAMARAKUNTA PRIORITY FACILITIES")
print("=" * 60)
print("Output:", OUT)
print("Count:", len(facilities))
print(facilities[[
    "facility_id", "facility_name", "facility_type",
    "priority_group", "source"
]].to_string(index=False))

for _, row in facilities.iterrows():
    p = row.geometry
    print(
        f"{row['facility_name']}: "
        f"E={p.x:.2f} m, N={p.y:.2f} m"
    )

print("\nCreated successfully. Source files were not changed.")
