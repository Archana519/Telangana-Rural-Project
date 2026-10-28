import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 4: VILLAGE INPUT-DATA READINESS VALIDATION
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
    "phase25_village_input_readiness.csv"
)

# ============================================================
# REQUIRED INPUT CATEGORIES
# ============================================================

INPUT_CHECKS = {
    "imagery": [
        os.path.join(
            "raw",
            "imagery"
        )
    ],

    "study_area": [
        os.path.join(
            "study_area"
        )
    ],

    "dem": [
        os.path.join(
            "raw",
            "dem"
        )
    ],

    "landcover": [
        os.path.join(
            "raw",
            "landcover"
        )
    ],

    "reference_data": [
        os.path.join(
            "reference"
        )
    ],

    "aligned_data": [
        os.path.join(
            "aligned"
        )
    ]
}


print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 4 - VILLAGE INPUT-DATA READINESS VALIDATION")
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
# 3. VALIDATE INPUT CATEGORIES
# ============================================================

print("\n" + "=" * 80)
print("INPUT-DATA VALIDATION")
print("=" * 80)

records = []

for village in villages:

    village_root = os.path.join(
        DISTRICT_ROOT,
        village
    )

    print("\n" + "-" * 80)
    print(f"Village: {village}")
    print("-" * 80)

    category_status = {}

    for category, relative_paths in INPUT_CHECKS.items():

        found = False
        found_paths = []

        for relative_path in relative_paths:

            full_path = os.path.join(
                village_root,
                relative_path
            )

            if not os.path.isdir(full_path):
                continue

            try:
                entries = os.listdir(full_path)
            except PermissionError:
                entries = []

            files = [
                item
                for item in entries
                if os.path.isfile(
                    os.path.join(
                        full_path,
                        item
                    )
                )
            ]

            if len(files) > 0:

                found = True
                found_paths.append(
                    relative_path
                )

        if found:

            category_status[category] = "AVAILABLE"

            print(
                f"[AVAILABLE] {category}"
            )

        else:

            category_status[category] = "MISSING_OR_EMPTY"

            print(
                f"[MISSING/EMPTY] {category}"
            )

    available_count = sum(
        value == "AVAILABLE"
        for value in category_status.values()
    )

    total_categories = len(category_status)

    if available_count == total_categories:

        readiness = "INPUTS_READY"

    elif available_count >= 4:

        readiness = "PARTIALLY_READY"

    else:

        readiness = "NOT_READY"

    record = {
        "district": "Siddipet",
        "village": village,
        "imagery": category_status["imagery"],
        "study_area": category_status["study_area"],
        "dem": category_status["dem"],
        "landcover": category_status["landcover"],
        "reference_data": category_status["reference_data"],
        "aligned_data": category_status["aligned_data"],
        "available_categories": available_count,
        "total_categories": total_categories,
        "readiness": readiness,
        "village_path": village_root
    }

    records.append(record)


# ============================================================
# 4. SAVE REPORT
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


# ============================================================
# 5. DISPLAY REPORT
# ============================================================

print("\n" + "=" * 80)
print("VILLAGE INPUT READINESS REPORT")
print("=" * 80)

if len(df) > 0:

    print(
        df[
            [
                "district",
                "village",
                "imagery",
                "study_area",
                "dem",
                "landcover",
                "reference_data",
                "aligned_data",
                "available_categories",
                "total_categories",
                "readiness"
            ]
        ].to_string(index=False)
    )

else:

    print("No villages found.")


# ============================================================
# 6. SUMMARY
# ============================================================

ready_count = int(
    (df["readiness"] == "INPUTS_READY").sum()
) if len(df) > 0 else 0

partial_count = int(
    (df["readiness"] == "PARTIALLY_READY").sum()
) if len(df) > 0 else 0

not_ready_count = int(
    (df["readiness"] == "NOT_READY").sum()
) if len(df) > 0 else 0

print("\n" + "=" * 80)
print("PHASE 25 STEP 4 SUMMARY")
print("=" * 80)

print(f"Villages checked     : {len(df)}")
print(f"Inputs ready         : {ready_count}")
print(f"Partially ready      : {partial_count}")
print(f"Not ready            : {not_ready_count}")

print("\nReport saved to:")
print(OUTPUT_FILE)

print("\nImportant:")
print("This step checks whether expected input directories contain files.")
print("It does NOT verify data quality, CRS correctness, spatial coverage,")
print("classification accuracy, or scientific validity.")