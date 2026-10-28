
from pathlib import Path
import geopandas as gpd
import pandas as pd

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
OUT = BASE / "results"
OUT.mkdir(parents=True, exist_ok=True)

health_file = REF / "tgrac_health.gpkg"
subcentre_file = REF / "tgrac_sub_centres.gpkg"
facilities_file = REF / "damarakunta_priority_facilities.gpkg"

health = gpd.read_file(health_file).to_crs("EPSG:32644")
subcentres = gpd.read_file(subcentre_file).to_crs("EPSG:32644")
facilities = gpd.read_file(facilities_file).to_crs("EPSG:32644")

h = health.iloc[0]
s = subcentres.iloc[0]

hp = h.geometry
sp = s.geometry

distance = hp.distance(sp)

report = pd.DataFrame([
    {
        "source": "tgrac_health.gpkg",
        "facility_name": h.get("Facility_Name"),
        "nin_id": h.get("NIN_ID"),
        "latitude": h.get("Latitude"),
        "longitude": h.get("Longitude"),
        "easting": hp.x,
        "northing": hp.y,
        "distance_between_records_m": distance,
    },
    {
        "source": "tgrac_sub_centres.gpkg",
        "facility_name": s.get("Facility_Name"),
        "nin_id": s.get("NIN_ID"),
        "latitude": s.get("Latitude"),
        "longitude": s.get("Longitude"),
        "easting": sp.x,
        "northing": sp.y,
        "distance_between_records_m": distance,
    },
])

csv_path = OUT / "damarakunta_health_record_comparison.csv"
report.to_csv(csv_path, index=False)

print("HEALTH RECORD COMPARISON COMPLETE")
print(f"Distance between records: {distance:.2f} m")
print(f"Report saved: {csv_path}")
print("\nExisting priority-facility record:")
print(
    facilities[
        facilities["facility_id"].astype(str).str.contains(
            "HEALTH_8734223673", case=False, regex=False
        )
    ].to_string(index=False)
)
print("\nIMPORTANT: This report compares records; it does not determine which coordinate is correct.")
