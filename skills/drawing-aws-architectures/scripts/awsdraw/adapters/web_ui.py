"""Local web UI (stdlib http.server) bound to 127.0.0.1: paste or upload a use case, get a .drawio.

Hardening: loopback only, Host/Origin checks (DNS-rebinding/CSRF), JSON-only POSTs, body size cap,
uploads written to a throw-away temp dir with sanitised names, saves restricted to one output folder.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import tempfile
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from ..domain.errors import SpecError

MAX_BODY = 40 * 1024 * 1024
ALLOWED_SUFFIXES = {".txt", ".md", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


@dataclass
class UiDeps:
    analyze: Callable[[str, list[str], str], dict]  # (text, file paths, mode) -> response dict
    save: Callable[[str, str], tuple[str, bool]]  # (xml, filename) -> (path, opened)
    providers: list  # enabled AI providers, e.g. ["github", "anthropic"]


def _safe_name(name: str, fallback: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)[:80].strip("._")
    return base or fallback


def make_handler(deps: UiDeps, page: str, port_getter: Callable[[], int]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "awsdraw"

        def log_message(self, *args):  # keep the terminal quiet
            pass

        def _origin_ok(self) -> bool:
            port = port_getter()
            allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if self.headers.get("Host", "") not in allowed_hosts:
                return False
            origin = self.headers.get("Origin")
            return origin is None or origin in {f"http://{h}" for h in allowed_hosts}

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; img-src 'self' data:")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: dict) -> None:
            self._send(code, json.dumps(obj).encode(), "application/json; charset=utf-8")

        def do_GET(self):  # noqa: N802
            if not self._origin_ok():
                return self._json(403, {"error": "Forbidden host"})
            if self.path in ("/", "/index.html"):
                return self._send(200, page.replace("__PROVIDERS__", json.dumps(deps.providers)).encode(), "text/html; charset=utf-8")
            self._json(404, {"error": "Not found"})

        def do_POST(self):  # noqa: N802
            if not self._origin_ok():
                return self._json(403, {"error": "Forbidden host"})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self._json(415, {"error": "JSON body required"})
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._json(413, {"error": f"Body must be 1 byte to {MAX_BODY // (1024 * 1024)} MB."})
            try:
                data = json.loads(self.rfile.read(length))
                if self.path == "/api/generate":
                    return self._json(200, self._generate(data))
                if self.path == "/api/save":
                    path, opened = deps.save(str(data.get("xml", "")), str(data.get("filename", "architecture.drawio")))
                    return self._json(200, {"path": path, "opened": opened})
                self._json(404, {"error": "Not found"})
            except SpecError as exc:
                self._json(400, {"error": str(exc)})
            except (json.JSONDecodeError, AttributeError, TypeError, binascii.Error):
                self._json(400, {"error": "Malformed request."})

        @staticmethod
        def _generate(data: dict) -> dict:
            files = data.get("files") or []
            if len(files) > 8:
                raise SpecError("Attach at most 8 files.")
            with tempfile.TemporaryDirectory(prefix="awsdraw-") as tmp:
                paths = []
                for i, f in enumerate(files):
                    name = _safe_name(str(f.get("name", "")), f"file{i}")
                    if Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
                        raise SpecError(f"'{name}': unsupported type. Use {', '.join(sorted(ALLOWED_SUFFIXES))}.")
                    target = Path(tmp) / f"{i}_{name}"
                    target.write_bytes(base64.b64decode(str(f.get("data", "")), validate=True))
                    paths.append(str(target))
                mode = str(data.get("mode") or "offline")
                if mode not in ("offline", "github", "anthropic"):
                    raise SpecError("Unknown mode.")
                return deps.analyze(str(data.get("text", ""))[:50000], paths, mode)

    return Handler


def serve(deps: UiDeps, page: str, port: int = 8765) -> ThreadingHTTPServer:
    holder: dict[str, ThreadingHTTPServer] = {}
    handler = make_handler(deps, page, lambda: holder["s"].server_address[1])
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    holder["s"] = server
    return server
