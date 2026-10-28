import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 7 - MULTI-VILLAGE PROCESSING SUMMARY
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

READINESS_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_village_readiness.csv"
)

INPUT_READINESS_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_village_input_readiness.csv"
)

MANIFEST_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_village_processing_manifest.csv"
)

BATCH_READINESS_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_batch_readiness.csv"
)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_processing_summary.csv"
)

print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 7 - MULTI-VILLAGE PROCESSING SUMMARY")
print("=" * 80)


# ============================================================
# 1. LOAD CSV SAFELY
# ============================================================

def load_report(path, name):

    if not os.path.isfile(path):

        print(f"[MISSING] {name}: {path}")

        return pd.DataFrame()

    try:

        df = pd.read_csv(path)

        print(
            f"[OK] Loaded {name}: "
            f"{len(df)} record(s)"
        )

        print(
            f"     Columns: {list(df.columns)}"
        )

        return df

    except Exception as e:

        print(
            f"[ERROR] Could not load {name}: {e}"
        )

        return pd.DataFrame()


print("\n" + "=" * 80)
print("LOADING PHASE 25 REPORTS")
print("=" * 80)

village_readiness = load_report(
    READINESS_FILE,
    "village readiness"
)

input_readiness = load_report(
    INPUT_READINESS_FILE,
    "input readiness"
)

manifest = load_report(
    MANIFEST_FILE,
    "processing manifest"
)

batch_readiness = load_report(
    BATCH_READINESS_FILE,
    "batch readiness"
)


# ============================================================
# 2. DISCOVER VILLAGES DIRECTLY FROM DISTRICT FOLDER
# ============================================================

print("\n" + "=" * 80)
print("DISCOVERING VILLAGES")
print("=" * 80)

villages = []

if os.path.isdir(DISTRICT_ROOT):

    for name in sorted(
        os.listdir(DISTRICT_ROOT)
    ):

        path = os.path.join(
            DISTRICT_ROOT,
            name
        )

        if os.path.isdir(path):

            villages.append(name)

print(
    f"[OK] Villages discovered: {len(villages)}"
)

for village in villages:

    print(
        f"     - {village}"
    )


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def get_village_rows(df, village):

    if df.empty:
        return pd.DataFrame()

    if "village" not in df.columns:
        return pd.DataFrame()

    return df[
        df["village"]
        .astype(str)
        .str.strip()
        == village
    ]


def row_contains_text(row, keywords):

    for value in row.tolist():

        text_value = str(value).upper()

        for keyword in keywords:

            if keyword in text_value:

                return True

    return False


# ============================================================
# 4. CHECK FOLDER STRUCTURE
# ============================================================

def check_folder_structure(village):

    village_root = os.path.join(
        DISTRICT_ROOT,
        village
    )

    required_dirs = [
        "study_area",
        os.path.join("raw", "imagery"),
        os.path.join("raw", "dem"),
        os.path.join("raw", "landcover"),
        "reference",
        "aligned",
        "predictions",
        "results"
    ]

    missing = []

    for relative_dir in required_dirs:

        path = os.path.join(
            village_root,
            relative_dir
        )

        if not os.path.isdir(path):

            missing.append(relative_dir)

    return len(missing) == 0, missing


# ============================================================
# 5. CHECK INPUT READINESS
# ============================================================

def check_input_readiness(village):

    rows = get_village_rows(
        input_readiness,
        village
    )

    if rows.empty:

        return False

    row = rows.iloc[0]

    # Look for explicit readiness text anywhere
    if row_contains_text(
        row,
        [
            "INPUTS_READY",
            "READY"
        ]
    ):

        return True

    # Check numerical category readiness
    numeric_ready = []

    for value in row.tolist():

        text_value = str(value).strip()

        if text_value in [
            "6/6",
            "6"
        ]:

            numeric_ready.append(True)

    if numeric_ready:

        return True

    return False


# ============================================================
# 6. CHECK MANIFEST
# ============================================================

