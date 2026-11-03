"""Local browser-based roof digitizer for Damarakunta.

Run (Windows Command Prompt, project venv active):
    cd /d D:\\Telangana_Rural_Project\\digitizer
    python app.py

Serves ONLY on 127.0.0.1. Reads the raster/candidates read-only; the GeoPackage is written
only by the explicit Commit action (see core.py / README.md).
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from core import (Config, DigitizerError, Project, DEFAULT_CANDIDATES, DEFAULT_GPKG,  # noqa: E402
                  DEFAULT_RASTER)

TOKEN = secrets.token_urlsafe(16)
PROJECT: Project | None = None
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    server_version = "RoofDigitizer/1.0"

    def log_message(self, fmt, *args):  # quiet; errors are printed explicitly
        pass

    # ---- helpers
    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"))

    def _host_ok(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def _route(self, method):
        if not self._host_ok():
            return self._send(403, b"bad host", "text/plain")
        url = urlparse(self.path)
        q = parse_qs(url.query)
        path = url.path
        try:
            if method == "GET" and path == "/":
                html = (HERE / "static" / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            if not path.startswith("/api/"):
                return self._send(404, b"not found", "text/plain")
            if q.get("t", [""])[0] != TOKEN:
                return self._send(403, b"bad token", "text/plain")
            body = {}
            if method == "POST":
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
            P = PROJECT
            if method == "GET" and path == "/api/state":
                return self._json(P.state())
            m = re.fullmatch(r"/api/window/([^/]+)", path)
            if method == "GET" and m:
                return self._json(P.window_payload(_unq(m.group(1))))
            m = re.fullmatch(r"/api/window/([^/]+)/image\.png", path)
            if method == "GET" and m:
                return self._send(200, P.render_png(_unq(m.group(1))), "image/png")
            if method == "GET" and path == "/api/commit/preview":
                return self._json(P.commit_preview())
            if method == "POST":
                if path == "/api/draft/add":
                    return self._json(P.add_feature(body["window_id"], body["kind"], bool(body.get("unsure")), body["pixels"]))
                if path == "/api/draft/extent_whole":
                    return self._json(P.add_extent_whole_window(body["window_id"]))
                if path == "/api/draft/delete":
                    return self._json(P.delete_feature(body["uid"], bool(body.get("confirm_committed"))))
                if path == "/api/draft/restore":
                    return self._json(P.restore_feature(body["uid"]))
                if path == "/api/draft/unsure":
                    return self._json(P.set_unsure(body["uid"], bool(body["unsure"])))
                if path == "/api/window/complete":
                    return self._json(P.set_complete(body["window_id"], bool(body["complete"])))
                if path == "/api/commit":
                    return self._json(P.commit(body.get("confirm", "")))
            return self._send(404, b"not found", "text/plain")
        except DigitizerError as e:
            return self._json({"error": str(e)}, 400)
        except (KeyError, ValueError, TypeError) as e:
            return self._json({"error": f"Bad request: {e!r}"}, 400)
        except Exception as e:  # unexpected: report, keep serving
            traceback.print_exc()
            return self._json({"error": f"Internal error: {e!r}"}, 500)

    def do_GET(self):
        self._route("GET")

    def do_POST(self):
        self._route("POST")


def _unq(s: str) -> str:
    from urllib.parse import unquote
    return unquote(s)


def build_server(project: Project, port: int):
    global PROJECT
    PROJECT = project
    for p in range(port, port + 20):
        try:
            return ThreadingHTTPServer(("127.0.0.1", p), Handler), p
        except OSError:
            continue
    raise SystemExit(f"No free port in {port}-{port + 19}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raster", default=str(DEFAULT_RASTER))
    ap.add_argument("--gpkg", default=str(DEFAULT_GPKG))
    ap.add_argument("--candidates", default=str(DEFAULT_CANDIDATES))
    ap.add_argument("--pad-m", type=float, default=15.0, help="context margin around each window (metres)")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="read-only checks, then exit")
    a = ap.parse_args()
    try:
        proj = Project(Config(a.raster, a.gpkg, a.candidates, a.pad_m))
        if a.selfcheck:
            print("\n".join(proj.selfcheck()))
            print("SELFCHECK OK (nothing was written)")
            return
        srv, port = build_server(proj, a.port)
    except DigitizerError as e:
        raise SystemExit(f"ERROR: {e}")
    url = f"http://127.0.0.1:{port}/"
    print(f"Roof digitizer running at {url}   (Ctrl+C to stop)")
    print(f"  GeoPackage : {a.gpkg}\n  Draft file : {proj.cfg.draft_path}\n  Backups in : {proj.cfg.backup_dir}")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your draft is saved; the GeoPackage changes only when you press Commit.")


if __name__ == "__main__":
    main()
