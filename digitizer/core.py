"""Core logic for the Damarakunta roof digitizer.

Everything that touches geometry, coordinates or files lives here so it can be
tested without a browser.

Design rules (see README.md):
  * The raster and the candidate layer are opened read-only and never written.
  * Drawn polygons arrive as IMAGE-PIXEL coordinates of the cropped view; they are
    converted to EPSG:32644 map coordinates here with the crop's affine transform
    (never in the browser).
  * Work is autosaved to a sidecar draft file (JSON). The GeoPackage is only written by
    an explicit commit: backup -> temp copy -> write ONLY the reference_buildings layer ->
    verify (other layers and windows geometry/attributes identical) -> atomic replace.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import math
import os
import shutil
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from rasterio.windows import Window, from_bounds
from shapely.geometry import Polygon

EPSG = 32644
CRS = f"EPSG:{EPSG}"
LAYER_WINDOWS = "windows"
LAYER_REF = "reference_buildings"
EXTENT_NOTE = "TRACED_EXTENT"
UNSURE_NOTE = "unsure"
MIN_AREA_M2 = 2.0

DEFAULT_ROOT = Path(r"D:\Telangana_Rural_Project\Siddipet\Damarakunta")
DEFAULT_RASTER = DEFAULT_ROOT / "aligned" / "damarakunta_esri_highres_mosaic_0p6m.tif"
DEFAULT_GPKG = DEFAULT_ROOT / "results" / "v6_buildings" / "reference" / "digitize_windows.gpkg"
DEFAULT_CANDIDATES = DEFAULT_ROOT / "results" / "v6_buildings" / "candidate_buildings_full.gpkg"


class DigitizerError(Exception):
    """A problem the user should see verbatim (bad input, unsafe state, failed check)."""


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


# --------------------------------------------------------------------------- config
@dataclass
class Config:
    raster: Path
    gpkg: Path
    candidates: Path | None = None
    pad_m: float = 15.0

    def __post_init__(self):
        self.raster = Path(self.raster)
        self.gpkg = Path(self.gpkg)
        self.candidates = Path(self.candidates) if self.candidates else None

    @property
    def ref_dir(self) -> Path:
        return self.gpkg.parent

    @property
    def backup_dir(self) -> Path:
        return self.ref_dir / "digitizer_backups"

    @property
    def draft_path(self) -> Path:
        return self.ref_dir / "digitizer_draft.json"

    @property
    def status_path(self) -> Path:
        return self.ref_dir / "window_status.json"

    @property
    def log_path(self) -> Path:
        return self.ref_dir / "digitizer_commit_log.jsonl"


# --------------------------------------------------------------------------- coordinate conversion
def _apply(t, x, y):
    """Explicit affine arithmetic (independent of the affine package's operator overloading)."""
    return (t.a * x + t.b * y + t.c, t.d * x + t.e * y + t.f)


def px_to_map(transform, pixel_xy):
    """Continuous image-pixel coordinates -> map coordinates.

    (0, 0) is the OUTER upper-left corner of the upper-left pixel, exactly like the
    canvas origin in the browser, so no half-pixel offset is applied.
    """
    return [_apply(transform, float(x), float(y)) for x, y in pixel_xy]


def map_to_px(transform, map_xy):
    inv = ~transform
    return [_apply(inv, float(x), float(y)) for x, y in map_xy]


def _poly_to_px_rings(poly: Polygon, transform):
    rings = [list(poly.exterior.coords)] + [list(r.coords) for r in poly.interiors]
    return [[list(p) for p in map_to_px(transform, [(c[0], c[1]) for c in ring])] for ring in rings]


# --------------------------------------------------------------------------- gpkg helpers
def list_gpkg_layers(path: Path) -> list[str]:
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        rows = con.execute("SELECT table_name FROM gpkg_contents ORDER BY table_name").fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


def sqlite_integrity_ok(path: Path) -> bool:
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        con.close()


def layer_digest(path: Path, layer: str) -> str:
    """Order-sensitive SHA-256 over every attribute value and exact geometry bytes."""
    g = gpd.read_file(path, layer=layer)
    h = hashlib.sha256()
    h.update(("|".join(map(str, g.columns))).encode())
    for _, row in g.iterrows():
        for col in g.columns:
            if col == g.geometry.name:
                geom = row[col]
                h.update(b"NONE" if geom is None else geom.wkb)
            else:
                h.update(repr(row[col]).encode())
        h.update(b"\n")
    return h.hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_extent(note) -> bool:
    return EXTENT_NOTE in ("" if note is None or (isinstance(note, float) and math.isnan(note)) else str(note)).upper()


def _clean_note(note) -> str:
    if note is None or (isinstance(note, float) and math.isnan(note)):
        return ""
    return str(note)


# --------------------------------------------------------------------------- draft store
class Draft:
    """Sidecar JSON autosave. Written atomically after every change."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.data = self._load()

    @staticmethod
    def _empty():
        return {"version": 1, "features": [], "removed_committed": [], "complete": {}, "updated": None}

    def _load(self):
        if not self.path.exists():
            return self._empty()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:  # never silently discard someone's work
            raise DigitizerError(
                f"Draft file {self.path} could not be read ({e}). It was NOT overwritten. "
                f"A previous copy may exist as {self.path}.prev - rename the broken file and retry."
            )
        base = self._empty()
        base.update(d)
        return base

    def save(self):
        with self.lock:
            self.data["updated"] = _now()
            tmp = self.path.with_name(self.path.name + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f)
                f.flush()
                os.fsync(f.fileno())
            if self.path.exists():
                shutil.copy2(self.path, self.path.with_name(self.path.name + ".prev"))
            os.replace(tmp, self.path)


# --------------------------------------------------------------------------- project
class Project:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.lock = threading.RLock()
        for label, p in (("raster", cfg.raster), ("windows GeoPackage", cfg.gpkg)):
            if not Path(p).exists():
                raise DigitizerError(f"Missing {label}: {p}")
        self.draft = Draft(cfg.draft_path)
        self._cand = None

    # ---- reading -----------------------------------------------------------
    def read_windows(self) -> gpd.GeoDataFrame:
        if LAYER_WINDOWS not in list_gpkg_layers(self.cfg.gpkg):
            raise DigitizerError(f"Layer '{LAYER_WINDOWS}' not found in {self.cfg.gpkg}")
        g = gpd.read_file(self.cfg.gpkg, layer=LAYER_WINDOWS)
        if g.crs is None:
            raise DigitizerError("windows layer has no CRS; refusing to guess")
        if g.crs.to_epsg() != EPSG:
            g = g.to_crs(CRS)
        if "window_id" not in g.columns:
            raise DigitizerError("windows layer has no 'window_id' column")
        if g.empty:
            raise DigitizerError("windows layer is empty")
        return g.reset_index(drop=True)

    def _window(self, wid: str):
        g = self.read_windows()
        m = g[g["window_id"].astype(str) == str(wid)]
        if m.empty:
            raise DigitizerError(f"Unknown window_id '{wid}'")
        return m.iloc[0]

    def read_reference(self) -> gpd.GeoDataFrame:
        gp = self.cfg.gpkg
        if LAYER_REF not in list_gpkg_layers(gp):
            raise DigitizerError(f"Layer '{LAYER_REF}' not found in {gp}")
        g = gpd.read_file(gp, layer=LAYER_REF)
        if g.crs is None:
            raise DigitizerError(f"{LAYER_REF} has no CRS; refusing to guess")
        if g.crs.to_epsg() != EPSG:
            raise DigitizerError(
                f"{LAYER_REF} CRS is {g.crs}, expected {CRS}. Not reprojecting an existing layer on write."
            )
        for col in ("window_id", "note"):
            if col not in g.columns:
                g[col] = ""
        g["window_id"] = g["window_id"].map(_clean_note)
        g["note"] = g["note"].map(_clean_note)
        if "uid" not in g.columns:
            g["uid"] = None
        uids = []
        for _, r in g.iterrows():
            u = r["uid"]
            if u is None or (isinstance(u, float) and math.isnan(u)) or str(u) == "":
                digest = hashlib.sha1(
                    (r.geometry.wkb_hex + "|" + r["window_id"] + "|" + r["note"]).encode()
                ).hexdigest()[:12]
                u = "legacy-" + digest
            uids.append(str(u))
        g["uid"] = uids
        if g["uid"].duplicated().any():
            raise DigitizerError("Duplicate uid values in reference_buildings; fix before using the tool")
        return g.reset_index(drop=True)

    def _candidates(self):
        if self._cand is None:
            if not self.cfg.candidates or not Path(self.cfg.candidates).exists():
                self._cand = gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=CRS)
            else:
                g = gpd.read_file(self.cfg.candidates)
                if g.crs is None:
                    raise DigitizerError("candidate layer has no CRS; refusing to guess")
                self._cand = g.to_crs(CRS).reset_index(drop=True)
                _ = self._cand.sindex
        return self._cand

    # ---- raster crop -------------------------------------------------------
    def _crop_grid(self, src, bounds):
        if src.crs is None or src.crs.to_epsg() != EPSG:
            raise DigitizerError(f"Raster CRS is {src.crs}, expected {CRS}")
        t = src.transform
        if t.b != 0 or t.d != 0:
            raise DigitizerError("Raster is rotated/sheared; north-up rasters only")
        pad = self.cfg.pad_m
        w = from_bounds(bounds[0] - pad, bounds[1] - pad, bounds[2] + pad, bounds[3] + pad, transform=t)
        c0 = math.floor(w.col_off + 1e-9)
        r0 = math.floor(w.row_off + 1e-9)
        c1 = math.ceil(w.col_off + w.width - 1e-9)
        r1 = math.ceil(w.row_off + w.height - 1e-9)
        win = Window(c0, r0, c1 - c0, r1 - r0)
        return win, src.window_transform(win)

    def window_transform(self, wid: str):
        row = self._window(wid)
        with rasterio.open(self.cfg.raster) as src:
            win, tr = self._crop_grid(src, row.geometry.bounds)
        return tr, int(win.width), int(win.height)

    def render_png(self, wid: str) -> bytes:
        row = self._window(wid)
        with rasterio.open(self.cfg.raster) as src:  # read-only
            win, _tr = self._crop_grid(src, row.geometry.bounds)
            idx = [1, 2, 3] if src.count >= 3 else [1, 1, 1]
            data = src.read(idx, window=win, boundless=True, fill_value=0)
        if data.dtype != np.uint8:
            lo, hi = np.percentile(data[data > 0], [1, 99]) if (data > 0).any() else (0, 1)
            data = np.clip((data.astype(np.float32) - lo) / max(hi - lo, 1e-6), 0, 1)
            data = (data * 255).astype(np.uint8)
        img = Image.fromarray(np.moveaxis(data, 0, -1))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # ---- payloads ----------------------------------------------------------
    def _committed_by_window(self, ref: gpd.GeoDataFrame, windows: gpd.GeoDataFrame):
        ids = set(windows["window_id"].astype(str))
        out = {}
        for _, r in ref.iterrows():
            wid = r["window_id"]
            if wid not in ids:  # fall back to spatial membership
                pt = r.geometry.representative_point()
                hit = windows[windows.geometry.contains(pt)]
                wid = str(hit.iloc[0]["window_id"]) if len(hit) else ""
            out.setdefault(wid, []).append(r)
        return out

    def state(self) -> dict:
        with self.lock:
            windows = self.read_windows()
            ref = self.read_reference()
            comm = self._committed_by_window(ref, windows)
            removed = set(self.draft.data["removed_committed"])
            out = []
            for _, w in windows.iterrows():
                wid = str(w["window_id"])
                c_rows = [r for r in comm.get(wid, []) if r["uid"] not in removed]
                d_rows = [f for f in self.draft.data["features"] if f["window_id"] == wid]
                roofs = sum(1 for r in c_rows if not _is_extent(r["note"])) + sum(1 for f in d_rows if f["kind"] == "roof")
                unsure = sum(1 for r in c_rows if not _is_extent(r["note"]) and "unsure" in r["note"].lower()) + sum(
                    1 for f in d_rows if f["kind"] == "roof" and f["note"] == UNSURE_NOTE)
                extents = sum(1 for r in c_rows if _is_extent(r["note"])) + sum(1 for f in d_rows if f["kind"] == "extent")
                out.append({
                    "window_id": wid,
                    "role": _clean_note(w.get("role", "")) if hasattr(w, "get") else "",
                    "n_pred": int(w["n_pred"]) if "n_pred" in w.index and pd.notna(w["n_pred"]) else None,
                    "roofs": roofs, "unsure": unsure, "extents": extents,
                    "draft_pending": len(d_rows),
                    "complete": bool(self.draft.data["complete"].get(wid, False)),
                    "needs_extent": "CORE" in wid.upper(),
                })
            return {
                "windows": out,
                "gpkg": str(self.cfg.gpkg),
                "backup_dir": str(self.cfg.backup_dir),
                "draft_path": str(self.cfg.draft_path),
                "pending_new": len(self.draft.data["features"]),
                "pending_removed": len(self.draft.data["removed_committed"]),
            }

    def window_payload(self, wid: str) -> dict:
        with self.lock:
            windows = self.read_windows()
            row = self._window(wid)
            with rasterio.open(self.cfg.raster) as src:
                win, tr = self._crop_grid(src, row.geometry.bounds)
            width, height = int(win.width), int(win.height)
            geom = row.geometry
            polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
            window_px = [_poly_to_px_rings(p, tr)[0] for p in polys]

            feats = []
            ref = self.read_reference()
            comm = self._committed_by_window(ref, windows).get(str(wid), [])
            removed = set(self.draft.data["removed_committed"])
            for r in comm:
                for p in (list(r.geometry.geoms) if r.geometry.geom_type == "MultiPolygon" else [r.geometry]):
                    feats.append({"uid": r["uid"], "source": "committed", "removed": r["uid"] in removed,
                                  "kind": "extent" if _is_extent(r["note"]) else "roof",
                                  "note": r["note"], "rings": _poly_to_px_rings(p, tr)})
            for f in self.draft.data["features"]:
                if f["window_id"] != str(wid):
                    continue
                p = Polygon(f["coords"])
                feats.append({"uid": f["uid"], "source": "draft", "removed": False, "kind": f["kind"],
                              "note": f["note"], "rings": _poly_to_px_rings(p, tr)})

            cands = []
            cg = self._candidates()
            if len(cg):
                from shapely.geometry import box
                x0, y0 = _apply(tr, 0, height)
                x1, y1 = _apply(tr, width, 0)
                hits = cg.sindex.query(box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), predicate="intersects")
                for i in hits:
                    g = cg.geometry.iloc[int(i)]
                    for p in (list(g.geoms) if g.geom_type == "MultiPolygon" else [g]):
                        cands.append({"rings": _poly_to_px_rings(p, tr)})
            return {
                "window_id": str(wid), "width": width, "height": height,
                "transform": [tr.a, tr.b, tr.c, tr.d, tr.e, tr.f],
                "crs": CRS, "window_px": window_px, "features": feats, "candidates": cands,
                "complete": bool(self.draft.data["complete"].get(str(wid), False)),
            }

    # ---- editing (draft only) ----------------------------------------------
    def add_feature(self, wid: str, kind: str, unsure: bool, pixels) -> dict:
        if kind not in ("roof", "extent"):
            raise DigitizerError("kind must be 'roof' or 'extent'")
        tr, _w, _h = self.window_transform(wid)
        pts = []
        for p in pixels:
            xy = (float(p[0]), float(p[1]))
            if not (math.isfinite(xy[0]) and math.isfinite(xy[1])):
                raise DigitizerError("Non-finite vertex")
            if not pts or math.hypot(xy[0] - pts[-1][0], xy[1] - pts[-1][1]) > 1e-6:
                pts.append(xy)
        if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= 1e-6:
            pts.pop()
        if len(pts) < 3:
            raise DigitizerError("A polygon needs at least 3 distinct vertices")
        poly = Polygon(px_to_map(tr, pts))
        if not poly.is_valid:
            raise DigitizerError("Polygon is self-intersecting. Nothing was saved - redraw it.")
        if poly.area < MIN_AREA_M2:
            raise DigitizerError(f"Polygon area {poly.area:.2f} m2 is below the {MIN_AREA_M2} m2 minimum")
        return self._store(wid, kind, EXTENT_NOTE if kind == "extent" else (UNSURE_NOTE if unsure else ""), poly)

    def add_extent_whole_window(self, wid: str) -> dict:
        row = self._window(wid)
        g = row.geometry
        if g.geom_type != "Polygon":
            raise DigitizerError("Window geometry is not a single polygon")
        return self._store(wid, "extent", EXTENT_NOTE, Polygon(g.exterior.coords))

    def _store(self, wid, kind, note, poly: Polygon) -> dict:
        with self.draft.lock:
            feat = {"uid": uuid.uuid4().hex[:12], "window_id": str(wid), "kind": kind, "note": note,
                    "coords": [list(c) for c in poly.exterior.coords][:-1], "created": _now()}
            self.draft.data["features"].append(feat)
            self.draft.save()
        return {"uid": feat["uid"], "area_m2": round(poly.area, 2)}

    def delete_feature(self, uid: str, confirm_committed: bool = False) -> dict:
        with self.draft.lock:
            feats = self.draft.data["features"]
            for i, f in enumerate(feats):
                if f["uid"] == uid:
                    feats.pop(i)
                    self.draft.save()
                    return {"deleted": "draft"}
            ref = self.read_reference()
            if uid in set(ref["uid"]):
                if not confirm_committed:
                    raise DigitizerError("Deleting an already committed polygon needs explicit confirmation")
                if uid not in self.draft.data["removed_committed"]:
                    self.draft.data["removed_committed"].append(uid)
                self.draft.save()
                return {"deleted": "committed (applies at next commit)"}
        raise DigitizerError(f"No polygon with uid {uid}")

    def restore_feature(self, uid: str) -> dict:
        with self.draft.lock:
            if uid in self.draft.data["removed_committed"]:
                self.draft.data["removed_committed"].remove(uid)
                self.draft.save()
            return {"restored": uid}

    def set_unsure(self, uid: str, unsure: bool) -> dict:
        with self.draft.lock:
            for f in self.draft.data["features"]:
                if f["uid"] == uid:
                    if f["kind"] != "roof":
                        raise DigitizerError("Only roofs can be marked unsure")
                    f["note"] = UNSURE_NOTE if unsure else ""
                    self.draft.save()
                    return {"note": f["note"]}
        raise DigitizerError("Only uncommitted (draft) polygons can be re-labelled; delete and redraw a committed one")

    def set_complete(self, wid: str, flag: bool) -> dict:
        st = {w["window_id"]: w for w in self.state()["windows"]}
        if str(wid) not in st:
            raise DigitizerError(f"Unknown window_id '{wid}'")
        w = st[str(wid)]
        if flag and w["needs_extent"] and w["extents"] == 0:
            raise DigitizerError(
                f"{wid} is a partially traced window: draw a TRACED_EXTENT around the area you finished "
                f"(or use 'Whole window = traced extent') before marking it complete."
            )
        with self.draft.lock:
            if flag:
                self.draft.data["complete"][str(wid)] = True
            else:
                self.draft.data["complete"].pop(str(wid), None)
            self.draft.save()
        return {"complete": bool(flag)}

    # ---- commit --------------------------------------------------------------
    def _build_commit_frame(self):
        windows = self.read_windows()
        ids = set(windows["window_id"].astype(str))
        existing = self.read_reference()
        removed = set(self.draft.data["removed_committed"])
        errors, warnings = [], []
        keep = existing[~existing["uid"].isin(removed)].copy()
        existing_uids = set(existing["uid"])
        rows, dupes = [], 0
        for f in self.draft.data["features"]:
            if f["uid"] in existing_uids:
                dupes += 1
                continue
            if f["window_id"] not in ids:
                errors.append(f"Draft polygon {f['uid']} refers to unknown window '{f['window_id']}'")
                continue
            poly = Polygon(f["coords"])
            if (not poly.is_valid) or poly.is_empty or poly.area < MIN_AREA_M2:
                errors.append(f"Draft polygon {f['uid']} in {f['window_id']} is invalid or too small")
                continue
            rows.append({"window_id": f["window_id"], "note": f["note"], "uid": f["uid"], "geometry": poly})
        if rows:
            new = gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS)
        else:
            new = gpd.GeoDataFrame({"window_id": [], "note": [], "uid": []}, geometry=[], crs=CRS)
        out = pd.concat([keep, new], ignore_index=True)
        out = gpd.GeoDataFrame(out, geometry="geometry", crs=CRS)
        if len(out):
            bad = out[~out.geometry.is_valid | out.geometry.is_empty]
            if len(bad):
                errors.append(f"{len(bad)} geometries would be invalid/empty after commit")
            if out["uid"].duplicated().any():
                errors.append("Duplicate uid in the frame to be written")
        return existing, keep, new, out, removed, dupes, errors, warnings

    def commit_preview(self) -> dict:
        with self.lock:
            existing, keep, new, out, removed, dupes, errors, warnings = self._build_commit_frame()
            per = {}
            for _, r in new.iterrows():
                d = per.setdefault(r["window_id"], {"roofs": 0, "unsure": 0, "extents": 0})
                if _is_extent(r["note"]):
                    d["extents"] += 1
                else:
                    d["roofs"] += 1
                    d["unsure"] += int(r["note"] == UNSURE_NOTE)
            st = self.state()["windows"]
            complete = [w["window_id"] for w in st if w["complete"]]
            for w in st:
                if w["complete"] and w["needs_extent"] and w["extents"] == 0:
                    errors.append(f"{w['window_id']} marked complete but has no TRACED_EXTENT")
                if (w["roofs"] or w["extents"]) and not w["complete"]:
                    warnings.append(f"{w['window_id']} has traced polygons but is not marked complete - "
                                    f"the evaluation will skip it")
            has_changes = bool(len(new) or removed)
            return {
                "gpkg": str(self.cfg.gpkg),
                "backup_dir": str(self.cfg.backup_dir),
                "existing_total": int(len(existing)),
                "removed": [{"uid": u} for u in sorted(removed)],
                "new_by_window": per, "new_total": int(len(new)),
                "total_after": int(len(out)), "duplicates_skipped": dupes,
                "complete_windows": complete,
                "windows_layer_digest": layer_digest(self.cfg.gpkg, LAYER_WINDOWS)[:16],
                "errors": errors, "warnings": warnings, "has_changes": has_changes,
            }

    def commit(self, confirm: str) -> dict:
        if confirm != "COMMIT":
            raise DigitizerError("Commit needs explicit confirmation")
        with self.lock:
            gp = self.cfg.gpkg
            existing, keep, new, out, removed, dupes, errors, warnings = self._build_commit_frame()
            if errors:
                raise DigitizerError("Commit blocked:\n- " + "\n- ".join(errors))
            st_windows = self.state()["windows"]
            for w in st_windows:
                if w["complete"] and w["needs_extent"] and w["extents"] == 0:
                    raise DigitizerError(f"Commit blocked: {w['window_id']} is complete but has no TRACED_EXTENT")
            has_changes = bool(len(new) or removed)
            layers_before = list_gpkg_layers(gp)
            win_digest_before = layer_digest(gp, LAYER_WINDOWS)
            other_digests = {l: layer_digest(gp, l) for l in layers_before if l not in (LAYER_REF,)}
            backup = None
            if has_changes:
                self.cfg.backup_dir.mkdir(parents=True, exist_ok=True)
                first = self.cfg.backup_dir / f"{gp.stem}.ORIGINAL_before_digitizer.gpkg"
                if not first.exists():
                    shutil.copy2(gp, first)
                backup = self.cfg.backup_dir / f"{gp.stem}_{_stamp()}_pre_commit.gpkg"
                shutil.copy2(gp, backup)
                tmp = gp.with_name(f".{gp.stem}.commit_{uuid.uuid4().hex[:8]}.tmp.gpkg")
                try:
                    shutil.copy2(gp, tmp)
                    kwargs = {} if len(out) else {"geometry_type": "Polygon"}
                    out.to_file(tmp, layer=LAYER_REF, driver="GPKG", **kwargs)
                    self._verify_written(tmp, layers_before, other_digests, out)
                    try:
                        os.replace(tmp, gp)
                    except PermissionError:
                        raise DigitizerError(
                            "The GeoPackage is open in another program (QGIS, Python, ...). Close it and commit again. "
                            "Nothing was changed; your draft is intact."
                        )
                finally:
                    if tmp.exists():
                        try:
                            tmp.unlink()
                        except OSError:
                            pass
                # post-replace check against the live file; roll back from backup on any mismatch
                try:
                    self._verify_written(gp, layers_before, other_digests, out)
                except Exception:
                    shutil.copy2(backup, gp)
                    raise
            # status file (which windows the evaluation should score)
            complete = sorted(w["window_id"] for w in st_windows if w["complete"])
            extents = {w["window_id"]: w["extents"] for w in st_windows}
            status = {"written": _now(), "gpkg": str(gp), "complete_windows": complete, "extents_per_window": extents}
            tmp_status = self.cfg.status_path.with_name(self.cfg.status_path.name + ".tmp")
            with open(tmp_status, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
            os.replace(tmp_status, self.cfg.status_path)
            # draft now contains nothing that is not in the GeoPackage
            with self.draft.lock:
                self.draft.data["features"] = []
                self.draft.data["removed_committed"] = []
                self.draft.save()
            win_digest_after = layer_digest(gp, LAYER_WINDOWS)
            result = {
                "committed_new": int(len(new)), "removed": len(removed), "total_in_layer": int(len(out)),
                "backup": str(backup) if backup else None,
                "windows_layer_unchanged": win_digest_after == win_digest_before,
                "status_file": str(self.cfg.status_path), "complete_windows": complete,
            }
            with open(self.cfg.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"time": _now(), **result}) + "\n")
            return result

    def _verify_written(self, path: Path, layers_before, other_digests, expected: gpd.GeoDataFrame):
        if not sqlite_integrity_ok(path):
            raise DigitizerError("SQLite integrity check failed on the written GeoPackage; aborted")
        layers_after = list_gpkg_layers(path)
        if set(layers_after) != set(layers_before):
            raise DigitizerError(f"Layer list changed ({layers_before} -> {layers_after}); aborted, original untouched")
        for l, dg in other_digests.items():
            if layer_digest(path, l) != dg:
                raise DigitizerError(f"Layer '{l}' differs after write; aborted, original untouched")
        back = gpd.read_file(path, layer=LAYER_REF)
        if back.crs is None or back.crs.to_epsg() != EPSG:
            raise DigitizerError("Written reference layer lost its CRS; aborted")
        if len(back) != len(expected):
            raise DigitizerError(f"Row count mismatch after write ({len(back)} vs {len(expected)}); aborted")
        if set(back["uid"].astype(str)) != set(expected["uid"].astype(str)):
            raise DigitizerError("uid set mismatch after write; aborted")
        if len(back) and not back.geometry.is_valid.all():
            raise DigitizerError("Invalid geometry after write; aborted")
        exp = {r["uid"]: r.geometry for _, r in expected.iterrows()}
        for _, r in back.iterrows():
            if not r.geometry.equals_exact(exp[str(r["uid"])], 1e-6):
                raise DigitizerError(f"Geometry for {r['uid']} changed during write; aborted")

    # ---- self check ----------------------------------------------------------
    def selfcheck(self) -> list[str]:
        lines = []
        with rasterio.open(self.cfg.raster) as src:
            lines.append(f"raster: {self.cfg.raster.name} | CRS {src.crs} | {src.width}x{src.height} px | "
                         f"res {src.res} | bands {src.count} | dtype {src.dtypes[0]} | nodata {src.nodata}")
            if src.crs is None or src.crs.to_epsg() != EPSG:
                raise DigitizerError("Raster CRS is not EPSG:32644")
        lines.append(f"gpkg layers: {list_gpkg_layers(self.cfg.gpkg)}")
        w = self.read_windows()
        lines.append(f"windows: {len(w)} -> {list(w['window_id'])} | columns {[c for c in w.columns if c != 'geometry']}")
        ref = self.read_reference()
        lines.append(f"reference_buildings: {len(ref)} rows | columns {[c for c in ref.columns if c != 'geometry']} | CRS {ref.crs}")
        c = self._candidates()
        lines.append(f"candidates: {len(c)} polygons | CRS {c.crs}")
        for wid in w["window_id"].astype(str):
            tr, wd, ht = self.window_transform(wid)
            row = self._window(wid)
            (cx, cy) = (row.geometry.centroid.x, row.geometry.centroid.y)
            px = map_to_px(tr, [(cx, cy)])[0]
            back = px_to_map(tr, [px])[0]
            err = math.hypot(back[0] - cx, back[1] - cy)
            lines.append(f"  {wid}: crop {wd}x{ht}px | centre->px ({px[0]:.1f},{px[1]:.1f}) -> map round-trip error {err:.2e} m")
        return lines