def check_manifest(village):

    rows = get_village_rows(
        manifest,
        village
    )

    if rows.empty:

        return False

    row = rows.iloc[0]

    # First check explicit status
    if row_contains_text(
        row,
        [
            "READY"
        ]
    ):

        return True

    # If all expected directory columns exist,
    # verify the actual paths.
    manifest_columns = [
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

    existing_columns = [
        column
        for column in manifest_columns
        if column in rows.columns
    ]

    if len(existing_columns) == len(
        manifest_columns
    ):

        all_exist = True

        for column in existing_columns:

            path = str(
                row[column]
            )

            if not os.path.exists(path):

                all_exist = False

        if all_exist:

            return True

    return False


# ============================================================
# 7. CHECK BATCH RESULTS
# ============================================================

def check_batch_results(village):

    rows = get_village_rows(
        batch_readiness,
        village
    )

    if rows.empty:

        return False, 0, 0

    row = rows.iloc[0]

    # Get result counts
    try:

        found = int(
            row.get(
                "results_found",
                0
            )
        )

    except Exception:

        found = 0

    try:

        required = int(
            row.get(
                "results_required",
                0
            )
        )

    except Exception:

        required = 0

    # Explicit BATCH_READY check
    readiness_value = str(
        row.get(
            "readiness",
            ""
        )
    ).upper().strip()

    if readiness_value == "BATCH_READY":

        return True, found, required

    # Fallback based on counts
    if (
        required > 0
        and found == required
    ):

        return True, found, required

    return False, found, required


# ============================================================
# 8. CREATE SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("CREATING MULTI-VILLAGE SUMMARY")
print("=" * 80)

summary_records = []

for village in villages:

    folder_ready, missing_dirs = (
        check_folder_structure(village)
    )

    input_ready = check_input_readiness(
        village
    )

    manifest_ready = check_manifest(
        village
    )

    batch_ready, results_found, results_required = (
        check_batch_results(village)
    )

    if (
        folder_ready
        and input_ready
        and manifest_ready
        and batch_ready
    ):

        overall_status = (
            "READY_FOR_MULTI_VILLAGE_PIPELINE"
        )

    elif (
        folder_ready
        or input_ready
        or manifest_ready
        or batch_ready
    ):

        overall_status = (
            "PARTIALLY_READY"
        )

    else:

        overall_status = "NOT_READY"

    summary_records.append(
        {
            "district": "Siddipet",
            "village": village,
            "folder_structure_ready": folder_ready,
            "input_data_ready": input_ready,
            "manifest_ready": manifest_ready,
            "batch_results_ready": batch_ready,
            "pipeline_results_found": results_found,
            "pipeline_results_required": results_required,
            "missing_directories": "; ".join(
                missing_dirs
            ),
            "overall_status": overall_status
        }
    )

    print(
        f"\nVillage: {village}"
    )

    print(
        f"  Folder structure : "
        f"{'READY' if folder_ready else 'NOT READY'}"
    )

    print(
        f"  Input data       : "
        f"{'READY' if input_ready else 'NOT READY'}"
    )

    print(
        f"  Manifest         : "
        f"{'READY' if manifest_ready else 'NOT READY'}"
    )

    print(
        f"  Pipeline results : "
        f"{results_found}/{results_required}"
    )

    print(
        f"  Batch results    : "
        f"{'READY' if batch_ready else 'NOT READY'}"
    )

    print(
        f"  Overall status   : "
        f"{overall_status}"
    )


# ============================================================
# 9. SAVE SUMMARY
# ============================================================

summary_df = pd.DataFrame(
    summary_records
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

summary_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 10. DISPLAY FINAL TABLE
# ============================================================

print("\n" + "=" * 80)
print("MULTI-VILLAGE PROCESSING SUMMARY")
print("=" * 80)

if not summary_df.empty:

    print(
        summary_df.to_string(
            index=False
        )
    )

else:

    print("No villages found.")


# ============================================================
# 11. FINAL COUNTS
# ============================================================

if not summary_df.empty:

    fully_ready = int(
        (
            summary_df[
                "overall_status"
            ]
            == "READY_FOR_MULTI_VILLAGE_PIPELINE"
        ).sum()
    )

    partially_ready = int(
        (
            summary_df[
                "overall_status"
            ]
            == "PARTIALLY_READY"
        ).sum()
    )

    not_ready = int(
        (
            summary_df[
                "overall_status"
            ]
            == "NOT_READY"
        ).sum()
    )

else:

    fully_ready = 0
    partially_ready = 0
    not_ready = 0


# ============================================================
# 12. FINAL STATUS
# ============================================================

print("\n" + "=" * 80)
print("PHASE 25 STEP 7 SUMMARY")
print("=" * 80)

print(
    f"Villages summarized : {len(summary_df)}"
)

print(
    f"Fully ready         : {fully_ready}"
)

print(
    f"Partially ready     : {partially_ready}"
)

print(
    f"Not ready           : {not_ready}"
)

print("\nSummary saved to:")
print(OUTPUT_FILE)

print("\nImportant:")
print(
    "This summary consolidates the Phase 25 "
    "folder, input, manifest, and pipeline "
    "readiness checks."
)

print(
    "It does not establish scientific validity, "
    "segmentation accuracy, or field validation."
)

print(
    "It does not rerun AI, GIS, routing, "
    "or evaluation processing."
)

if (
    len(summary_df) > 0
    and fully_ready == len(summary_df)
):

    print(
        "\nSTATUS: ALL DISCOVERED VILLAGES ARE "
        "READY FOR THE MULTI-VILLAGE PIPELINE."
    )

else:

    print(
        "\nSTATUS: SOME VILLAGES REQUIRE "
        "ADDITIONAL PREPARATION."
    )

print(
    "\nPHASE 25 STEP 7 COMPLETED."
)