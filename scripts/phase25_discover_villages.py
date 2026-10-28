import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 3: MULTI-VILLAGE DISCOVERY AND VALIDATION
# ============================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"
DISTRICT_ROOT = os.path.join(PROJECT_ROOT, "Siddipet")

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "docs",
    "village_template"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_village_readiness.csv"
)

# Standard folders required for every village
REQUIRED_FOLDERS = [
    "study_area",
    "raw",
    "reference",
    "aligned",
    "derived",
    "predictions",
    "results"
]

print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 3 - MULTI-VILLAGE DISCOVERY AND VALIDATION")
print("=" * 80)

# ============================================================
# 1. CHECK DISTRICT DIRECTORY
# ============================================================

print("\nChecking district directory...")

if not os.path.isdir(DISTRICT_ROOT):
    print("[ERROR] District directory not found:")
    print(DISTRICT_ROOT)
    raise SystemExit(1)

print(f"[OK] District directory exists: {DISTRICT_ROOT}")


# ============================================================
# 2. DISCOVER VILLAGE DIRECTORIES
# ============================================================

print("\n" + "=" * 80)
print("DISCOVERING VILLAGE DIRECTORIES")
print("=" * 80)

village_names = []

for name in sorted(os.listdir(DISTRICT_ROOT)):

    path = os.path.join(
        DISTRICT_ROOT,
        name
    )

    if os.path.isdir(path):
        village_names.append(name)

if len(village_names) == 0:

    print("[WARNING] No village directories found.")

else:

    for village in village_names:
        print(f"[FOUND] {village}")

print(f"\nVillages discovered: {len(village_names)}")


# ============================================================
# 3. VALIDATE EACH VILLAGE
# ============================================================

print("\n" + "=" * 80)
print("VALIDATING VILLAGE STRUCTURES")
print("=" * 80)

records = []

for village in village_names:

    village_root = os.path.join(
        DISTRICT_ROOT,
        village
    )

    missing_folders = []

    for folder in REQUIRED_FOLDERS:

        folder_path = os.path.join(
            village_root,
            folder
        )

        if not os.path.isdir(folder_path):
            missing_folders.append(folder)

    if len(missing_folders) == 0:
        readiness = "READY"
    else:
        readiness = "INCOMPLETE"

    records.append(
        {
            "district": "Siddipet",
            "village": village,
            "readiness": readiness,
            "missing_folders": ", ".join(missing_folders),
            "village_path": village_root
        }
    )

    if readiness == "READY":

        print(
            f"[READY] {village}"
        )

    else:

        print(
            f"[INCOMPLETE] {village} "
            f"| Missing: {', '.join(missing_folders)}"
        )


# ============================================================
# 4. SAVE READINESS REPORT
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

df = pd.DataFrame(records)

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 80)
print("READINESS REPORT")
print("=" * 80)

print(df.to_string(index=False))


# ============================================================
# 5. SUMMARY
# ============================================================

ready_count = int(
    (df["readiness"] == "READY").sum()
) if len(df) > 0 else 0

incomplete_count = int(
    (df["readiness"] == "INCOMPLETE").sum()
) if len(df) > 0 else 0

print("\n" + "=" * 80)
print("PHASE 25 STEP 3 SUMMARY")
print("=" * 80)

print(f"Villages discovered : {len(village_names)}")
print(f"Villages ready      : {ready_count}")
print(f"Villages incomplete : {incomplete_count}")

print("\nReadiness report:")
print(OUTPUT_FILE)

if incomplete_count == 0 and ready_count > 0:

    print("\nSTATUS: ALL DISCOVERED VILLAGES HAVE THE STANDARD STRUCTURE.")

elif ready_count > 0:

    print("\nSTATUS: SOME VILLAGES ARE READY AND SOME ARE INCOMPLETE.")

else:

    print("\nSTATUS: NO READY VILLAGES FOUND.")

print("\nImportant:")
print("This step validates folder structure only.")
print("It does not claim that imagery, GIS layers, or model outputs")
print("exist or are scientifically valid for every village.")