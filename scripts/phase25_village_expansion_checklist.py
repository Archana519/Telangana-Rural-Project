import os
import pandas as pd

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 9 - VILLAGE EXPANSION CHECKLIST
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
    "phase25_village_expansion_checklist.csv"
)

print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 9 - VILLAGE EXPANSION CHECKLIST")
print("=" * 80)


# ============================================================
# EXPECTED VILLAGE STRUCTURE
# ============================================================
# Reference GIS data are stored directly in "reference".
# There is intentionally NO raw\reference requirement.
# ============================================================

REQUIRED_DIRECTORIES = [
    "study_area",
    os.path.join("raw", "imagery"),
    os.path.join("raw", "dem"),
    os.path.join("raw", "landcover"),
    "reference",
    "aligned",
    "derived",
    "predictions",
    "results"
]


# ============================================================
# EXPECTED DATA / PROCESSING STAGES
# ============================================================

CHECKLIST_ITEMS = [
    {
        "stage": "1",
        "requirement": "Village study-area boundary",
        "purpose": "Defines the rural village study extent"
    },
    {
        "stage": "2",
        "requirement": "Real village satellite imagery",
        "purpose": "Primary imagery input for the village"
    },
    {
        "stage": "3",
        "requirement": "Georeferenced / aligned imagery",
        "purpose": "Places imagery in the project coordinate system"
    },
    {
        "stage": "4",
        "requirement": "DEM",
        "purpose": "Provides terrain/elevation information"
    },
    {
        "stage": "5",
        "requirement": "Land-cover data",
        "purpose": "Supports land-use and routing-cost analysis"
    },
    {
        "stage": "6",
        "requirement": "Reference GIS data",
        "purpose": "Provides existing roads and available facility/reference information"
    },
    {
        "stage": "7",
        "requirement": "StrongDINOv2Seg inference",
        "purpose": "Provides AI-based segmentation for the village"
    },
    {
        "stage": "8",
        "requirement": "Building and road extraction",
        "purpose": "Extracts infrastructure features from segmentation"
    },
    {
        "stage": "9",
        "requirement": "Public-service facility identification",
        "purpose": "Identifies schools, healthcare and government/public-service facilities"
    },
    {
        "stage": "10",
        "requirement": "Accessibility-gap analysis",
        "purpose": "Measures facility/structure relationship to the existing road network"
    },
    {
        "stage": "11",
        "requirement": "Priority assignment",
        "purpose": "Applies public-service, residential and well-connected priority groups"
    },
    {
        "stage": "12",
        "requirement": "Cost surface",
        "purpose": "Combines land-cover and terrain constraints for route planning"
    },
    {
        "stage": "13",
        "requirement": "Candidate route generation",
        "purpose": "Generates possible new connections"
    },
    {
        "stage": "14",
        "requirement": "Existing-road comparison",
        "purpose": "Separates candidate connections from existing-road proximity"
    },
    {
        "stage": "15",
        "requirement": "Multi-criteria route evaluation",
        "purpose": "Evaluates candidate routes using multiple planning criteria"
    },
    {
        "stage": "16",
        "requirement": "Before/after connectivity analysis",
        "purpose": "Compares planning-model connectivity before and after a proposed connection"
    },
    {
        "stage": "17",
        "requirement": "Ablation study",
        "purpose": "Tests the effect of removing selected evaluation criteria"
    },
    {
        "stage": "18",
        "requirement": "Sensitivity analysis",
        "purpose": "Tests route-selection stability under alternative weights"
    },
    {
        "stage": "19",
        "requirement": "Final GIS outputs",
        "purpose": "Produces maps, spatial layers and planning results"
    }
]


# ============================================================
# 1. CHECK DISTRICT DIRECTORY
# ============================================================

if not os.path.isdir(DISTRICT_ROOT):

    print(
        "[ERROR] District directory not found:"
    )

    print(DISTRICT_ROOT)

    raise SystemExit(1)


# ============================================================
# 2. DISCOVER VILLAGES
# ============================================================

villages = []

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
    f"\n[OK] Villages discovered: {len(villages)}"
)


# ============================================================
# 3. CHECK VILLAGE FOLDER STRUCTURE
# ============================================================

print("\n" + "=" * 80)
print("VILLAGE STRUCTURE CHECK")
print("=" * 80)

structure_records = []

