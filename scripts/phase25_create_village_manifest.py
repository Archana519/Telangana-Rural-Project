import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 5: MULTI-VILLAGE PROCESSING MANIFEST
# ============================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"
DISTRICT_ROOT = os.path.join(
    PROJECT_ROOT,
    "Siddipet"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "docs",
    "village_template"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_village_processing_manifest.csv"
)

print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 5 - MULTI-VILLAGE PROCESSING MANIFEST")
print("=" * 80)


# ============================================================
# 1. CHECK DISTRICT DIRECTORY
# ============================================================

if not os.path.isdir(DISTRICT_ROOT):

    print("[ERROR] District directory not found:")
    print(DISTRICT_ROOT)

    raise SystemExit(1)

print(f"\n[OK] District directory: {DISTRICT_ROOT}")


# ============================================================
# 2. DISCOVER VILLAGES
# ============================================================

villages = []

for name in sorted(os.listdir(DISTRICT_ROOT)):

    path = os.path.join(
        DISTRICT_ROOT,
        name
    )

    if os.path.isdir(path):
        villages.append(name)

print(f"[OK] Villages discovered: {len(villages)}")


# ============================================================
# 3. CREATE MANIFEST
# ============================================================

records = []

for village in villages:

    village_root = os.path.join(
        DISTRICT_ROOT,
        village
    )

    imagery_dir = os.path.join(
        village_root,
        "raw",
        "imagery"
    )

    dem_dir = os.path.join(
        village_root,
        "raw",
        "dem"
    )

    landcover_dir = os.path.join(
        village_root,
        "raw",
        "landcover"
    )

    study_area_dir = os.path.join(
        village_root,
        "study_area"
    )

    reference_dir = os.path.join(
        village_root,
        "reference"
    )

    aligned_dir = os.path.join(
        village_root,
        "aligned"
    )

    predictions_dir = os.path.join(
        village_root,
        "predictions"
    )

    results_dir = os.path.join(
        village_root,
        "results"
    )

    records.append(
        {
            "district": "Siddipet",
            "village": village,

            "village_root": village_root,

            "study_area_dir": study_area_dir,

            "imagery_dir": imagery_dir,

            "dem_dir": dem_dir,

            "landcover_dir": landcover_dir,

            "reference_dir": reference_dir,

            "aligned_dir": aligned_dir,

            "predictions_dir": predictions_dir,

            "results_dir": results_dir,

            "status": "READY"
        }
    )


# ============================================================
# 4. CREATE DATAFRAME
# ============================================================

manifest = pd.DataFrame(records)


# ============================================================
# 5. SAVE MANIFEST
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

manifest.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 6. DISPLAY MANIFEST
# ============================================================

print("\n" + "=" * 80)
print("MULTI-VILLAGE PROCESSING MANIFEST")
print("=" * 80)

if len(manifest) > 0:

    print(
        manifest[
            [
                "district",
                "village",
                "village_root",
                "study_area_dir",
                "imagery_dir",
                "dem_dir",
                "landcover_dir",
                "reference_dir",
                "aligned_dir",
                "predictions_dir",
                "results_dir",
                "status"
            ]
        ].to_string(index=False)
    )

else:

    print("No villages found.")


# ============================================================
# 7. VERIFY PATHS
# ============================================================

print("\n" + "=" * 80)
print("VERIFYING MANIFEST PATHS")
print("=" * 80)

path_columns = [
    "village_root",
    "study_area_dir",
    "imagery_dir",
    "dem_dir",
    "landcover_dir",
    "reference_dir",
    "aligned_dir",
    "predictions_dir",
    "results_dir"
]

path_errors = 0

for _, row in manifest.iterrows():

    print(f"\nVillage: {row['village']}")

    for column in path_columns:

        path = row[column]

        if os.path.isdir(path):

            print(f"[OK] {column}")

        else:

            print(f"[MISSING] {column}")
            path_errors += 1


# ============================================================
# 8. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("PHASE 25 STEP 5 SUMMARY")
print("=" * 80)

print(f"Villages in manifest : {len(manifest)}")
print(f"Path errors          : {path_errors}")

print("\nManifest saved to:")
print(OUTPUT_FILE)

if path_errors == 0 and len(manifest) > 0:

    print("\nSTATUS: MULTI-VILLAGE PROCESSING MANIFEST READY.")

else:

    print("\nSTATUS: MANIFEST VERIFICATION REQUIRES ATTENTION.")

print("\nImportant:")
print("The manifest records paths for discovered villages.")
print("It does not claim that a village has been scientifically processed.")