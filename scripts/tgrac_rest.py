"""
tgrac_rest.py - minimal, READ-ONLY helper for ArcGIS REST services (TGRAC).

Only GET requests are made. Nothing is ever written to the server.
Used by: verify_siddipet_village.py, inspect_tgrac_angadi_kistapur.py,
         prepare_siddipet_village.py
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import requests

HEADERS = {"User-Agent": "CBIT-MTech-research/1.0 (read-only metadata inspection)"}


class RestError(RuntimeError):
    """Raised when the server answers with an ArcGIS error or cannot be reached."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def get_json(url: str, params: dict | None = None, verify: bool = True,
             retries: int = 3, timeout: int = 60) -> dict:
    """GET url with f=pjson (unless params override f) and return parsed JSON."""
    query = {"f": "pjson"}
    query.update(params or {})
    last_error = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=query, headers=HEADERS,
                                timeout=timeout, verify=verify)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
            continue
        if isinstance(data, dict) and "error" in data:
            raise RestError(f"{url} -> server error: {data['error']}")
        return data
    raise RestError(f"Could not read {url}: {last_error}")


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def supports_geojson(layer_info: dict) -> bool:
    fmts = str(layer_info.get("supportedQueryFormats", "")).lower()
    return "geojson" in fmts


def query_layer(layer_url: str, layer_info: dict, where: str = "1=1",
                bbox_wgs84: tuple | None = None, return_geometry: bool = True,
                verify: bool = True) -> tuple[list[dict], list[dict], bool]:
    """
    Query a feature layer. Returns (geojson_features, raw_pages, exceeded_limit).

    raw_pages are the server responses exactly as parsed, for saving to raw/.
    Pagination is used only if the layer advertises supportsPagination.
    """
    fmt = "geojson" if supports_geojson(layer_info) else "json"
    base = {"where": where, "outFields": "*",
            "returnGeometry": "true" if return_geometry else "false",
            "outSR": 4326, "f": fmt}
    if bbox_wgs84:
        base.update({"geometry": ",".join(f"{v:.8f}" for v in bbox_wgs84),
                     "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                     "spatialRel": "esriSpatialRelIntersects"})
    paginate = bool(layer_info.get("advancedQueryCapabilities", {})
                    .get("supportsPagination"))
    page_size = int(layer_info.get("maxRecordCount") or 1000)

    features, pages, offset, exceeded = [], [], 0, False
    while True:
        params = dict(base)
        if paginate:
            params.update(resultOffset=offset, resultRecordCount=page_size)
        page = get_json(layer_url.rstrip("/") + "/query", params, verify=verify)
        pages.append(page)
        batch = page.get("features", [])
        if fmt == "json":
            batch = [esri_to_geojson_feature(f, page.get("geometryType"))
                     for f in batch]
        features.extend(batch)
        exceeded = bool(page.get("exceededTransferLimit")
                        or page.get("properties", {}).get("exceededTransferLimit"))
        if not (paginate and exceeded and batch):
            break
        offset += len(batch)
    return features, pages, exceeded


# ---------- Esri JSON -> GeoJSON (fallback when f=geojson is unsupported) ----------

def _ring_area(ring):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))


def esri_to_geojson_feature(feat: dict, geometry_type: str | None) -> dict:
    g = feat.get("geometry") or {}
    geom = None
    if "x" in g and "y" in g:
        geom = {"type": "Point", "coordinates": [g["x"], g["y"]]}
    elif "points" in g:
        geom = {"type": "MultiPoint", "coordinates": g["points"]}
    elif "paths" in g:
        geom = {"type": "MultiLineString", "coordinates": g["paths"]}
    elif "rings" in g:
        # Esri: outer rings clockwise (negative signed area), holes counter-clockwise.
        polys = []
        for ring in g["rings"]:
            ring2d = [pt[:2] for pt in ring]
            if _ring_area(ring2d) <= 0 or not polys:
                polys.append([ring2d])
            else:
                polys[-1].append(ring2d)
        geom = {"type": "MultiPolygon", "coordinates": polys}
    return {"type": "Feature", "properties": feat.get("attributes", {}),
            "geometry": geom}
