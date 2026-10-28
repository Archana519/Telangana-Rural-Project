import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 1: VILLAGE CONFIGURATION AND READINESS CHECK
# ============================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

VILLAGES = [
    {
        "district": "Siddipet",
        "mandal": "Markook",
        "village": "Angadi_Kistapur",
        "status": "COMPLETED"
    }
]

print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 1 - VILLAGE CONFIGURATION AND READINESS CHECK")
print("=" * 80)

print("\nConfigured villages:")
print("-" * 80)

for village in VILLAGES:
    print(
        f"District : {village['district']}\n"
        f"Mandal   : {village['mandal']}\n"
        f"Village  : {village['village']}\n"
        f"Status   : {village['status']}\n"
    )

# ============================================================
# CHECK CURRENT VILLAGE OUTPUTS
# ============================================================

print("=" * 80)
print("CHECKING ANGADI KISTAPUR OUTPUTS")
print("=" * 80)

village_root = os.path.join(
    PROJECT_ROOT,
    "Siddipet",
    "Angadi_Kistapur"
)

required_files = [
    "study_area",
    "raw",
    "reference",
    "aligned",
    "derived",
    "results"
]

for folder in required_files:

    path = os.path.join(village_root, folder)

    if os.path.exists(path):
        print(f"[OK] Folder exists: {folder}")
    else:
        print(f"[MISSING] Folder: {folder}")


# ============================================================
# IMPORTANT RESULT FILES
# ============================================================

results_dir = os.path.join(
    village_root,
    "results"
)

important_results = [
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

print("\n" + "=" * 80)
print("CHECKING COMPLETED PHASE RESULTS")
print("=" * 80)

found = 0
missing = 0

for filename in important_results:

    path = os.path.join(results_dir, filename)

    if os.path.exists(path):
        print(f"[OK]      {filename}")
        found += 1
    else:
        print(f"[MISSING] {filename}")
        missing += 1


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("PHASE 25 STEP 1 SUMMARY")
print("=" * 80)

print(f"Configured villages : {len(VILLAGES)}")
print(f"Result files found  : {found}")
print(f"Result files missing: {missing}")

if missing == 0:
    print("\nSTATUS: ANGADI KISTAPUR IS READY AS THE REFERENCE VILLAGE.")
else:
    print("\nSTATUS: SOME OUTPUTS ARE MISSING.")

print("\nNext step:")
print("Add a second rural village only after its required GIS/imagery")
print("data are available and the same pipeline can be applied.")