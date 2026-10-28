
import geopandas as gpd
from pathlib import Path

project = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
reference = project / "reference"

# 1. Inspect cadastral parcel identifiers
print("--- Cadastral identifiers ---")

parcel_file = reference / "damarakunta_cadastral_valid.gpkg"
parcels = gpd.read_file(parcel_file)

fields = [
    "Base_Syno",
    "DMV_1991",
    "V_2011",
    "Descriptio",
    "Remarks",
]

print(parcels[fields].head(12).to_string(index=False))

# 2. Inspect all reference GeoPackages
print("\n--- Reference vector layers ---")

keywords = [
    "drain", "stream", "water", "river", "canal",
    "culvert", "owner", "survey", "syno", "road", "type"
]

for file in sorted(reference.glob("*.gpkg")):
    try:
        layer = gpd.read_file(file)

        relevant_fields = [
            column for column in layer.columns
            if any(word in column.lower() for word in keywords)
        ]

        print(f"\nFile: {file.name}")
        print("Features:", len(layer))
        print("CRS:", layer.crs)
        print("Geometry:", layer.geom_type.value_counts().to_dict())
        print("Relevant fields:", relevant_fields)

    except Exception as error:
        print(f"\nFile: {file.name}")
        print("Read error:", error)
