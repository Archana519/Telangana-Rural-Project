"""
inspect_tgrac_angadi_kistapur.py

Read-only inventory of the TGRAC Abadi MapServer. It:
  * lists every layer with its full group path,
  * picks the layers under/named "Angadi Kistapur" (and shows where the
    drone/satellite image layers sit in the tree),
  * records type, geometry, CRS, extent, fields, capabilities, query formats,
    copyright text and tiling (cache) resolution,
  * lists any ImageServer in the same folder (the only service type that can
    serve ORIGINAL pixels),
  * writes a verdict on what can and cannot be exported.

It does NOT download or export any imagery.

Writes (time-stamped, never overwritten):
  <village>/study_area/tgrac_abadi_inventory_<stamp>.json
  <village>/study_area/tgrac_abadi_layers_<stamp>.csv
  <village>/raw/tgrac_abadi/service_<stamp>.json, layers_<stamp>.json

Usage:
  python inspect_tgrac_angadi_kistapur.py
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from tgrac_rest import RestError, get_json, save_json, stamp, utc_now

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VILLAGE_DIR = ROOT / "Siddipet" / "Angadi_Kistapur"
DEFAULT_SERVICE = ("https://tgrac.telangana.gov.in/arcgis/rest/services/"
                   "Abadi_Folder/Abadi_Final/MapServer")
IMAGE_WORDS = re.compile(r"image|drone|satellite|ortho|raster", re.I)


def build_paths(layers):
    by_id = {l["id"]: l for l in layers}

    def path(l):
        parts, cur = [l["name"]], l
        while cur.get("parentLayer") or cur.get("parentLayerId", -1) not in (-1, None):
            pid = (cur.get("parentLayer") or {}).get("id", cur.get("parentLayerId"))
            if pid is None or pid not in by_id:
                break
            cur = by_id[pid]
            parts.append(cur["name"])
        return " / ".join(reversed(parts))

    def descendants(lid):
        out, stack = [], [lid]
        while stack:
            cur = by_id.get(stack.pop())
            if not cur:
                continue
            for s in cur.get("subLayers") or []:
                sid = s["id"] if isinstance(s, dict) else s
                out.append(sid)
                stack.append(sid)
            for sid in cur.get("subLayerIds") or []:
                if sid not in out:
                    out.append(sid)
                    stack.append(sid)
        return out

    return by_id, path, descendants


def tile_resolutions(service):
    ti = service.get("tileInfo") or {}
    lods = ti.get("lods") or []
    return [{"level": l.get("level"), "resolution": l.get("resolution"),
             "scale": l.get("scale")} for l in lods]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--service", default=DEFAULT_SERVICE)
    ap.add_argument("--keyword", default="kistapur",
                    help="case-insensitive text identifying the village's layers")
    ap.add_argument("--village-dir", type=Path, default=DEFAULT_VILLAGE_DIR)
    ap.add_argument("--insecure", action="store_true")
    args = ap.parse_args()
    verify, ts = not args.insecure, stamp()
    study, raw = args.village_dir / "study_area", args.village_dir / "raw" / "tgrac_abadi"

    try:
        service = get_json(args.service, verify=verify)
        layers_doc = get_json(args.service.rstrip("/") + "/layers", verify=verify)
    except RestError as exc:
        sys.exit(f"Cannot read service: {exc}")
    save_json(raw / f"service_{ts}.json", service)
    save_json(raw / f"layers_{ts}.json", layers_doc)

    layers = layers_doc.get("layers", []) + layers_doc.get("tables", [])
    by_id, path_of, descendants = build_paths(layers)

    roots = [l["id"] for l in layers if args.keyword.lower() in l["name"].lower()]
    selected = set(roots)
    for r in roots:
        selected.update(descendants(r))
    image_layers = [l["id"] for l in layers
                    if l.get("type") == "Raster Layer" or IMAGE_WORDS.search(l["name"])]

    rows = []
    for l in layers:
        ext = l.get("extent") or {}
        caps = l.get("capabilities", "")
        rows.append({
            "id": l["id"],
            "name": l["name"],
            "path": path_of(l),
            "belongs_to_village": l["id"] in selected,
            "is_image_candidate": l["id"] in image_layers,
            "type": l.get("type"),
            "geometryType": l.get("geometryType"),
            "wkid": (ext.get("spatialReference") or {}).get("latestWkid")
                    or (ext.get("spatialReference") or {}).get("wkid"),
            "extent": [ext.get("xmin"), ext.get("ymin"), ext.get("xmax"), ext.get("ymax")],
            "capabilities": caps,
            "query_supported": "Query" in caps and l.get("type") == "Feature Layer",
            "supportedQueryFormats": l.get("supportedQueryFormats"),
            "maxRecordCount": l.get("maxRecordCount"),
            "n_fields": len(l.get("fields") or []),
            "field_names": [f["name"] for f in (l.get("fields") or [])],
            "pixel_size_exposed": {k: l[k] for k in ("pixelSizeX", "pixelSizeY") if k in l}
                                  or "not exposed by MapServer layer",
            "copyrightText": l.get("copyrightText") or "",
            "description": (l.get("description") or "")[:300],
        })

    # Look for ImageServers in the same folder (only these can return original pixels).
    folder_url = args.service.rsplit("/", 2)[0]
    try:
        folder = get_json(folder_url, verify=verify)
        folder_services = folder.get("services", [])
    except RestError as exc:
        folder_services = [{"error": str(exc)}]
    image_servers = [s for s in folder_services if s.get("type") == "ImageServer"]

    caps = service.get("capabilities", "")
    village_images = [r for r in rows if r["belongs_to_village"] and r["is_image_candidate"]]
    verdict = {
        "service_type": "MapServer",
        "service_capabilities": caps,
        "rendered_map_export_possible": "Map" in caps,
        "original_raster_download_via_this_MapServer": False,
        "why": "A MapServer 'export' returns a rendered picture (PNG/JPG/etc.), resampled "
               "to the requested size and symbolised; it is not the original imagery bands.",
        "max_export_image_px": [service.get("maxImageWidth"), service.get("maxImageHeight")],
        "supportedImageFormatTypes": service.get("supportedImageFormatTypes"),
        "is_cached_tiles": bool(service.get("singleFusedMapCache")),
        "tile_resolutions_in_service_units": tile_resolutions(service),
        "service_wkid": (service.get("spatialReference") or {}).get("latestWkid")
                        or (service.get("spatialReference") or {}).get("wkid"),
        "image_servers_in_same_folder": image_servers,
        "original_pixels_possibly_available": bool(image_servers),
        "copyrightText": service.get("copyrightText") or "not stated by service",
        "licence_status": "No licence stated -> treat as NOT licensed; written "
                          "permission from TGRAC required before any use in results.",
        "village_layers_found": len(selected),
        "village_image_layers": [f"{r['id']}: {r['path']}" for r in village_images],
    }

    inventory = {"service": args.service, "inspected_at_utc": utc_now(),
                 "keyword": args.keyword, "verdict": verdict, "layers": rows}
    save_json(study / f"tgrac_abadi_inventory_{ts}.json", inventory)
    with open(study / f"tgrac_abadi_layers_{ts}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)

    print(f"Service: {args.service}")
    print(f"  capabilities: {caps} | cached tiles: {verdict['is_cached_tiles']} "
          f"| wkid: {verdict['service_wkid']}")
    print(f"  copyright: {verdict['copyrightText']}")
    print(f"  layers total: {len(rows)} | under '{args.keyword}': {len(selected)}")
    for r in rows:
        if r["belongs_to_village"]:
            flag = "IMAGE " if r["is_image_candidate"] else "      "
            print(f"   {flag}{r['id']:>3}  {r['type'] or '':<14} {r['path']}")
    others = [r for r in rows if r["is_image_candidate"] and not r["belongs_to_village"]]
    if others:
        print("  image layers NOT under the village group (check their extent):")
        for r in others:
            print(f"         {r['id']:>3}  {r['path']}")
    print(f"  ImageServers in folder: {[s.get('name') for s in image_servers] or 'none'}")
    print(f"  Original raster downloadable via this MapServer: NO (rendered export only)")
    print(f"Saved: {study / f'tgrac_abadi_inventory_{ts}.json'}")


if __name__ == "__main__":
    main()
