#!/usr/bin/env python
"""Print every school / health / government place candidate of a village with its verification status, so mis-geocoded or duplicate records can be added to
configs/multivillage/villages/<id>_facility_exclusions.csv (columns id,name,reason) before the final run. Run after `run_village_end_to_end.py --stage open`.

    python scripts/list_facility_candidates.py --village aswaraopeta
Flags shown: SHARED_POINT (several records at one identical coordinate: a generic geocode, weak evidence), FOREIGN_NAME (place names that belong elsewhere, e.g. Pakistani towns),
NO_FOOTPRINT (no detected footprint within 20 m).
"""
import argparse
import pickle
import re
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
FOREIGN = re.compile(r"faisalabad|umerkot|jaranwala|mirpurkhas|karachi|lahore|islamabad|punjab pakistan|sindh|dhaka|kathmandu", re.I)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", required=True)
    ap.add_argument("--variant", default=None, choices=[None, "segmentation"])
    a = ap.parse_args()
    f = REPO / "data" / "villages" / a.village / ("state_segmentation.pkl" if a.variant else "state.pkl")
    if not f.exists():
        sys.exit(f"{f} not found: run scripts/run_village_end_to_end.py --village {a.village} --stage open (then --stage route for --variant segmentation)")
    S = pickle.load(open(f, "rb"))
    fa = S["fac_all"].copy()
    fa["shared"] = fa.groupby(["x_epsg32644", "y_epsg32644"]).name.transform("size")
    fa["flag"] = [";".join(x for x in (("SHARED_POINT" if r.shared > 1 else ""), ("FOREIGN_NAME" if FOREIGN.search(str(r["name"]) or "") else ""),
                                       ("NO_FOOTPRINT" if not r.footprint_within_20m else "")) if x) for _, r in fa.iterrows()]
    cols = ["id", "name", "facility_type", "taxonomy_primary", "lat", "lon", "dist_to_nearest_footprint_m", "status", "flag"]
    with pd.option_context("display.max_rows", None, "display.width", 250, "display.max_colwidth", 42):
        print(fa.sort_values(["status", "facility_type", "name"])[cols].to_string(index=False))
    print("\nstatus counts:", fa.status.value_counts().to_dict(), "| flagged:", int((fa["flag"] != "").sum()))
    print(f"Add records to exclude to configs/multivillage/villages/{a.village}_facility_exclusions.csv (id,name,reason), then re-run the extract step.")


if __name__ == "__main__":
    main()
