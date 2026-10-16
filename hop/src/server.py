"""HTTP layer: static UI plus JSON API. Business logic lives in the services and scanner layers."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, NamedTuple
from urllib.parse import urlsplit

from .. import APP_NAME, __version__
from .config import LOOPBACK, Settings
from .constants import (
    ApiPath,
    Encoding,
    ErrorMessage,
    FileExt,
    FileName,
    HeaderValue,
    HttpHeader,
    HttpStatus,
    HttpVerb,
    LogMessage,
    MimeType,
    ModelKey,
    NetConstant,
    TemplatePlaceholder,
)
from .errors import HopError, NotFoundError, ValidationError
from .netutil import is_admin, local_ip
from .protocols import (
    PortScannerProtocol,
    ReverseProxyProtocol,
    RouteServiceProtocol,
)

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
STATIC_DIR = WEB_DIR / "static"
MAX_BODY = 64 * 1024
CONTENT_TYPES: dict[str, str] = {
    FileExt.CSS: MimeType.CSS,
    FileExt.JS: MimeType.JAVASCRIPT,
    FileExt.SVG: MimeType.SVG,
}
SECURITY_HEADERS: dict[str, str] = {
    HttpHeader.X_CONTENT_TYPE_OPTIONS: HeaderValue.NOSNIFF,
    HttpHeader.X_FRAME_OPTIONS: HeaderValue.DENY,
    HttpHeader.REFERRER_POLICY: HeaderValue.NO_REFERRER,
    HttpHeader.CACHE_CONTROL: HeaderValue.NO_CACHE,
}


class RouteHandler(NamedTuple):
    verb: HttpVerb
    pattern: re.Pattern
    handler: Callable[[ApiHandler, tuple[str, ...]], Any]


# (method, path regex, handler lambda): direct dispatch without reflection
_ROUTES = (
    RouteHandler(HttpVerb.GET, re.compile(ApiPath.ROOT), lambda h, _: h._h_index()),
    RouteHandler(HttpVerb.GET, re.compile(ApiPath.STATIC_PATTERN), lambda h, args: h._h_static(*args)),
    RouteHandler(HttpVerb.GET, re.compile(ApiPath.STATUS), lambda h, _: h._h_status()),
    RouteHandler(HttpVerb.GET, re.compile(ApiPath.ROUTES), lambda h, _: h._h_list_routes()),
    RouteHandler(HttpVerb.POST, re.compile(ApiPath.ROUTES), lambda h, _: h._h_save_route()),
    RouteHandler(HttpVerb.DELETE, re.compile(ApiPath.ROUTE_ITEM_PATTERN), lambda h, args: h._h_delete_route(*args)),
    RouteHandler(HttpVerb.GET, re.compile(ApiPath.SCAN), lambda h, _: h._h_scan_state()),
    RouteHandler(HttpVerb.POST, re.compile(ApiPath.SCAN), lambda h, _: h._h_start_scan()),
)


@dataclass(frozen=True)
class ServerContext:
    settings: Settings
    routes: RouteServiceProtocol
    scanner: PortScannerProtocol
    proxy: ReverseProxyProtocol

    @property
    def allowed_hosts(self) -> frozenset:
        """DNS-rebinding protection: only these Host/Origin values are accepted."""
        return frozenset({LOOPBACK, NetConstant.LOCALHOST, self.settings.panel_name})


class ApiHandler(BaseHTTPRequestHandler):
    ctx: ServerContext

    def log_message(self, fmt: str, *args: Any) -> None:
        log.debug("%s - %s", self.address_string(), fmt % args)

    do_GET = lambda self: self._dispatch(HttpVerb.GET)        # noqa: E731
    do_POST = lambda self: self._dispatch(HttpVerb.POST)      # noqa: E731
    do_DELETE = lambda self: self._dispatch(HttpVerb.DELETE)  # noqa: E731

    # -- dispatch ------------------------------------------------------
    def _dispatch(self, method: HttpVerb) -> None:
        if not self._allowed():
            return self._json({ModelKey.ERROR: ErrorMessage.FORBIDDEN}, HttpStatus.FORBIDDEN)
        path = urlsplit(self.path).path
        matched = False
        try:
            for route in _ROUTES:
                m = route.pattern.fullmatch(path)
                if not m:
                    continue
                matched = True
                if route.verb == method:
                    body = route.handler(self, m.groups())
                    if body is not None:
                        self._json(body)
                    return
            status = HttpStatus.METHOD_NOT_ALLOWED if matched else HttpStatus.NOT_FOUND
            error_msg = ErrorMessage.METHOD_NOT_ALLOWED if matched else ErrorMessage.NOT_FOUND
            self._json({ModelKey.ERROR: error_msg}, status)
        except HopError as exc:
            self._json({ModelKey.ERROR: str(exc)}, exc.status)
        except json.JSONDecodeError:
            self._json({ModelKey.ERROR: ErrorMessage.INVALID_JSON}, HttpStatus.BAD_REQUEST)
        except Exception:
            log.exception(LogMessage.REQUEST_FAILED, method, path)
            self._json({ModelKey.ERROR: ErrorMessage.SERVER_ERROR}, HttpStatus.INTERNAL_SERVER_ERROR)

    def _allowed(self) -> bool:
        host = (self.headers.get(HttpHeader.HOST) or "").rsplit(":", 1)[0].lower()
        origin = self.headers.get(HttpHeader.ORIGIN)
        allowed = self.ctx.allowed_hosts
        return host in allowed and (not origin or (urlsplit(origin).hostname or "") in allowed)

    # -- handlers ------------------------------------------------------
    def _h_index(self) -> None:
        html = (WEB_DIR / FileName.INDEX_HTML).read_text(encoding=Encoding.UTF8).replace(TemplatePlaceholder.APP_NAME, APP_NAME)
        self._send(HttpStatus.OK, html.encode(Encoding.UTF8), MimeType.HTML)

    def _h_static(self, name: str) -> None:
        path = (STATIC_DIR / name).resolve()
        if path.parent != STATIC_DIR.resolve() or not path.is_file():
            raise NotFoundError(ErrorMessage.FILE_NOT_FOUND)
        self._send(HttpStatus.OK, path.read_bytes(), CONTENT_TYPES.get(path.suffix, MimeType.OCTET_STREAM))

    def _h_status(self) -> dict:
        s, proxy = self.ctx.settings, self.ctx.proxy
        return {
            ModelKey.APP: APP_NAME,
            ModelKey.VERSION: __version__,
            ModelKey.TLD: s.tld,
            ModelKey.UI_PORT: s.ui_port,
            ModelKey.PROXY_PORT: proxy.port,
            ModelKey.ADMIN: is_admin(),
            ModelKey.LOCAL_IP: local_ip(),
            ModelKey.HOSTS_PATH: str(s.hosts_path),
            ModelKey.PANEL_NAME: s.panel_name,
            ModelKey.PANEL_URL: proxy.url_for(s.panel_name),
        }

    def _h_list_routes(self) -> dict:
        return self.ctx.routes.list_routes()

    def _h_save_route(self) -> dict:
        return {ModelKey.OK: True, **self.ctx.routes.save(self._read_json()).to_dict()}

    def _h_delete_route(self, name: str) -> dict:
        return {ModelKey.OK: True, **self.ctx.routes.delete(name).to_dict()}

    def _h_scan_state(self) -> dict:
        return self.ctx.scanner.snapshot()

    def _h_start_scan(self) -> dict:
        data = self._read_json()
        self.ctx.scanner.start(data.get(ModelKey.START, 1), data.get(ModelKey.END, 10000), bool(data.get(ModelKey.SUBNET)))
        return {ModelKey.OK: True}

    # -- helpers -------------------------------------------------------
    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get(HttpHeader.CONTENT_LENGTH) or 0)
        except ValueError:
            raise ValidationError(ErrorMessage.INVALID_CONTENT_LENGTH) from None
        if not 0 <= length <= MAX_BODY:
            raise ValidationError(ErrorMessage.REQUEST_TOO_LARGE)
        data = json.loads(self.rfile.read(length) if length else b"{}")
        if not isinstance(data, dict):
            raise ValidationError(ErrorMessage.EXPECTED_JSON_OBJECT)
        return data

    def _json(self, obj: Any, status: int = HttpStatus.OK) -> None:
        self._send(status, json.dumps(obj).encode(Encoding.UTF8), MimeType.JSON)

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header(HttpHeader.CONTENT_TYPE, f"{content_type}; {HeaderValue.CHARSET_UTF8}")
        self.send_header(HttpHeader.CONTENT_LENGTH, str(len(body)))
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
