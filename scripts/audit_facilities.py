#!/usr/bin/env python
"""Multi-source, four-pass audit of the public facilities of a study area.

    python scripts/audit_facilities.py --village alampur            # also: aswaraopeta | adilabad_urban_updated | damarakunta | all
    python scripts/audit_facilities.py --village all --from-raw     # redo passes 2-4 from the saved raw harvest (no network)

Pass 1  HARVEST   every candidate inside and within 500 m of the locked study polygon from
                  * OpenStreetMap (Overpass API; amenity / building / office / government / healthcare tags and facility-like names),
                  * Overture Maps Places (pinned release of the village config; Damarakunta: same release, fetched here),
                  * Wikidata (SPARQL bounding-box query) and Wikipedia geosearch,
                  * TGRAC layers committed for Damarakunta (anganwadi, health, sub-centre, priority facilities),
                  * LGD / Telangana Govt / district directories: no open API (checked, logged as not reachable) -> use a file you hold with --extra-csv.
Pass 2  CLEAN     one category (School, College, Hospital, Government Office, Anganwadi), duplicates of the same campus merged across sources, and every removed item logged with its reason:
                  closed / disused, commercial (pharmacy, medical shop, diagnostic lab, coaching centre, bank, cooperative credit society), religious or heritage site, not one of the five categories,
                  foreign place names, low-confidence single-source record, outside the polygon (distance given).
Pass 3  SNAP      each survivor is moved onto the real building: footprint containing the point, else the best footprint within 35 m (large buildings are preferred over sheds and houses);
                  no building within 35 m -> excluded ("no building: field / road / wrong pin"). Contact sheets on the Esri imagery (0.6 m) with the footprint outline and the snapped marker are rendered for review.
Pass 4  WRITE     configs/multivillage/villages/<village>_verified_facilities.csv (read by the pipeline instead of the raw Overture places) and <village>_facility_exclusions.csv (log of every removed item),
                  plus the pass tables and contact sheets in DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE/facility_audit/<village>/.

Confidence: high = two or more independent sources and the pin within 12 m of a footprint; medium = one source and the pin within 12 m, or two sources and a snap of 12-35 m; low = one source and a snap of 12-35 m
(kept in the table with use_in_analysis = False for an on-site check; not used for routing or maps).
Footprints for snapping are the open Overture footprints (the StrongDINOv2Seg footprints exist only on the owner's PC); `--footprints <gpkg>` snaps to another layer (for example buildings_v8_*.gpkg).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import Point, box
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
CRS = "EPSG:32644"
TO_WGS = Transformer.from_crs(CRS, 4326, always_xy=True)
FROM_WGS = Transformer.from_crs(4326, CRS, always_xy=True)
UA = {"User-Agent": "research-facility-audit/1.0 (academic study, contact via repository owner)"}
OVERPASS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
CATS = ["School", "College", "Hospital", "Government Office", "Anganwadi"]
FTYPE = {"School": "school", "College": "college", "Hospital": "health", "Government Office": "government", "Anganwadi": "anganwadi"}
CFG_DIR = REPO / "configs" / "multivillage" / "villages"
AUDIT = REPO / "DELIVERABLES_CONTRIBUTION_3_MULTI_VILLAGE" / "facility_audit"
SNAP_M, SNAP_OK_M, BORDER_M, HARVEST_BUFFER_M = 35.0, 12.0, 150.0, 500.0
VILLAGES = ["damarakunta", "adilabad_urban_updated", "aswaraopeta", "alampur"]

# ------------------------------------------------------------------------------------------------ classification
FOREIGN = re.compile(r"faisalabad|umerkot|jaranwala|mirpurkhas|karachi|lahore|islamabad|punjab pakistan|sindh|dhaka|kathmandu", re.I)
NOT_FACILITY = [
    (re.compile(r"pharmac|medical (shop|store|hall)|chemist|medicals?\b|drug ?store|optical|opticals", re.I), "commercial: pharmacy / medical shop (not a care facility)"),
    (re.compile(r"diagnostic|pathology|scan cent|x-?ray|laborator", re.I), "commercial: diagnostic laboratory (not a care facility)"),
    (re.compile(r"coaching|tuition|training institute|computer (centre|center|institute)|tutorial|academy of|spoken english", re.I), "commercial: coaching / tuition centre (not a school)"),
    (re.compile(r"\bbank\b|\batm\b|credit society|cooperative (bank|credit)|co-?operative society|finance|insurance|chit fund", re.I), "financial institution / cooperative society (not a public office)"),
    (re.compile(r"temple|mandir|masjid|mosque|church|dargah|gurudwara|jogulamba|place_of_worship|worship|religious|ashram(?! school)", re.I), "religious / heritage site (not one of the five categories)"),
    (re.compile(r"hotel|lodge|restaurant|bar\b|shop|store|mart\b|showroom|motors|gas_station|petrol|bus_station|bus stand|bus station|theater|theatre|cinema|kalyana|function hall|garden|park\b", re.I), "commercial / transport / leisure (not one of the five categories)"),
]
GOV = re.compile(r"panchayat|\bmro\b|mpdo|tahsil|tehsil|municipal|collectorate|registrar|police|court\b|post office|electricity|electrical (dept|department|office|sub)|transco|tsspdcl|tsnpdcl|discom|water (works|board|supply)|mandal (parishad|office|revenue)|revenue|\brdo\b|forest|excise|r ?and ?b\b|r&b|"
                 r"panchayat raj|agricultur\w* (office|extension|dept)|veterinary|fire station|sub.?treasury|treasury|\bmeeseva\b|e-?seva|ration|civil supplies|government office|govt\.? office|inspection (building|bungalow)", re.I)
COLLEGE = re.compile(r"college|polytechnic|\biti\b|b\.? ?ed\b|university|univercity|institute of|iiit|engineering|junior|degree|vocational", re.I)
SCHOOL = re.compile(r"school|vidyalaya|vidya|zphs|mpps|mpups|mpp|gurukul|gurukulam|residential|convent|kids|montessori|kindergarten|nursery|play ?school|model school|kasturba|\bkgbv\b|primary|high school|pathshala|balabharathi", re.I)
HOSP = re.compile(r"hospital|\bphc\b|\bchc\b|sub.?cent(re|er)|clinic|nursing home|maternity|dispensary|health cent|arogya|aarogya|eye care|dental|medical college|aayush|ayush|polyclinic|maternal|child welfare", re.I)
ANGAN = re.compile(r"anganwadi|angan ?wadi|aanganwadi|anganvadi|icds|balwadi|child care cent|creche|crèche|balamitra|bala vikas|nutrition cent", re.I)
HOSTEL = re.compile(r"hostel", re.I)
WELFARE = re.compile(r"social welfare|bc welfare|sc welfare|st welfare|tribal|welfare|minority|gurukul|ashram", re.I)
PRESCHOOL_PRIVATE = re.compile(r"montessori|play ?school|kids|convent|nursery|international|public school|e-?techno|techno|olympiad|talent", re.I)
AMENITY_CAT = {"school": "School", "college": "College", "university": "College", "hospital": "Hospital", "clinic": "Hospital", "doctors": "Hospital", "dentist": "Hospital", "nursing_home": "Hospital",
               "townhall": "Government Office", "courthouse": "Government Office", "police": "Government Office", "post_office": "Government Office", "fire_station": "Government Office",
               "public_building": "Government Office", "social_facility": "Anganwadi", "childcare": "Anganwadi", "kindergarten": "Anganwadi"}
TAX_CAT = [(re.compile(r"college_university|university|college|vocational|trade_school|technical"), "College"), (re.compile(r"preschool|elementary_school|high_school|middle_school|school|montessori"), "School"),
           (re.compile(r"hospital|health_care|medical_center|clinic|urgent_care|community_health|health_and_medical|maternity|nursing"), "Hospital"),
           (re.compile(r"government_office|city_hall|town_hall|local_and_state|community_and_government|post_office|police_station|courthouse|fire_station|public_service"), "Government Office"),
           (re.compile(r"childcare|child_care|day_care|daycare"), "Anganwadi")]


def classify(name: str, tags: dict, taxonomy: str, source: str) -> tuple:
    """(category or None, reason if None, subtype). Order matters: exclusions that identify a non-facility first, then Anganwadi, College, School, Hospital, Government."""
    n = name or ""
    tx = taxonomy.lower() if isinstance(taxonomy, str) else ""
    am = (tags.get("amenity") or "").lower()
    blob = " ".join([n, tx, am, tags.get("building", ""), tags.get("office", ""), tags.get("healthcare", ""), tags.get("government", "")])
    short = re.sub(r"[^a-z0-9]", "", n.lower())
    if n and len(short) <= 4 and short not in ("phc", "chc", "zphs", "mpdo", "mro", "iti", "ps", "mpps", "kgbv", "anm", "rto") and not re.search(r"\d", n):
        return None, f"unclear record: name '{n}' carries no facility word (cannot be verified)", ""
    if FOREIGN.search(blob):
        return None, "foreign place name (mis-geocoded record from another country)", ""
    if am == "pharmacy" or tx in ("pharmacy", "medical_supply_store", "laboratory_testing", "optician", "drugstore"):
        return None, ("commercial: pharmacy / medical shop (not a care facility)" if "lab" not in tx else "commercial: diagnostic laboratory (not a care facility)"), ""
    if am in ("place_of_worship",) or "worship" in tx or tx in ("religious_organization", "historic_site", "landmark_and_historical_building", "monument"):
        return None, "religious / heritage site (not one of the five categories)", ""
    if tx in ("financial_service", "bank_or_credit_union", "credit_union", "bank", "atm", "shopping", "gas_station", "hotel", "bus_station", "commercial_industrial", "real_estate_service", "professional_service"):
        return None, f"not a public facility (Overture category {tx})", ""
    if am in ("community_centre", "social_centre") and not GOV.search(n):
        return None, "community hall (not an office or welfare centre)", ""
    # a name that identifies a public facility wins over a generic category
    if ANGAN.search(n) or "anganwadi" in tx or am in ("childcare",) or (am == "kindergarten" and not PRESCHOOL_PRIVATE.search(n)):
        return "Anganwadi", "", "anganwadi / ICDS / child care"
    if HOSTEL.search(n) and WELFARE.search(n):
        return "Anganwadi", "", "welfare hostel"
    for rx, why in NOT_FACILITY:
        if rx.search(n) and not (am in AMENITY_CAT):
            return None, why, ""
    if am in ("college", "university") or tx in ("college_university",) or (COLLEGE.search(n) and not re.search(r"primary|high school|public school|kids", n, re.I) and (am == "" or am in ("school", "college"))):
        return "College", "", "higher education" + (" (junior / degree / polytechnic)" if COLLEGE.search(n) else "")
    if am == "school" or SCHOOL.search(n) or any(r.search(tx) for r, c in TAX_CAT if c == "School"):
        return "School", "", ("pre-primary / private" if PRESCHOOL_PRIVATE.search(n) else "school")
    if am in ("hospital", "clinic", "doctors", "dentist", "nursing_home") or tags.get("healthcare") or HOSP.search(n) or any(r.search(tx) for r, c in TAX_CAT if c == "Hospital"):
        return "Hospital", "", ("clinic / PHC / sub-centre" if re.search(r"clinic|phc|sub.?cent|dispensary|nursing|doctor", n + am, re.I) else "hospital")
    if am in AMENITY_CAT and AMENITY_CAT[am] == "Government Office" or tags.get("office") == "government" or tags.get("government") or tags.get("building") in ("government", "civic", "public") or GOV.search(n) \
            or any(r.search(tx) for r, c in TAX_CAT if c == "Government Office"):
        return "Government Office", "", "government / civic office"
    if am == "education" or tx in ("education",):
        return None, "generic education record without a school / college name (not classifiable)", ""
    return None, "not one of the five categories", ""


def norm(s: str) -> str:
    t = (s or "").lower().replace("govt", "government").replace("zphs", "zp high school").replace("ashwa", "aswa")
    t = re.sub(r"sub[\s\-]*cent(re|er)", "subcentre", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


DISTINCT = re.compile(r"\b(mpps|mpups|mpp|zphs|zp high school|primary|upper primary|high school|junior|degree|polytechnic|kgbv|model|residential|anganwadi|phc|chc|sub ?cent\w*|hospital|clinic)\b|\b(?:[ivx]{1,4}|\d+)\b", re.I)


def distinct_tokens(name: str) -> frozenset:
    """Type words and numbers that tell two neighbouring facilities apart (MPPS vs ZPHS, Anganwadi-III vs -IX, Junior vs Degree college): names that differ in them are different facilities."""
    t = norm(name)
    return frozenset(m.group(0).lower().replace(" ", "") for m in DISTINCT.finditer(t) if not (m.group(0).isalpha() and len(m.group(0)) == 1))


def same_facility_name(a: str, b: str) -> bool:
    ta, tb = distinct_tokens(a), distinct_tokens(b)
    return not (ta and tb and ta != tb and not (ta <= tb or tb <= ta))


def sim(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.9
    return difflib.SequenceMatcher(None, a, b).ratio()


# ------------------------------------------------------------------------------------------------ area loading
def load_area(v: str, footprints: str | None = None) -> dict:
    """Locked polygon (EPSG:32644), open footprints, Overture places (all categories), local reference layers."""
    from src.multivillage import acquire as A
    if v == "damarakunta":
        root = REPO / "Siddipet" / "Damarakunta"
        cell = gpd.read_file(root / "study_area" / "damarakunta_boundary.gpkg").to_crs(CRS).geometry.union_all()
        fp = gpd.read_file(footprints or (root / "results/v8_instances/buildings_v8_full.gpkg"), layer="buildings").to_crs(CRS)
        fp = fp[fp.geometry.area >= 15]
        cfg = A.load_cfg("adilabad_urban")
        places = None
        mosaic = root / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
    else:
        cfg = A.load_cfg(v)
        d = A.data_dir(cfg)
        cell = gpd.read_file(d / "boundary.gpkg").to_crs(CRS).geometry.union_all()
        fp = gpd.read_file(footprints) if footprints else gpd.read_file(d / "buildings.gpkg")
        fp = fp.to_crs(CRS)
        fp = fp[fp.geometry.area >= 15]
        places = gpd.read_file(d / "places_4km.gpkg").to_crs(CRS)
        slug = cfg["village"]["work_slug"]
        mosaic = REPO / "data" / "villages" / f"{slug}_esri" / "aligned" / f"{slug}_esri_highres_mosaic_0p6m.tif"
    return dict(v=v, cfg=cfg, cell=cell, fp=fp.reset_index(drop=True), places=places, mosaic=mosaic, root=REPO / "Siddipet" / "Damarakunta")


def load_overrides(v: str) -> pd.DataFrame:
    """configs/multivillage/villages/<village>_facility_overrides.csv: decisions taken after looking at the contact sheets / Google Maps (columns match, action, note).
    match = text found in the name or source id; action = keep_pin (the source pin is on the roof of a building that the footprint layer lacks) | exclude | category:<Category>."""
    f = CFG_DIR / f"{v}_facility_overrides.csv"
    return pd.read_csv(f).fillna("") if f.exists() else pd.DataFrame(columns=["match", "action", "note"])


def override_for(ov: pd.DataFrame, name: str, ids: str):
    for r in ov.itertuples():
        if r.match and (r.match.lower() in (name or "").lower() or r.match.lower() in (ids or "").lower()):
            return r
    return None


# ------------------------------------------------------------------------------------------------ pass 1
def post(url, data, tries=3, timeout=150):
    last = None
    for i in range(tries):
        try:
            r = requests.post(url, data=data, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:80]}"
        time.sleep(3 * (i + 1))
    raise RuntimeError(last)


def tiles(bbox_wgs, max_deg=0.03):
    """Split the window into tiles of at most ~3.3 km so every Overpass query stays small (the public mirrors time out on city-sized windows)."""
    w, s, e, n = bbox_wgs
    nx, ny = max(1, int(np.ceil((e - w) / max_deg))), max(1, int(np.ceil((n - s) / max_deg)))
    xs, ys = np.linspace(w, e, nx + 1), np.linspace(s, n, ny + 1)
    return [(xs[i], ys[j], xs[i + 1], ys[j + 1]) for i in range(nx) for j in range(ny)]


def harvest_osm(bbox_wgs, log, cache: Path, offline=False):
    """Overpass queries per tile and tag group; every answer is cached per query (cache/osm_<hash>.json), so a re-run only repeats the queries that failed (the public mirrors are often overloaded).
    Returns (elements, mirrors used, note incl. the share of queries that succeeded)."""
    import hashlib
    cache.mkdir(parents=True, exist_ok=True)
    name_rx = "anganwadi|angan ?wadi|aanganwadi|icds|balwadi|PHC|sub.?cent|ZPHS|MPDO|MRO|tahsil|panchayat|hostel|ITI|polytechnic|college|school|hospital|clinic|office|police|court|post office"
    els, seen, used, ok, total, fails_in_row = [], set(), set(), 0, 0, 0
    for (w, s, e, n) in tiles(bbox_wgs):
        bb = f"({s:.5f},{w:.5f},{n:.5f},{e:.5f})"
        parts = [f'nwr["amenity"~"^(school|college|university|hospital|clinic|doctors|dentist|nursing_home|pharmacy|townhall|courthouse|police|post_office|community_centre|kindergarten|childcare|social_facility|fire_station|public_building|library)$"]{bb};',
                 f'nwr["building"~"^(school|hospital|government|civic|public|kindergarten|college|university)$"]{bb};',
                 f'nwr["office"="government"]{bb};nwr["government"]{bb};nwr["healthcare"]{bb};',
                 f'nwr["name"~"{name_rx}",i]["amenity"!~"^(restaurant|cafe|bank|atm|fuel|place_of_worship)$"]{bb};']
        for part in parts:
            total += 1
            cf = cache / f"osm_{hashlib.md5(part.encode()).hexdigest()[:16]}.json"
            data = None
            if cf.exists():
                data, used_m = json.loads(cf.read_text(encoding="utf-8")), "cache"
            elif not offline and fails_in_row < 4:                            # mirrors are down: stop wasting minutes, a later run resumes from the cache
                q = f"[out:json][timeout:90];({part});out tags center;"
                for url in OVERPASS:
                    try:
                        r = post(url, {"data": q}, tries=1, timeout=40)
                        data, used_m = r.json().get("elements", []), url.split("/")[2]
                        cf.write_text(json.dumps(data), encoding="utf-8")
                        break
                    except Exception:
                        pass
            if data is None:
                fails_in_row += 1
                continue
            fails_in_row = 0
            ok += 1
            used.add(used_m)
            for el in data:
                k = (el["type"], el["id"])
                if k not in seen:
                    seen.add(k); els.append(el)
    log(f"  OSM Overpass: {ok}/{total} queries answered ({len(els)} elements)")
    note = "" if ok == total else (f"PARTIAL: {ok} of {total} Overpass queries answered (public mirrors overloaded); the rest is covered only by the Photon text search; re-run to resume" if ok else "Overpass unreachable from this machine (all mirrors failed); only the Photon text search was used for OpenStreetMap")
    return els, ",".join(sorted(used)), note


PHOTON_Q = ["school", "college", "hospital", "clinic", "govt", "government", "office", "anganwadi", "panchayat", "police", "post office", "phc", "centre", "zp", "mpp", "high school", "primary", "public",
            "health", "hostel", "court", "library", "hall", "municipal", "mandal", "tahsildar", "bhavan", "vidyalaya", "junior", "degree", "polytechnic", "nursing", "maternity", "sub centre", "kindergarten", "kids"]
PHOTON_KEYS = {"amenity", "office", "building", "healthcare", "government", "social_facility", "emergency", "craft"}


def harvest_photon(bbox_wgs, log):
    """OpenStreetMap through the Photon geocoder (komoot): a text search, so it is a second, incomplete view of OSM used when Overpass is down and to cross-check it. Many queries, results de-duplicated by OSM id."""
    w, s, e, n = bbox_wgs
    seen, out, fails = set(), [], 0
    for q in PHOTON_Q:
        for tag in (None, "amenity", "office", "building"):
            prm = dict(q=q, bbox=f"{w},{s},{e},{n}", limit=60, lang="en")
            if tag:
                prm["osm_tag"] = tag
            try:
                r = requests.get("https://photon.komoot.io/api/", params=prm, headers=UA, timeout=40)
                if r.status_code != 200:
                    fails += 1
                    continue
                for f in r.json().get("features", []):
                    pr = f["properties"]
                    k = (pr.get("osm_type"), pr.get("osm_id"))
                    if k in seen or pr.get("osm_key") not in PHOTON_KEYS:
                        continue
                    seen.add(k)
                    out.append(dict(type={"N": "node", "W": "way", "R": "relation"}.get(pr.get("osm_type"), "node"), id=pr.get("osm_id"), center=dict(lon=f["geometry"]["coordinates"][0], lat=f["geometry"]["coordinates"][1]),
                                    tags={pr.get("osm_key"): pr.get("osm_value"), "name": pr.get("name", "")}))
            except Exception:
                fails += 1
            time.sleep(0.15)
    log(f"  OSM via Photon: {len(out)} facility-like objects ({fails} failed requests)")
    return out


def harvest_wikidata(bbox_wgs, log):
    w, s, e, n = bbox_wgs
    q = f"""SELECT ?item ?itemLabel ?coord ?classLabel WHERE {{ SERVICE wikibase:box {{ ?item wdt:P625 ?coord . bd:serviceParam wikibase:cornerSouthWest "Point({w} {s})"^^geo:wktLiteral .
      bd:serviceParam wikibase:cornerNorthEast "Point({e} {n})"^^geo:wktLiteral }} OPTIONAL {{ ?item wdt:P31 ?class }} SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,te". }} }}"""
    try:
        r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers=UA, timeout=90)
        r.raise_for_status()
        rows = r.json()["results"]["bindings"]
        log(f"  Wikidata: {len(rows)} items with coordinates in the window")
        return rows, ""
    except Exception as ex:
        log(f"  Wikidata: {type(ex).__name__}: {str(ex)[:80]}")
        return [], f"Wikidata unreachable: {str(ex)[:80]}"


def harvest_wikipedia(centre_wgs, radius_m, log):
    lon, lat = centre_wgs
    for i in range(3):
        try:
            r = requests.get("https://en.wikipedia.org/w/api.php", params=dict(action="query", list="geosearch", gscoord=f"{lat}|{lon}", gsradius=min(10000, int(radius_m)), gslimit=100, format="json"), headers=UA, timeout=40)
            if r.status_code == 200:
                rows = r.json().get("query", {}).get("geosearch", [])
                log(f"  Wikipedia geosearch: {len(rows)} articles")
                return rows, ""
        except Exception:
            pass
        time.sleep(4 * (i + 1))
    log("  Wikipedia geosearch: rate-limited / unreachable")
    return [], "Wikipedia geosearch unreachable or rate-limited"


def pass1(A: dict, out: Path, log, from_raw=False, extra_csv=None) -> tuple:
    """Candidate harvest -> DataFrame (one row per source record) + notes on sources."""
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    zone = A["cell"].buffer(HARVEST_BUFFER_M)
    wb = tuple(gpd.GeoSeries([zone], crs=CRS).to_crs(4326).total_bounds)
    notes, rows = {}, []
    # --- OSM
    els, mirror, err = harvest_osm(wb, log, raw / "osm_cache", offline=from_raw)
    legacy = raw / "osm_overpass.json"                                   # answers saved by an earlier run of this script (before the per-query cache)
    if legacy.exists():
        have = {(e["type"], e["id"]) for e in els}
        old = [e for e in json.loads(legacy.read_text(encoding="utf-8")) if (e["type"], e["id"]) not in have]
        els += old
        err = (err + "; " if err else "") + f"{len(old)} elements from an earlier saved Overpass answer"
    notes["OpenStreetMap (Overpass)"] = (err + "; " if err else "") + f"{len(els)} elements via {mirror}"
    pf = raw / "osm_photon.json"
    if from_raw and pf.exists():
        ph = json.loads(pf.read_text(encoding="utf-8"))
    else:
        ph = harvest_photon(wb, log)
        if ph:
            pf.write_text(json.dumps(ph), encoding="utf-8")
    notes["OpenStreetMap (Photon geocoder, text search)"] = f"{len(ph)} facility-like objects (a second, incomplete view of OSM; Overpass is the complete one)"
    have = {(el["type"], el["id"]) for el in els}
    els = els + [e for e in ph if (e["type"], e["id"]) not in have]
    for el in els:
        t = el.get("tags", {})
        c = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
        if c.get("lat") is None:
            continue
        rows.append(dict(source="OSM", source_id=f"{el['type']}/{el['id']}", name=t.get("name") or t.get("name:en") or "", tags=t, taxonomy=t.get("amenity", ""), lon=c["lon"], lat=c["lat"], confidence=np.nan,
                         status=("closed" if any(k.startswith(("disused", "abandoned", "was:")) for k in t) else "open"), is_area=el["type"] != "node"))
    # --- Overture places
    if A["places"] is not None:
        P = A["places"][A["places"].geometry.intersects(zone)]
    else:
        P = overture_places(wb, A["cfg"], raw, from_raw, log)
        P = P[P.geometry.intersects(zone)] if len(P) else P
    notes["Overture Maps Places"] = f"{len(P)} places in the window (all categories; release {A['cfg']['overture_release']})"
    for r in P.itertuples():
        lon, lat = TO_WGS.transform(r.geometry.x, r.geometry.y)
        rows.append(dict(source="Overture", source_id=r.id, name=r.name or "", tags={}, taxonomy=r.taxonomy_primary or "", lon=lon, lat=lat, confidence=float(r.confidence) if r.confidence == r.confidence else np.nan,
                         status=str(r.operating_status or "open"), is_area=False))
    # --- Wikidata / Wikipedia
    wf = raw / "wikidata.json"
    if from_raw and wf.exists():
        wd, werr = json.loads(wf.read_text(encoding="utf-8")), ""
    else:
        wd, werr = harvest_wikidata(wb, log)
        if wd:
            wf.write_text(json.dumps(wd), encoding="utf-8")
    seen = {}
    for b in wd:
        m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", b["coord"]["value"])
        if not m:
            continue
        qid = b["item"]["value"].rsplit("/", 1)[1]
        seen.setdefault(qid, dict(name=b.get("itemLabel", {}).get("value", ""), lon=float(m.group(1)), lat=float(m.group(2)), classes=[]))["classes"].append(b.get("classLabel", {}).get("value", ""))
    nwd = 0
    for qid, d in seen.items():
        if re.match(r"Q\d+$", d["name"]):
            continue
        rows.append(dict(source="Wikidata", source_id=qid, name=d["name"], tags={}, taxonomy=" ".join(d["classes"]).lower(), lon=d["lon"], lat=d["lat"], confidence=np.nan, status="open", is_area=False))
        nwd += 1
    notes["Wikidata (SPARQL box)"] = werr or f"{len(seen)} items with coordinates, {nwd} labelled"
    c0 = gpd.GeoSeries([A["cell"].centroid], crs=CRS).to_crs(4326).iloc[0]
    wk, kerr = harvest_wikipedia((c0.x, c0.y), 4000, log)
    for a in wk:
        rows.append(dict(source="Wikipedia", source_id=str(a["pageid"]), name=a["title"], tags={}, taxonomy="", lon=a["lon"], lat=a["lat"], confidence=np.nan, status="open", is_area=False))
    notes["Wikipedia geosearch"] = kerr or f"{len(wk)} articles within 4 km"
    notes["LGD / Telangana Govt / district directories"] = "no open API reachable from this sandbox (LGD, UDISE+, Telangana school / PHC / anganwadi directories are portals without a query API): not used unless a file is passed with --extra-csv"
    # --- local reference layers (Damarakunta TGRAC) and user-supplied directory extracts
    if A["v"] == "damarakunta":
        root = A["root"] / "reference"
        for f, label, namecol in (("tgrac_anganwadi.gpkg", "Anganwadi", "Anganwadi_Name"), ("tgrac_health.gpkg", "Hospital", "Facility_Name"), ("tgrac_sub_centres.gpkg", "Hospital", "Facility_Name"),
                                  ("damarakunta_priority_facilities.gpkg", None, "facility_name"), ("derived/damarakunta_priority_facilities_final_5.gpkg", None, "facility_name")):
            g = gpd.read_file(root / f).to_crs(CRS)
            for i, r in g.iterrows():
                lon, lat = TO_WGS.transform(r.geometry.x, r.geometry.y)
                rows.append(dict(source="TGRAC", source_id=f"{f}:{i}", name=str(r.get(namecol, "")), tags={}, taxonomy=(label or str(r.get("facility_type", ""))).lower(), lon=lon, lat=lat, confidence=np.nan, status="open", is_area=False))
        notes["TGRAC layers (Damarakunta, committed)"] = "anganwadi, health, sub-centre and priority-facility layers in Siddipet/Damarakunta/reference"
    if extra_csv:
        x = pd.read_csv(extra_csv)
        for i, r in x.iterrows():
            rows.append(dict(source="Directory file", source_id=f"{Path(extra_csv).name}:{i}", name=str(r["name"]), tags={}, taxonomy=str(r.get("category", "")).lower(), lon=float(r["lon"]), lat=float(r["lat"]), confidence=np.nan, status="open", is_area=False))
        notes["Directory file"] = f"{len(x)} records from {extra_csv}"
    df = pd.DataFrame(rows)
    return df, notes


def overture_places(wb, cfg, raw: Path, from_raw: bool, log) -> gpd.GeoDataFrame:
    """Damarakunta has no data/villages folder: fetch the Overture places of its window (pinned release)."""
    from shapely import from_wkb
    f = raw / "overture_places.gpkg"
    if f.exists() and from_raw:
        return gpd.read_file(f)
    from src.multivillage import acquire as A
    df, rel = A.overture(cfg, "places", "place", wb, ["id", "confidence", "basic_category", "operating_status", "names", "categories", "geometry"])
    g = gpd.GeoDataFrame(df.drop(columns=["geometry"]), geometry=[from_wkb(x) for x in df.geometry], crs=4326).to_crs(CRS)
    g["name"] = [(n or {}).get("primary") if isinstance(n, dict) else None for n in g.get("names", [None] * len(g))]
    g["taxonomy_primary"] = [(c or {}).get("primary") if isinstance(c, dict) else None for c in g.get("categories", [None] * len(g))]
    g = g.drop(columns=[c for c in ("names", "categories") if c in g])
    g.to_file(f, driver="GPKG")
    log(f"  Overture places (release {rel}): {len(g)}")
    return g


# ------------------------------------------------------------------------------------------------ pass 2
def pass2(A: dict, df: pd.DataFrame, prior_excl: pd.DataFrame | None, log) -> tuple:
    """Classify, remove false positives, merge duplicates across sources. Returns (clusters DataFrame, exclusions DataFrame)."""
    cell = A["cell"]
    excl = []
    ex_prev = {} if prior_excl is None else dict(zip(prior_excl["id"].astype(str), prior_excl["reason"]))
    recs = []
    for r in df.itertuples():
        x, y = FROM_WGS.transform(r.lon, r.lat)
        pt = Point(x, y)
        cat, why, sub = classify(r.name, r.tags if isinstance(r.tags, dict) else {}, r.taxonomy, r.source)
        # sources that are only candidates for orientation (Wikipedia articles, Wikidata items of other kinds) need a recognisable facility class
        if r.source in ("Wikipedia", "Wikidata") and cat is None and not why:
            why = "not a facility (article / item of another kind)"
        if cat is None and r.source in ("Wikipedia", "Wikidata"):
            continue                                                         # ordinary landmarks are not logged one by one (they are not facility candidates)
        d_out = float(pt.distance(cell)) if not pt.within(cell) else 0.0
        base = dict(source=r.source, source_id=r.source_id, name=r.name, category=cat, subtype=sub, lat=round(r.lat, 6), lon=round(r.lon, 6), x=x, y=y, confidence=r.confidence, status=r.status, is_area=r.is_area, dist_outside_m=round(d_out, 1))
        reason = None
        if str(r.source_id) in ex_prev and r.source == "Overture":
            reason = "carried over from the earlier exclusion list: " + str(ex_prev[str(r.source_id)])
        elif cat is None:
            reason = why
        elif str(r.status).lower() in ("closed", "permanently_closed", "temporarily_closed") or r.status == "closed":
            reason = f"closed / disused ({r.status})"
        elif r.source == "Overture" and r.confidence == r.confidence and r.confidence < 0.5 and not r.name:
            reason = "low-confidence unnamed record"
        elif d_out > 0:
            reason = f"outside the study polygon ({d_out:.0f} m){' - bordering' if d_out <= BORDER_M else ''}"
        if reason:
            excl.append(dict(base, reason=reason))
        else:
            recs.append(base)
    R = pd.DataFrame(recs)
    if not R.empty:                                                      # one point shared by several differently named records of one source = a locality / village centroid, not a surveyed building
        key = list(zip(R.source, R.x.round(0), R.y.round(0)))
        R["_k"] = key
        bad = set()
        for k, g in R.groupby("_k"):
            if g.name.map(norm).nunique() >= 2:
                bad |= set(g.index)
        for i in sorted(bad):
            r = R.loc[i]
            excl.append(dict(source=r.source, source_id=r.source_id, name=r["name"], category=r.category, subtype=r.subtype, lat=r.lat, lon=r.lon, dist_outside_m=r.dist_outside_m,
                             reason="placeholder coordinate: several differently named records of this source share one point (a village / locality centroid, not a surveyed building)"))
        R = R.drop(index=list(bad)).drop(columns="_k").reset_index(drop=True)
    if R.empty:
        return R, pd.DataFrame(excl)
    # cluster duplicates: same category; 25 m, or 120 m with a similar / contained name, or one name missing within 60 m
    n = len(R)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i in range(n):
        for j in range(i + 1, n):
            if R.category.iat[i] != R.category.iat[j]:
                continue
            d = float(np.hypot(R.x.iat[i] - R.x.iat[j], R.y.iat[i] - R.y.iat[j]))
            s = sim(R.name.iat[i], R.name.iat[j])
            if not same_facility_name(R.name.iat[i], R.name.iat[j]):
                continue                                                          # e.g. MPPS and ZPHS of one village, Anganwadi-III and -IX: never merged
            if d <= 25 or (d <= 120 and s >= 0.6) or (d <= 60 and (not R.name.iat[i] or not R.name.iat[j])) or (d <= 300 and s >= 0.9 and len(norm(R.name.iat[i])) > 6):
                parent[find(i)] = find(j)
    R["cluster"] = [find(i) for i in range(n)]
    out = []
    pri = {"OSM": 0, "TGRAC": 1, "Directory file": 1, "Wikidata": 2, "Overture": 3, "Wikipedia": 4}
    for cid, g in R.groupby("cluster"):
        g = g.assign(p=g.source.map(pri)).sort_values(["is_area", "p"], ascending=[False, True])
        best = g.iloc[0]
        names = [x for x in g.sort_values("p").name if x]
        nm = names[0] if names else ""
        srcs = sorted(set(g.source), key=lambda s: pri[s])
        out.append(dict(cluster=cid, name=nm, all_names=" | ".join(dict.fromkeys(names)), category=best.category, subtype=best.subtype, lat=best.lat, lon=best.lon, x=best.x, y=best.y,
                        sources=";".join(srcs), source_ids=";".join(f"{s}:{i}" for s, i in zip(g.source, g.source_id)), n_records=len(g), overture_conf=g.confidence.max()))
        for _, r in g.iloc[1:].iterrows():
            excl.append(dict(source=r.source, source_id=r.source_id, name=r["name"], category=r.category, subtype=r.subtype, lat=r.lat, lon=r.lon, reason=f"duplicate of '{nm or best['name']}' ({best.source}:{best.source_id}): same campus / facility across sources",
                             dist_outside_m=0.0))
    C = pd.DataFrame(out).sort_values(["category", "name"]).reset_index(drop=True)
    ov = load_overrides(A["v"])
    keep_rows = []
    for _, r in C.iterrows():
        o = override_for(ov, r["name"], r.source_ids)
        if o is not None and o.action == "exclude":
            excl.append(dict(source=r.sources, source_id=r.source_ids, name=r["name"], category=r.category, subtype=r.subtype, lat=r.lat, lon=r.lon, dist_outside_m=0.0, reason=f"manual review: {o.note}"))
            continue
        if o is not None and o.action.startswith("category:"):
            r = r.copy(); r["category"] = o.action.split(":", 1)[1]
        keep_rows.append(r)
    C = pd.DataFrame(keep_rows).reset_index(drop=True)
    log(f"  pass 2: {len(df)} source records -> {len(C)} facilities after cleaning, {len(excl)} removed / merged")
    return C, pd.DataFrame(excl)


# ------------------------------------------------------------------------------------------------ pass 3
def pass3(A: dict, C: pd.DataFrame, log) -> tuple:
    """Snap every facility to a footprint; facilities without a building within SNAP_M are removed."""
    fp = A["fp"]
    sidx = fp.sindex
    ov3 = load_overrides(A["v"])
    keep, drop = [], []
    for r in C.itertuples():
        p = Point(r.x, r.y)
        o = override_for(ov3, r.name, r.source_ids)
        if o is not None and o.action == "keep_pin":
            keep.append(dict(r._asdict(), snapped_to_building=True, snap_distance_m=0.0, building_area_m2=float("nan"), lat_snapped=r.lat, lon_snapped=r.lon, sx=r.x, sy=r.y, building_index=-1, snap_method=f"manual review: pin on a roof, building missing from the footprint layer ({o.note})"))
            continue
        idx = list(sidx.query(p.buffer(SNAP_M), predicate="intersects"))
        cand = fp.iloc[idx].copy()
        cand["d"] = cand.geometry.distance(p)
        cand = cand[cand.d <= SNAP_M]
        if cand.empty:
            drop.append(dict(r._asdict(), reason=f"no building within {SNAP_M:.0f} m of the point (field / road / wrong pin): needs an on-site check"))
            continue
        cand["a"] = cand.geometry.area
        inside = cand[cand.d == 0]
        if len(inside):
            b = inside.sort_values("a", ascending=False).iloc[0]
        else:
            real = cand[cand.a >= 25]                                           # a pin is never snapped onto a shed / hut-sized footprint if a real building is in range
            real = real if len(real) else cand
            b = real.sort_values(["d", "a"], ascending=[True, False]).iloc[0]
            if r.category in ("School", "College", "Hospital") and b.a < 60:      # big facilities: a compound building beats a gate house / hut next to it
                big = real[(real.a >= 300) & (real.d <= 25)]
                if len(big):
                    b = big.sort_values("d").iloc[0]
        from shapely.ops import nearest_points
        if b.geometry.contains(p):
            rp = p                                                            # already on the roof: keep the surveyed position
        else:                                                                 # nearest point of the building, moved 1.5 m inward (merged blobs: the representative point can be 20 m from the pin)
            q = nearest_points(b.geometry, p)[0]
            c = b.geometry.representative_point()
            dx, dy = c.x - q.x, c.y - q.y
            L = float(np.hypot(dx, dy)) or 1.0
            step = min(1.5, L)
            rp = Point(q.x + dx / L * step, q.y + dy / L * step)
            if not b.geometry.contains(rp):
                rp = q
        lon, lat = TO_WGS.transform(rp.x, rp.y)
        keep.append(dict(r._asdict(), snapped_to_building=True, snap_distance_m=round(float(p.distance(b.geometry)), 1), building_area_m2=round(float(b.a), 0), lat_snapped=round(lat, 6), lon_snapped=round(lon, 6),
                         sx=rp.x, sy=rp.y, building_index=int(b.name)))
    K, D = pd.DataFrame(keep), pd.DataFrame(drop)
    log(f"  pass 3: {len(K)} snapped to a building, {len(D)} removed (no building within {SNAP_M:.0f} m)")
    return K, D


def contact_sheets(A: dict, K: pd.DataFrame, outdir: Path, log, per_sheet=20, half=60.0):
    """Esri imagery chips (120 m) with footprint outlines, original point (red x) and snapped marker (cyan ring), numbered; the sheets are what a reviewer checks by eye."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from src.multivillage import segmentation_variant as SV
    mos = A["mosaic"]
    use_mosaic = Path(mos).exists()
    from PIL import Image
    import io
    fp = A["fp"]
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("contact_sheet_*.jpg"):
        old.unlink()
    n_sheets = int(np.ceil(len(K) / per_sheet)) if len(K) else 0
    for s in range(n_sheets):
        sub = K.iloc[s * per_sheet:(s + 1) * per_sheet]
        cols = 5
        rows_ = int(np.ceil(len(sub) / cols))
        fig, axs = plt.subplots(rows_, cols, figsize=(cols * 3.0, rows_ * 3.7), squeeze=False)
        for ax in axs.ravel():
            ax.axis("off")
        for ax, (_, r) in zip(axs.ravel(), sub.iterrows()):
            e = (r.sx - half, r.sy - half, r.sx + half, r.sy + half)
            try:
                if use_mosaic:
                    img, ex = SV._read_rgb(Path(mos), e, max_px=420)
                    ax.imshow(img, extent=ex, origin="upper")
                else:
                    im = None
                    eb = (r.sx - 150, r.sy - 150, r.sx + 150, r.sy + 150)          # the export service refuses windows below ~300 m; fetch 300 m (0.6 m/px) and crop to the 120 m chip
                    for _try in range(4):
                        resp = requests.get("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export", params=dict(bbox=",".join(map(str, eb)), bboxSR=32644, imageSR=32644, size="500,500", format="png", f="image"), headers=UA, timeout=60)
                        try:
                            im = Image.open(io.BytesIO(resp.content)).convert("RGB")
                            break
                        except Exception:
                            time.sleep(2 * (_try + 1))
                    if im is None:
                        raise RuntimeError("Esri export failed")
                    ax.imshow(im, extent=(eb[0], eb[2], eb[1], eb[3]), origin="upper")
            except Exception:
                ax.set_facecolor("#cccccc")
            near = fp[fp.geometry.intersects(box(*e))]
            if len(near):
                near.boundary.plot(ax=ax, color="#ffeb3b", lw=0.6)
            ax.plot([r.x], [r.y], marker="x", color="red", ms=7, mew=1.6)
            ax.plot([r.sx], [r.sy], marker="o", mfc="none", mec="#00e5ff", ms=11, mew=1.8)
            ax.set_xlim(e[0], e[2]); ax.set_ylim(e[1], e[3]); ax.axis("off")
            ax.set_title(f"{r.facility_id} {r.category}\n{(r['name'] or '(unnamed)')[:30]}  snap {r.snap_distance_m:g} m", fontsize=6.3)
        fig.suptitle(f"Facility contact sheet {s + 1}/{n_sheets}: red x = source point, cyan ring = snapped to footprint (yellow outlines); 120 m chips; Esri World Imagery ({'mosaic' if use_mosaic else 'export service'})", fontsize=7.5)
        fig.tight_layout(rect=(0, 0, 1, 0.97))
        fig.savefig(outdir / f"contact_sheet_{s + 1:02d}.jpg", dpi=110)
        plt.close(fig)
    log(f"  contact sheets: {n_sheets} in {outdir}")


# ------------------------------------------------------------------------------------------------ pass 4
def pass4(A: dict, K: pd.DataFrame, EX: pd.DataFrame, notes: dict, out: Path, log):
    v = A["v"]
    K = K.copy().reset_index(drop=True)
    K["facility_id"] = [f"{v[:3].upper()}-{FTYPE[c][:3].upper()}-{i + 1:03d}" for i, c in enumerate(K.category)]
    srcs = K.sources.str.split(";")
    K["verification_sources"] = [";".join(s + ["Esri 0.6 m imagery + footprint snap"]) for s in srcs]
    ok = [(d <= SNAP_OK_M) or (c in ("School", "College", "Hospital") and a >= 300 and d <= 25) for d, c, a in zip(K.snap_distance_m, K.category, K.building_area_m2)]       # campus rule: pin at the edge of a compound building
    K["confidence"] = ["high" if (len(s) >= 2 and o) else ("medium" if (len(s) >= 2 or o) and d <= SNAP_M else "low") for s, o, d in zip(srcs, ok, K.snap_distance_m)]
    K["use_in_analysis"] = K.confidence != "low"                      # snap > 12 m with a single source: the pin and the building may not belong together; listed for an on-site check, not used for routing or maps
    V = pd.DataFrame(dict(facility_id=K.facility_id, name=K["name"].replace("", "(unnamed)"), category=K.category, lat=K.lat_snapped, lon=K.lon_snapped, verification_sources=K.verification_sources, confidence=K.confidence,
                          snapped_to_building=K.snapped_to_building, use_in_analysis=K.use_in_analysis, snap_method=(K.snap_method.fillna("nearest footprint (pin moved onto the building)") if "snap_method" in K else "nearest footprint (pin moved onto the building)"), subtype=K.subtype, snap_distance_m=K.snap_distance_m, building_area_m2=K.building_area_m2, source_lat=K.lat, source_lon=K.lon, source_ids=K.source_ids,
                          other_names=K.all_names))
    V.to_csv(CFG_DIR / f"{v}_verified_facilities.csv", index=False, lineterminator="\n")
    cols = ["id", "name", "reason", "category", "source", "lat", "lon", "dist_outside_m"]
    E = EX.copy()
    E["id"] = E.source_id.astype(str)
    E = E.reindex(columns=cols)
    E.to_csv(CFG_DIR / f"{v}_facility_exclusions.csv", index=False, lineterminator="\n")
    d = AUDIT / v
    d.mkdir(parents=True, exist_ok=True)
    V.to_csv(d / "pass4_verified_facilities.csv", index=False, lineterminator="\n")
    E.to_csv(d / "pass4_exclusions.csv", index=False, lineterminator="\n")
    (d / "sources_checked.json").write_text(json.dumps(dict(village=v, date=time.strftime("%Y-%m-%d"), sources=notes, snap_m=SNAP_M, border_m=BORDER_M, harvest_buffer_m=HARVEST_BUFFER_M), indent=2, ensure_ascii=False), encoding="utf-8")
    (d / "README.md").write_text(f'''# Facility audit: {v}

Produced by `scripts/audit_facilities.py --village {v}` (four passes). Final tables: `pass4_verified_facilities.csv` (also `configs/multivillage/villages/{v}_verified_facilities.csv`, read by the pipeline) and
`pass4_exclusions.csv` (every removed or merged record with its reason; also `{v}_facility_exclusions.csv`).

| file | content |
|---|---|
| `pass1_candidates.csv` | every source record harvested (OpenStreetMap, Overture Places, Wikidata, Wikipedia, local reference layers) before any cleaning |
| `pass2_clusters.csv` | records after classification (five categories), false-positive removal and duplicate merging across sources |
| `pass3_snapping.csv` | each facility with its source point, the footprint it was snapped to, snap distance and building area |
| `pass4_verified_facilities.csv` | facility_id, name, category, lat, lon, verification_sources, confidence, snapped_to_building, use_in_analysis (False = low confidence, for an on-site check) |
| `contact_sheet_NN.jpg` | Esri imagery chips (120 m): red x = source point, cyan ring = final marker, yellow = footprints |
| `sources_checked.json` | which sources answered and how many records each gave; sources that were not reachable are stated |
| `raw/` | saved raw answers (Overpass per query, Photon, Wikidata, Overture places) so the audit can be redone offline (`--from-raw`) |
| `{v}_facility_overrides.csv` (in configs/multivillage/villages/) | manual decisions after looking at the contact sheets or Google Maps |

Limits: LGD / UDISE+ / Telangana directories have no open query API and were not used; Overpass mirrors were overloaded at times (see `sources_checked.json` for the share of answered queries);
snapping uses the open Overture footprints (StrongDINOv2Seg footprints exist only on the owner's PC); anything that needs a field visit is listed with `use_in_analysis = False` or in the exclusions.
''', encoding="utf-8")
    log(f"  pass 4: {len(V)} verified facilities ({V.category.value_counts().to_dict()}), {len(E)} exclusion-log rows -> {CFG_DIR.name}/{v}_verified_facilities.csv, {v}_facility_exclusions.csv")
    return V, E, K


def audit(v: str, a) -> None:
    log = lambda *x: print(*x, flush=True)
    log(f"\n=== facility audit: {v} ===")
    A = load_area(v, a.footprints)
    out = AUDIT / v
    out.mkdir(parents=True, exist_ok=True)
    prior = None
    pe = CFG_DIR / f"{v}_facility_exclusions.csv"
    if pe.exists() and not a.fresh:
        try:
            t = pd.read_csv(pe)
            prior = t[t.reason.astype(str).str.len() > 0] if {"id", "reason"} <= set(t.columns) else None
            prior = prior[~prior.reason.astype(str).str.contains("duplicate of|outside the study polygon|not one of the five|commercial|religious|no building within", regex=True)] if prior is not None else None
        except Exception:
            prior = None
    df, notes = pass1(A, out, log, a.from_raw, a.extra_csv)
    pd.DataFrame(df.assign(tags=df.tags.map(lambda t: json.dumps(t, ensure_ascii=False) if t else ""))).to_csv(out / "pass1_candidates.csv", index=False, lineterminator="\n")
    C, EX2 = pass2(A, df, prior, log)
    C.to_csv(out / "pass2_clusters.csv", index=False, lineterminator="\n")
    K, D3 = pass3(A, C, log)
    EX = pd.concat([EX2, D3.assign(source="merged", source_id=D3.get("source_ids", ""), dist_outside_m=0.0)[["source", "source_id", "name", "category", "lat", "lon", "reason", "dist_outside_m"]] if len(D3) else None], ignore_index=True)
    K = K.reset_index(drop=True)
    V, E, K = pass4(A, K, EX, notes, out, log)
    K.assign(facility_id=V.facility_id).to_csv(out / "pass3_snapping.csv", index=False, lineterminator="\n")
    contact_sheets(A, K.assign(facility_id=V.facility_id).rename(columns={}), out, log)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--village", required=True, choices=VILLAGES + ["all"])
    ap.add_argument("--from-raw", action="store_true", help="re-use the saved raw harvest in the audit folder (no network)")
    ap.add_argument("--fresh", action="store_true", help="ignore the existing exclusion file as a prior (default: its manual, non-automatic entries are kept)")
    ap.add_argument("--footprints", default=None, help="snap to this footprint layer (gpkg, layer 'buildings' for damarakunta) instead of the open Overture footprints")
    ap.add_argument("--retry-osm", action="store_true", help="only (re)try the Overpass queries that have no cached answer yet, then exit (use repeatedly while the public mirrors are overloaded)")
    ap.add_argument("--extra-csv", default=None, help="a directory extract you hold (columns name, lat, lon, category) added as source 'Directory file'")
    a = ap.parse_args()
    for v in (VILLAGES if a.village == "all" else [a.village]):
        if a.retry_osm:
            A = load_area(v, a.footprints)
            zone = A["cell"].buffer(HARVEST_BUFFER_M)
            wb = tuple(gpd.GeoSeries([zone], crs=CRS).to_crs(4326).total_bounds)
            els, mirror, err = harvest_osm(wb, lambda *x: print(f"[{v}]", *x, flush=True), AUDIT / v / "raw" / "osm_cache")
            print(f"[{v}] {err or 'all Overpass queries answered'}", flush=True)
            continue
        audit(v, a)


if __name__ == "__main__":
    main()
