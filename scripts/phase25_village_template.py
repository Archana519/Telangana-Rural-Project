import os
import json

# ============================================================
# PHASE 25 - MULTIPLE VILLAGES
# STEP 2: STANDARD VILLAGE PROJECT TEMPLATE
# ============================================================

PROJECT_ROOT = r"D:\Telangana_Rural_Project"

TEMPLATE = {
    "district": "District_Name",
    "mandal": "Mandal_Name",
    "village": "Village_Name",
    "study_area": {
        "boundary": "",
        "imagery": ""
    },
    "data": {
        "raw_imagery": "",
        "dem": "",
        "landcover": "",
        "reference_roads": "",
        "schools": "",
        "health_facilities": "",
        "government_facilities": ""
    },
    "processing": {
        "segmentation": "StrongDINOv2Seg",
        "facility_priority": [
            "Public-service facilities",
            "Residential areas",
            "Already well-connected areas"
        ],
        "routing": "Multi-criteria road network optimization"
    },
    "status": "NOT_STARTED"
}


print("=" * 80)
print("PHASE 25 - MULTIPLE VILLAGES")
print("STEP 2 - STANDARD VILLAGE PROJECT TEMPLATE")
print("=" * 80)


# ============================================================
# 1. DISPLAY STANDARD STRUCTURE
# ============================================================

print("\nStandard village structure:")
print("-" * 80)

folders = [
    "study_area",
    "raw",
    "raw\\imagery",
    "raw\\dem",
    "raw\\landcover",
    "raw\\reference",
    "reference",
    "aligned",
    "derived",
    "predictions",
    "results"
]

for folder in folders:
    print(f"[TEMPLATE] {folder}")


# ============================================================
# 2. CREATE TEMPLATE CONFIGURATION
# ============================================================

template_dir = os.path.join(
    PROJECT_ROOT,
    "docs",
    "village_template"
)

os.makedirs(
    template_dir,
    exist_ok=True
)

template_file = os.path.join(
    template_dir,
    "village_config_template.json"
)

with open(
    template_file,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        TEMPLATE,
        f,
        indent=4
    )

print("\n[OK] Village configuration template created.")


# ============================================================
# 3. CREATE STANDARD FOLDER TEMPLATE
# ============================================================

folder_template_root = os.path.join(
    template_dir,
    "Village_Name"
)

for folder in folders:

    path = os.path.join(
        folder_template_root,
        folder
    )

    os.makedirs(
        path,
        exist_ok=True
    )

print("[OK] Standard village folder template created.")


# ============================================================
# 4. VERIFY TEMPLATE
# ============================================================

print("\n" + "=" * 80)
print("VERIFYING VILLAGE TEMPLATE")
print("=" * 80)

missing = []

for folder in folders:

    path = os.path.join(
        folder_template_root,
        folder
    )

    if os.path.isdir(path):
        print(f"[OK] {folder}")
    else:
        print(f"[MISSING] {folder}")
        missing.append(folder)


# ============================================================
# 5. VERIFY CONFIGURATION
# ============================================================

print("\n" + "=" * 80)
print("VERIFYING CONFIGURATION FILE")
print("=" * 80)

if os.path.isfile(template_file):

    with open(
        template_file,
        "r",
        encoding="utf-8"
    ) as f:
        config = json.load(f)

    required_keys = [
        "district",
        "mandal",
        "village",
        "study_area",
        "data",
        "processing",
        "status"
    ]

    for key in required_keys:

        if key in config:
            print(f"[OK] Configuration key: {key}")
        else:
            print(f"[MISSING] Configuration key: {key}")
            missing.append(key)

else:
    print("[MISSING] village_config_template.json")
    missing.append("village_config_template.json")


# ============================================================
# 6. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("PHASE 25 STEP 2 SUMMARY")
print("=" * 80)

print(f"Template directory : {template_dir}")
print(f"Configuration file : {template_file}")
print(f"Missing items      : {len(missing)}")

if len(missing) == 0:

    print("\nSTATUS: MULTI-VILLAGE TEMPLATE READY.")

else:

    print("\nSTATUS: TEMPLATE VERIFICATION FAILED.")

print("\nImportant:")
print("The template does NOT represent a processed second village.")
print("It is only a standard structure for adding future rural villages.")