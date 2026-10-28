"""
verify_siddipet_village.py

Confirms the identity of the study village (default: Angadi Kistapur, Markook
mandal, Siddipet district) against the TGRAC Master Administrative Boundary
service, and optionally against an LGD "All Villages of a State" export.

Writes (never overwrites earlier runs; files are time-stamped):
  <village>/study_area/village_identity_<stamp>.json
  <village>/study_area/village_identity_<stamp>.csv
  <village>/raw/tgrac_master_admin/service_<stamp>.json
  <village>/raw/tgrac_master_admin/village_boundary_<stamp>.geojson   (if found)

Usage (from Telangana_Rural_Project\\scripts):
  python verify_siddipet_village.py
  python verify_siddipet_village.py --lgd-csv ..\\downloads\\lgd_telangana_villages.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from tgrac_rest import RestError, get_json, query_layer, save_json, stamp, utc_now

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VILLAGE_DIR = ROOT / "Siddipet" / "Angadi_Kistapur"
DEFAULT_SERVICE = ("https://tgrac.telangana.gov.in/arcgis/rest/services/"
                   "Master_Administrative_Folder/Master_Administrative_Boundary/MapServer")

# Secondary reference, to be cross-checked against the Census 2011 PCA xlsx.
# Source: Wikidata Q15687164, which cites the District Census Handbook.
EXTERNAL_REFERENCE = {
    "census2011_village_code": "573656",
    "census2011_population": 998,
    "census2011_households": 224,
    "census2011_area_ha": 461,
    "source": "https://www.wikidata.org/wiki/Q15687164 (cites DCHB); VERIFY against Census PCA",
}

STRING_TYPES = {"esriFieldTypeString"}


def find_matches(service_url, service, token, verify):
    """Search every string field of every feature layer for `token`."""
    matches = []
    for lyr in service.get("layers", []):
        if lyr.get("subLayerIds"):          # group layer
            continue
        layer_url = f"{service_url}/{lyr['id']}"
        try:
            info = get_json(layer_url, verify=verify)
        except RestError as exc:
            print(f"  ! layer {lyr['id']} '{lyr['name']}': {exc}")
            continue
        if info.get("type") != "Feature Layer":
            continue
        fields = [f["name"] for f in info.get("fields", [])
                  if f.get("type") in STRING_TYPES]
        if not fields:
            continue
        where = " OR ".join(f"UPPER({f}) LIKE '%{token.upper()}%'" for f in fields)
        try:
            feats, _, exceeded = query_layer(layer_url, info, where=where,
                                             return_geometry=False, verify=verify)
        except RestError as exc:
            print(f"  ! query failed on layer {lyr['id']} '{lyr['name']}': {exc}")
            continue
        print(f"  layer {lyr['id']:>3} {lyr['name']!r}: {len(feats)} match(es)")
        for f in feats:
            matches.append({"layer_id": lyr["id"], "layer_name": lyr["name"],
                            "layer_url": layer_url, "layer_info": info,
                            "attributes": f.get("properties", {}),
                            "exceeded_limit": exceeded})
    return matches


def attrs_contain(attrs: dict, token: str) -> bool:
    return any(token.upper() in str(v).upper() for v in attrs.values())


def search_lgd(csv_path: Path, village_token: str):
    rows = []
    with open(csv_path, encoding="utf-8-sig", errors="replace") as fh:
        for row in csv.DictReader(fh):
            if any(village_token.upper() in str(v).upper() for v in row.values()):
                rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--service", default=DEFAULT_SERVICE)
    ap.add_argument("--village-token", default="KISTAPUR",
                    help="distinctive part of the village name to search")
    ap.add_argument("--village-name", default="Angadi Kistapur")
    ap.add_argument("--mandal", default="MARKOOK")
    ap.add_argument("--district", default="SIDDIPET")
    ap.add_argument("--village-dir", type=Path, default=DEFAULT_VILLAGE_DIR)
    ap.add_argument("--lgd-csv", type=Path, help="optional LGD villages export (CSV)")
    ap.add_argument("--insecure", action="store_true",
                    help="skip TLS certificate check (only if the site's certificate fails)")
    args = ap.parse_args()
    verify = not args.insecure
    ts = stamp()
    study, raw = args.village_dir / "study_area", args.village_dir / "raw" / "tgrac_master_admin"

    print(f"[1/4] Reading service: {args.service}")
    try:
        service = get_json(args.service, verify=verify)
    except RestError as exc:
        sys.exit(f"Cannot read the TGRAC service: {exc}\n"
                 "Check the URL in a browser from an Indian network first.")
    save_json(raw / f"service_{ts}.json", service)
    print(f"      {len(service.get('layers', []))} layers; "
          f"copyrightText={service.get('copyrightText')!r}")

    print(f"[2/4] Searching all string fields for '{args.village_token}'")
    matches = find_matches(args.service, service, args.village_token, verify)

    print("[3/4] Checking hierarchy (mandal + district must appear in the same record)")
    confirmed = [m for m in matches
                 if attrs_contain(m["attributes"], args.mandal)
                 and attrs_contain(m["attributes"], args.district)]
    status = "CONFIRMED_IN_TGRAC" if confirmed else (
        "NAME_FOUND_HIERARCHY_NOT_CONFIRMED" if matches else "NOT_FOUND_IN_TGRAC")
    print(f"      status: {status}")

    boundary_file = None
    if confirmed:
        best = confirmed[0]
        oid_field = best["layer_info"].get("objectIdField") or "OBJECTID"
        oid = best["attributes"].get(oid_field)
        if oid is not None:
            feats, pages, _ = query_layer(best["layer_url"], best["layer_info"],
                                          where=f"{oid_field}={oid}", verify=verify)
            if feats and feats[0].get("geometry"):
                boundary_file = raw / f"village_boundary_{ts}.geojson"
                save_json(boundary_file, {"type": "FeatureCollection", "features": feats})
                save_json(raw / f"village_boundary_{ts}_server_response.json", pages)
                print(f"      boundary saved: {boundary_file}")

    lgd_rows = search_lgd(args.lgd_csv, args.village_token) if args.lgd_csv else []

    print("[4/4] Writing identity record")
    record = {
        "village_name_requested": args.village_name,
        "mandal_requested": args.mandal,
        "district_requested": args.district,
        "status": status,
        "checked_at_utc": utc_now(),
        "tgrac_service": args.service,
        "tgrac_copyright_text": service.get("copyrightText") or "not stated by service",
        "tgrac_matches": [{k: v for k, v in m.items() if k != "layer_info"} for m in matches],
        "tgrac_boundary_file": str(boundary_file) if boundary_file else None,
        "lgd_csv": str(args.lgd_csv) if args.lgd_csv else None,
        "lgd_matches": lgd_rows,
        "external_reference_unverified": EXTERNAL_REFERENCE,
        "note": "Identity is CONFIRMED only when TGRAC attributes contain village, "
                "mandal and district together. External reference values must be "
                "checked against the Census 2011 PCA before use.",
    }
    save_json(study / f"village_identity_{ts}.json", record)

    with open(study / f"village_identity_{ts}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "layer", "status", "attributes"])
        for m in matches:
            w.writerow(["TGRAC", f"{m['layer_id']} {m['layer_name']}",
                        "hierarchy_ok" if m in confirmed else "name_only", m["attributes"]])
        for r in lgd_rows:
            w.writerow(["LGD", args.lgd_csv.name, "name_match", r])
    print(f"      written: {study / f'village_identity_{ts}.json'}")


if __name__ == "__main__":
    main()