for village in villages:

    village_root = os.path.join(
        DISTRICT_ROOT,
        village
    )

    missing = []

    for relative_dir in REQUIRED_DIRECTORIES:

        directory = os.path.join(
            village_root,
            relative_dir
        )

        if not os.path.isdir(directory):

            missing.append(
                relative_dir
            )

    if len(missing) == 0:

        status = "READY"

    else:

        status = "INCOMPLETE"

    structure_records.append(
        {
            "district": "Siddipet",
            "village": village,
            "structure_status": status,
            "missing_directories":
                "; ".join(missing)
        }
    )

    print(
        f"{village}: {status}"
    )

    if missing:

        print(
            "  Missing:",
            ", ".join(missing)
        )


# ============================================================
# 4. CREATE GENERAL EXPANSION CHECKLIST
# ============================================================

checklist_records = []

for item in CHECKLIST_ITEMS:

    checklist_records.append(
        {
            "stage": item["stage"],
            "requirement": item["requirement"],
            "purpose": item["purpose"],
            "required_for_new_village": "YES"
        }
    )


# ============================================================
# 5. SAVE REPORTS
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

structure_df = pd.DataFrame(
    structure_records
)

checklist_df = pd.DataFrame(
    checklist_records
)

# Save the detailed expansion checklist
checklist_df.to_csv(
    OUTPUT_FILE,
    index=False
)

# Save structure status separately
STRUCTURE_OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "phase25_village_structure_check.csv"
)

structure_df.to_csv(
    STRUCTURE_OUTPUT_FILE,
    index=False
)


# ============================================================
# 6. DISPLAY CHECKLIST
# ============================================================

print("\n" + "=" * 80)
print("NEW-VILLAGE EXPANSION CHECKLIST")
print("=" * 80)

print(
    checklist_df.to_string(
        index=False
    )
)


# ============================================================
# 7. CURRENT VILLAGE SUMMARY
# ============================================================

if len(structure_df) > 0:

    ready_count = int(
        (
            structure_df[
                "structure_status"
            ]
            == "READY"
        ).sum()
    )

    incomplete_count = int(
        (
            structure_df[
                "structure_status"
            ]
            == "INCOMPLETE"
        ).sum()
    )

else:

    ready_count = 0
    incomplete_count = 0


print("\n" + "=" * 80)
print("PHASE 25 STEP 9 SUMMARY")
print("=" * 80)

print(
    f"Villages discovered : {len(villages)}"
)

print(
    f"Structure ready     : {ready_count}"
)

print(
    f"Structure incomplete : {incomplete_count}"
)

print("\nChecklist saved to:")
print(OUTPUT_FILE)

print("\nStructure check saved to:")
print(STRUCTURE_OUTPUT_FILE)


# ============================================================
# 8. IMPORTANT PROJECT RULES
# ============================================================

print("\n" + "=" * 80)
print("NEW-VILLAGE PROCESSING RULES")
print("=" * 80)

print(
    "1. Only rural-village study areas should be added "
    "to the final project dataset."
)

print(
    "2. Each village must have its own study-area boundary "
    "and input data."
)

print(
    "3. Reference GIS data are stored in the village "
    "reference directory."
)

print(
    "4. Existing TGRAC/reference roads should be preserved "
    "as the baseline where available."
)

print(
    "5. Public-service facilities are the first priority group."
)

print(
    "6. Residential areas are the second priority group."
)

print(
    "7. Already well-connected buildings/areas generally "
    "do not require a new connection."
)

print(
    "8. A missing reference record does not prove that the "
    "real-world facility or feature is absent."
)

print(
    "9. AI predictions and reference GIS data must be "
    "distinguished from ground truth."
)

print(
    "10. Candidate routes are planning candidates, not "
    "field-validated engineered roads."
)

print(
    "11. Every newly added village should pass the same "
    "processing and evaluation stages."
)


# ============================================================
# 9. FINAL STATUS
# ============================================================

if (
    len(villages) > 0
    and incomplete_count == 0
):

    print(
        "\nSTATUS: CURRENT VILLAGE STRUCTURES "
        "ARE READY FOR FUTURE VILLAGE EXPANSION."
    )

else:

    print(
        "\nSTATUS: SOME VILLAGE STRUCTURES "
        "REQUIRE PREPARATION."
    )


print(
    "\nPHASE 25 STEP 9 COMPLETED."
)