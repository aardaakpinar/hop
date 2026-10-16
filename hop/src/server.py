"""HTTP layer: static UI plus JSON API. Business logic lives in the services and scanner layers."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .. import APP_NAME, __version__
from .config import LOOPBACK, Settings
from .errors import HopError, NotFoundError, ValidationError
from .netutil import is_admin, local_ip
from .proxy import ReverseProxy
from .scanner import PortScanner
from .services import RouteService

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
STATIC_DIR = WEB_DIR / "static"
MAX_BODY = 64 * 1024
CONTENT_TYPES = {".css": "text/css", ".js": "application/javascript", ".svg": "image/svg+xml"}
SECURITY_HEADERS = {"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                    "Referrer-Policy": "no-referrer", "Cache-Control": "no-cache"}

# (method, path regex, handler): adding an endpoint takes a single line
_ROUTES = [(m, re.compile(p), h) for m, p, h in (
    ("GET", r"/", "index"),
    ("GET", r"/static/([\w.-]+)", "static"),
    ("GET", r"/api/status", "status"),
    ("GET", r"/api/routes", "list_routes"),
    ("POST", r"/api/routes", "save_route"),
    ("DELETE", r"/api/routes/([a-z0-9.-]+)", "delete_route"),
    ("GET", r"/api/scan", "scan_state"),
    ("POST", r"/api/scan", "start_scan"),
)]


@dataclass(frozen=True)
class ServerContext:
    settings: Settings
    routes: RouteService
    scanner: PortScanner
    proxy: ReverseProxy

    @property
    def allowed_hosts(self) -> frozenset:
        """DNS-rebinding protection: only these Host/Origin values are accepted."""
        return frozenset({LOOPBACK, "localhost", self.settings.panel_name})


class ApiHandler(BaseHTTPRequestHandler):
    ctx: ServerContext

    def log_message(self, fmt: str, *args: Any) -> None:
        log.debug("%s - %s", self.address_string(), fmt % args)

    do_GET = lambda self: self._dispatch("GET")        # noqa: E731
    do_POST = lambda self: self._dispatch("POST")      # noqa: E731
    do_DELETE = lambda self: self._dispatch("DELETE")  # noqa: E731

    # -- dispatch ------------------------------------------------------
    def _dispatch(self, method: str) -> None:
        if not self._allowed():
            return self._json({"error": "forbidden"}, 403)
        path = urlsplit(self.path).path
        matched = False
        try:
            for verb, pattern, name in _ROUTES:
                m = pattern.fullmatch(path)
                if not m:
                    continue
                matched = True
                if verb == method:
                    body = getattr(self, f"_h_{name}")(*m.groups())
                    if body is not None:
                        self._json(body)
                    return
            self._json({"error": "method not allowed" if matched else "not found"}, 405 if matched else 404)
        except HopError as exc:
            self._json({"error": str(exc)}, exc.status)
        except json.JSONDecodeError:
            self._json({"error": "Invalid JSON"}, 400)
        except Exception:
            log.exception("Request failed: %s %s", method, path)
            self._json({"error": "Server error"}, 500)

    def _allowed(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].lower()
        origin = self.headers.get("Origin")
        allowed = self.ctx.allowed_hosts
        return host in allowed and (not origin or (urlsplit(origin).hostname or "") in allowed)

    # -- handlers ------------------------------------------------------
    def _h_index(self) -> None:
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8").replace("__APP__", APP_NAME)
        self._send(200, html.encode(), "text/html")

    def _h_static(self, name: str) -> None:
        path = (STATIC_DIR / name).resolve()
        if path.parent != STATIC_DIR.resolve() or not path.is_file():
            raise NotFoundError("File not found")
        self._send(200, path.read_bytes(), CONTENT_TYPES.get(path.suffix, "application/octet-stream"))

    def _h_status(self) -> dict:
        s, proxy = self.ctx.settings, self.ctx.proxy
        return {"app": APP_NAME, "version": __version__, "tld": s.tld, "ui_port": s.ui_port,
                "proxy_port": proxy.port, "admin": is_admin(), "local_ip": local_ip(),
                "hosts_path": str(s.hosts_path), "panel_name": s.panel_name,
                "panel_url": proxy.url_for(s.panel_name)}

    def _h_list_routes(self) -> dict:
        return self.ctx.routes.list_routes()

    def _h_save_route(self) -> dict:
        return {"ok": True, **self.ctx.routes.save(self._read_json()).to_dict()}

    def _h_delete_route(self, name: str) -> dict:
        return {"ok": True, **self.ctx.routes.delete(name).to_dict()}

    def _h_scan_state(self) -> dict:
        return self.ctx.scanner.snapshot()

    def _h_start_scan(self) -> dict:
        data = self._read_json()
        self.ctx.scanner.start(data.get("start", 1), data.get("end", 10000), bool(data.get("subnet")))
        return {"ok": True}

    # -- helpers -------------------------------------------------------
    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ValidationError("Invalid Content-Length") from None
        if not 0 <= length <= MAX_BODY:
            raise ValidationError("Request too large")
        data = json.loads(self.rfile.read(length) if length else b"{}")
        if not isinstance(data, dict):
            raise ValidationError("Expected a JSON object")
        return data

    def _json(self, obj: Any, status: int = 200) -> None:
        self._send(status, json.dumps(obj).encode(), "application/json")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


class WebServer:
    def __init__(self, ctx: ServerContext):
        handler = type("BoundApiHandler", (ApiHandler,), {"ctx": ctx})
        self._httpd = ThreadingHTTPServer((LOOPBACK, ctx.settings.ui_port), handler)

    def serve_forever(self) -> None:
        self._httpd.serve_forever()

    def close(self) -> None:
        self._httpd.server_close()
