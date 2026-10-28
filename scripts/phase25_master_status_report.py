import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 10 - UPDATED MASTER PROJECT STATUS REPORT
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
    "phase25_master_project_status.csv"
)

print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 10 - MASTER PROJECT STATUS REPORT")
print("=" * 80)


# ============================================================
# PHASE STATUS
# ============================================================

PHASES = [
    ("PHASE 0", "Project Setup", "COMPLETED"),
    ("PHASE 1", "Existing Project Audit", "COMPLETED"),
    ("PHASE 2", "Verify Angadi Kistapur", "COMPLETED"),
    ("PHASE 3", "Inspect TGRAC Data", "COMPLETED"),
    ("PHASE 4", "Imagery Decision", "COMPLETED"),
    ("PHASE 5", "Obtain / Prepare Real Imagery", "COMPLETED"),
    ("PHASE 6", "Image / GeoTIFF Inspection", "COMPLETED"),
    ("PHASE 7", "Village Preparation", "COMPLETED"),
    ("PHASE 8", "UTM / Georeferencing", "COMPLETED"),
    ("PHASE 9", "GIS Reference Data", "COMPLETED"),
    ("PHASE 10", "StrongDINOv2Seg", "COMPLETED"),
    ("PHASE 11", "Model Input Preparation", "COMPLETED"),
    ("PHASE 12", "Segmentation", "COMPLETED"),
    ("PHASE 13", "Building / Road Extraction", "COMPLETED"),
    ("PHASE 14", "Facility Identification", "COMPLETED"),
    ("PHASE 15", "Accessibility Analysis", "COMPLETED"),
    ("PHASE 16", "Priority Assignment", "COMPLETED"),
    ("PHASE 17", "Cost Surface", "COMPLETED"),
    ("PHASE 18", "Candidate Routes", "COMPLETED"),
    ("PHASE 19", "Routing Comparison", "COMPLETED"),
    ("PHASE 20", "Route Evaluation", "COMPLETED"),
    ("PHASE 21", "Before / After Connectivity", "COMPLETED"),
    ("PHASE 22", "Fair Comparison", "COMPLETED"),
    ("PHASE 23", "Ablation Study", "COMPLETED"),
    ("PHASE 24", "Sensitivity Analysis", "COMPLETED"),
    ("PHASE 25", "Multiple Villages", "IN PROGRESS"),
    ("PHASE 26", "Final Outputs", "PENDING"),
]


# ============================================================
# PHASE 25 STEP STATUS
# ============================================================

PHASE25_STEPS = [
    ("Step 1", "Village configuration", "COMPLETED"),
    ("Step 2", "Village template", "COMPLETED"),
    ("Step 3", "Village discovery", "COMPLETED"),
    ("Step 4", "Village input validation", "COMPLETED"),
    ("Step 5", "Village processing manifest", "COMPLETED"),
    ("Step 6", "Batch readiness", "COMPLETED"),
    ("Step 7", "Processing summary", "COMPLETED"),
    ("Step 8", "Master status preparation", "COMPLETED"),
    ("Step 9", "Village expansion checklist", "COMPLETED"),
    ("Step 10", "Updated master status report", "COMPLETED"),
]


# ============================================================
# DISCOVER VILLAGES
# ============================================================

if not os.path.isdir(DISTRICT_ROOT):

    print("[ERROR] District directory not found:")
    print(DISTRICT_ROOT)

    raise SystemExit(1)


villages = []

for name in sorted(os.listdir(DISTRICT_ROOT)):

    path = os.path.join(
        DISTRICT_ROOT,
        name
    )

    if os.path.isdir(path):

        villages.append(name)


# ============================================================
# CHECK PHASE 25 OUTPUTS
# ============================================================

required_outputs = [
    "phase18_facility_road_connections.csv",
    "phase18_new_road_candidates.csv",
    "phase18_new_road_candidate_evaluation.csv",
    "phase19_candidate_existing_road_comparison.csv",
    "phase19_multi_criteria_evaluation.csv",
    "phase20_route_evaluation.csv",
    "phase21_before_after_connectivity.csv",
    "phase22_fair_comparison.csv",
    "phase23_ablation_study.csv",
    "phase24_sensitivity_analysis.csv",
]

village_result_records = []

for village in villages:

    village_results = os.path.join(
        DISTRICT_ROOT,
        village,
        "results"
    )

    found = 0
    missing_files = []

    for filename in required_outputs:

        filepath = os.path.join(
            village_results,
            filename
        )

        if os.path.isfile(filepath):

            found += 1

        else:

            missing_files.append(filename)


    if found == len(required_outputs):

        result_status = "READY"

    else:

        result_status = "INCOMPLETE"


    village_result_records.append(
        {
            "district": "Siddipet",
            "village": village,
            "required_result_files": len(required_outputs),
            "result_files_found": found,
            "result_files_missing": len(missing_files),
            "result_status": result_status,
            "missing_files": "; ".join(missing_files)
        }
    )


