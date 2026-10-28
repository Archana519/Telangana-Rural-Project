import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 6: BATCH-PROCESSING READINESS
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
    "phase25_batch_readiness.csv"
)

print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 6 - BATCH-PROCESSING READINESS")
print("=" * 80)


# ============================================================
# REQUIRED PIPELINE OUTPUTS
# ============================================================

REQUIRED_RESULTS = [
    "phase18_facility_road_connections.csv",
    "phase18_new_road_candidates.csv",
    "phase18_new_road_candidate_evaluation.csv",
    "phase19_candidate_existing_road_comparison.csv",
    "phase19_multi_criteria_evaluation.csv",
    "phase20_route_evaluation.csv",
    "phase21_before_after_connectivity.csv",
    "phase22_fair_comparison.csv",
    "phase23_ablation_study.csv",
    "phase24_sensitivity_analysis.csv"
]


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
# 3. CHECK PIPELINE OUTPUTS
# ============================================================

records = []

print("\n" + "=" * 80)
print("CHECKING PIPELINE OUTPUTS")
print("=" * 80)

for village in villages:

    village_root = os.path.join(
        DISTRICT_ROOT,
        village
    )

    results_dir = os.path.join(
        village_root,
        "results"
    )

    found_results = []
    missing_results = []

    for filename in REQUIRED_RESULTS:

        path = os.path.join(
            results_dir,
            filename
        )

        if os.path.isfile(path):

            found_results.append(filename)

        else:

            missing_results.append(filename)

    found_count = len(found_results)
    missing_count = len(missing_results)

    if missing_count == 0:

        readiness = "BATCH_READY"

    elif found_count >= 7:

        readiness = "PARTIALLY_READY"

    else:

        readiness = "NOT_READY"

    print("\nVillage:", village)

    print(
        f"Results found: {found_count}/{len(REQUIRED_RESULTS)}"
    )

    if missing_count == 0:

        print("[READY] All required pipeline results are present.")

    else:

        print(
            "[MISSING]",
            ", ".join(missing_results)
        )

    records.append(
        {
            "district": "Siddipet",
            "village": village,
            "results_found": found_count,
            "results_required": len(REQUIRED_RESULTS),
            "results_missing": missing_count,
            "readiness": readiness,
            "missing_result_files": "; ".join(
                missing_results
            ),
            "results_dir": results_dir
        }
    )


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
print("BATCH READINESS REPORT")
print("=" * 80)

if len(df) > 0:

    print(
        df[
            [
                "district",
                "village",
                "results_found",
                "results_required",
                "results_missing",
                "readiness",
                "missing_result_files"
            ]
        ].to_string(index=False)
    )

else:

    print("No villages found.")


# ============================================================
# 6. SUMMARY
# ============================================================

batch_ready = int(
    (df["readiness"] == "BATCH_READY").sum()
) if len(df) > 0 else 0

partial = int(
    (df["readiness"] == "PARTIALLY_READY").sum()
) if len(df) > 0 else 0

not_ready = int(
    (df["readiness"] == "NOT_READY").sum()
) if len(df) > 0 else 0

print("\n" + "=" * 80)
print("PHASE 25 STEP 6 SUMMARY")
print("=" * 80)

print(f"Villages checked : {len(df)}")
print(f"Batch ready      : {batch_ready}")
print(f"Partially ready  : {partial}")
print(f"Not ready        : {not_ready}")

print("\nReport saved to:")
print(OUTPUT_FILE)

if batch_ready == len(df) and len(df) > 0:

    print(
        "\nSTATUS: ALL DISCOVERED VILLAGES "
        "HAVE THE REQUIRED PIPELINE OUTPUTS."
    )

elif batch_ready > 0:

    print(
        "\nSTATUS: SOME VILLAGES ARE READY "
        "AND SOME REQUIRE PROCESSING."
    )

else:

    print(
        "\nSTATUS: VILLAGES REQUIRE "
        "ADDITIONAL PIPELINE PROCESSING."
    )

print("\nImportant:")
print("This is a readiness check only.")
print("It does not rerun segmentation, routing, or evaluation.")
print("It does not establish scientific validity of the outputs.")