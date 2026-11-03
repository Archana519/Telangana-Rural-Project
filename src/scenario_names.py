"""Scenario run names and the facility layer used by the deliverables.

The final deliverables are built from the 'final' scenario family: the same planner and settings as the verified reference runs, but with the
anganwadi (facility_id 1702300) excluded (inputs/EXCLUSIONS.md) and the two TGRAC Gram Panchayat headquarters points added (inputs/ADMIN_UTILITIES.md):
five facilities. The verified 4-facility reference runs stay in the pipeline only for the reproduction check.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "Siddipet" / "Damarakunta"
EXCLUDED_FACILITY_ID = "1702300"
FAC_LAYER = V / "reference" / "derived" / "damarakunta_priority_facilities_final_5.gpkg"        # 3 retained + 2 Gram Panchayat HQ points
FAC_LAYER_EXCL = V / "reference" / "derived" / "damarakunta_priority_facilities_excl_1702300.gpkg"   # the 3 retained only (intermediate)
N_FACILITIES = 5
FAMILY = "final"
FAC_LAYER_ORIGINAL = V / "reference" / "damarakunta_priority_facilities.gpkg"      # hash-pinned input of the reference run: never edited
PRIMARY = "S2_fac_C0_s25_final_x4"            # penalty x4 on footprint cells
P3 = "S2_fac_C0_s25_final_x1"                 # no penalty
AVOID = "S2_fac_C0_s25_final_avoid_buf100"    # footprints buffered 7.1 m, penalty x100 (building-avoiding scenario)
AVOID_PREFIX = "S2_fac_C0_s25_final_avoid_buf"
REF_PRIMARY = "S2_fac_C0_s25_v11"             # verified 4-facility baseline
REF_P3 = "S2_fac_C0_s25_P3_none"