# ============================================================
# CREATE MASTER PHASE TABLE
# ============================================================

phase_records = []

for phase_id, phase_name, status in PHASES:

    phase_records.append(
        {
            "phase": phase_id,
            "phase_name": phase_name,
            "status": status
        }
    )


phase_df = pd.DataFrame(
    phase_records
)


# ============================================================
# CREATE PHASE 25 STEP TABLE
# ============================================================

step_records = []

for step_id, step_name, status in PHASE25_STEPS:

    step_records.append(
        {
            "step": step_id,
            "step_name": step_name,
            "status": status
        }
    )


step_df = pd.DataFrame(
    step_records
)


# ============================================================
# SAVE MASTER REPORT
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

phase_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY PHASE STATUS
# ============================================================

print("\n" + "=" * 80)
print("OVERALL PROJECT PHASE STATUS")
print("=" * 80)

print(
    phase_df.to_string(
        index=False
    )
)


# ============================================================
# DISPLAY PHASE 25 STEPS
# ============================================================

print("\n" + "=" * 80)
print("PHASE 25 STEP STATUS")
print("=" * 80)

print(
    step_df.to_string(
        index=False
    )
)


# ============================================================
# DISPLAY VILLAGE RESULT STATUS
# ============================================================

print("\n" + "=" * 80)
print("CURRENT VILLAGE RESULT STATUS")
print("=" * 80)

village_results_df = pd.DataFrame(
    village_result_records
)

if len(village_results_df) > 0:

    print(
        village_results_df.to_string(
            index=False
        )
    )

else:

    print("No villages discovered.")


# ============================================================
# SUMMARY
# ============================================================

completed_phases = int(
    (
        phase_df["status"]
        == "COMPLETED"
    ).sum()
)

in_progress_phases = int(
    (
        phase_df["status"]
        == "IN PROGRESS"
    ).sum()
)

pending_phases = int(
    (
        phase_df["status"]
        == "PENDING"
    ).sum()
)

completed_phase25_steps = int(
    (
        step_df["status"]
        == "COMPLETED"
    ).sum()
)

ready_villages = int(
    (
        village_results_df["result_status"]
        == "READY"
    ).sum()
) if len(village_results_df) > 0 else 0


print("\n" + "=" * 80)
print("MASTER STATUS SUMMARY")
print("=" * 80)

print(
    f"Completed phases       : {completed_phases}"
)

print(
    f"Phases in progress     : {in_progress_phases}"
)

print(
    f"Pending phases         : {pending_phases}"
)

print(
    f"Phase 25 steps done    : "
    f"{completed_phase25_steps}/{len(PHASE25_STEPS)}"
)

print(
    f"Villages discovered    : {len(villages)}"
)

print(
    f"Villages result-ready  : {ready_villages}"
)


# ============================================================
# PROJECT METHODOLOGY NOTES
# ============================================================

print("\n" + "=" * 80)
print("PROJECT METHODOLOGY NOTES")
print("=" * 80)

print(
    "1. The final project domain is rural villages."
)

print(
    "2. LoveDA is treated as technical/model-development "
    "context and not as the final rural study domain."
)

print(
    "3. Public-service facilities are the first priority group."
)

print(
    "4. Residential areas are the second priority group."
)

print(
    "5. Already well-connected buildings/areas generally "
    "do not require a new connection."
)

print(
    "6. Healthcare, schools and government/public-service "
    "facilities are within the same first-priority group."
)

print(
    "7. TGRAC/reference roads are preserved as the existing "
    "road baseline where available."
)

print(
    "8. Accessibility measurements are primarily geometric "
    "unless a network-based measure is explicitly stated."
)

print(
    "9. Candidate routes are planning candidates and are not "
    "field-validated engineered roads."
)

print(
    "10. Reference GIS data and AI predictions are not "
    "automatically treated as ground truth."
)

print(
    "11. Missing reference records do not prove real-world "
    "absence of a facility or feature."
)

print(
    "12. Phase 25 readiness indicates processing readiness, "
    "not scientific validation."
)


# ============================================================
# FINAL STATUS
# ============================================================

if (
    len(villages) > 0
    and ready_villages == len(villages)
    and completed_phase25_steps == len(PHASE25_STEPS)
):

    print(
        "\nSTATUS: PHASE 25 STEPS 1-10 ARE COMPLETED "
        "AND CURRENT VILLAGES ARE READY FOR MULTI-VILLAGE EXPANSION."
    )

else:

    print(
        "\nSTATUS: PHASE 25 STILL REQUIRES PREPARATION."
    )


print("\nMaster status report saved to:")
print(OUTPUT_FILE)

print(
    "\nPHASE 25 STEP 10 COMPLETED."
)