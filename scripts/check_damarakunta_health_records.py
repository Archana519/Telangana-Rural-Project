
from pathlib import Path
import geopandas as gpd

BASE = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
REF = BASE / "reference"
OUT = BASE / "results"

FILES = [
    REF / "tgrac_health.gpkg",
    REF / "tgrac_sub_centres.gpkg",
    REF / "damarakunta_priority_facilities.gpkg",
    REF / "tgrac_road_network.gpkg",
]

TARGET_CRS = "EPSG:32644"


def load_layer(path):
    if not path.exists():
        print(f"\nFILE NOT FOUND: {path}")
        return None

    try:
        gdf = gpd.read_file(path)
        if gdf.crs is None:
            print(f"\nWARNING: CRS missing: {path.name}")
            return None

        if gdf.crs.to_string() != TARGET_CRS:
            gdf = gdf.to_crs(TARGET_CRS)

        print(f"\nLoaded: {path.name}")
        print(f"Features: {len(gdf)} | CRS: {gdf.crs}")
        print(f"Fields: {list(gdf.columns)}")
        return gdf

    except Exception as exc:
        print(f"\nERROR loading {path.name}: {exc}")
        return None


def show_health_records(gdf, label):
    if gdf is None:
        return

    print(f"\n--- {label} ---")

    # Show records identifiable as the Damarakunta Sub Centre.
    text_cols = [
        c for c in gdf.columns
        if gdf[c].dtype == "object" and c != "geometry"
    ]

    matches = gdf.iloc[0:0]

    for col in text_cols:
        values = gdf[col].fillna("").astype(str)
        mask = values.str.contains(
            "Damarakunta", case=False, regex=False
        ) | values.str.contains(
            "8734223673", case=False, regex=False
        )

        if mask.any():
            matches = gdf.loc[mask]
            break

    if matches.empty:
        print("No matching record found by name or identifier.")
        print("Inspect the listed fields and source records.")
        return

    for idx, row in matches.iterrows():
        geom = row.geometry
        print(f"\nRecord index: {idx}")

        for col in gdf.columns:
            if col != "geometry":
                print(f"  {col}: {row[col]}")

        if geom is not None and not geom.is_empty:
            point = geom if geom.geom_type == "Point" else geom.representative_point()
            print(f"  Easting: {point.x:.2f}")
            print(f"  Northing: {point.y:.2f}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    health = load_layer(FILES[0])
    subcentres = load_layer(FILES[1])
    facilities = load_layer(FILES[2])
    roads = load_layer(FILES[3])

    show_health_records(health, "TGRAC HEALTH")
    show_health_records(subcentres, "TGRAC SUB-CENTRES")

    if facilities is None:
        print("\nCannot check facility distances: facility layer unavailable.")
        return

    if roads is None or roads.empty:
        print("\nCannot calculate road distances: road layer unavailable.")
        return

    roads = roads[roads.geometry.notna() & ~roads.geometry.is_empty]
    road_union = roads.geometry.union_all()

    print("\n--- FACILITY-TO-ROAD DISTANCE CHECK ---")

    for _, row in facilities.iterrows():
        name = str(row.get("facility_name", row.get("name", "Unknown")))
        geom = row.geometry

        if geom is None or geom.is_empty:
            continue

        point = geom if geom.geom_type == "Point" else geom.representative_point()
        distance = point.distance(road_union)

        print(
            f"{name}: nearest mapped road = "
            f"{distance:.2f} m"
        )

    print("\nCHECK COMPLETE.")
    print("These are geometric distances, not proof of usable entrances.")
    print("Compare duplicate health coordinates against official records.")
    print("Do not select a health-centre location solely by nearest-road distance.")


if __name__ == "__main__":
    main()
