"""Composition root: builds the components, wires them together and manages the lifecycle."""
from __future__ import annotations

import logging
import threading
import webbrowser

from .. import APP_NAME, __version__
from .config import LOOPBACK, Settings
from .hosts import HostsFile, SyncResult
from .models import Route
from .proxy import ReverseProxy
from .registry import RouteRegistry
from .scanner import PortScanner
from .server import ServerContext, WebServer
from .services import RouteService

log = logging.getLogger(__name__)


class Application:
    def __init__(self, settings: Settings):
        self.settings = settings
        panel = Route(settings.panel_name, LOOPBACK, settings.ui_port, builtin=True)
        self.registry = RouteRegistry(settings.routes_file, builtin=[panel])
        self.hosts = HostsFile(settings.hosts_path, settings.hosts_marker)
        self.routes = RouteService(settings, self.registry, self.hosts)
        self.proxy = ReverseProxy(self.registry, fallback_url=self.direct_url)
        self.scanner = PortScanner(own_ports=lambda: {settings.ui_port, self.proxy.port}, user_agent=APP_NAME)

    @property
    def direct_url(self) -> str:
        return f"http://{LOOPBACK}:{self.settings.ui_port}"

    def run(self) -> int:
        try:
            server = WebServer(ServerContext(self.settings, self.routes, self.scanner, self.proxy))
        except OSError as exc:
            log.error("Panel port (%s) is unavailable: %s", self.settings.ui_port, exc)
            return 1
        self.proxy.start(self.settings.proxy_candidates)
        sync = self.routes.sync_hosts()          # the panel name is part of this block too
        entry_url = self._report(sync)
        if self.settings.open_browser:
            threading.Timer(0.6, webbrowser.open, args=(entry_url,)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("Shutting down...")
        finally:
            server.close()
            self.proxy.stop()
        return 0

    def _report(self, sync: SyncResult) -> str:
        pretty = self.proxy.url_for(self.settings.panel_name) if self.proxy.port else None
        entry = pretty if (pretty and sync.ok) else self.direct_url
        log.info("%s %s", APP_NAME, __version__)
        log.info("Panel : %s", entry)
        if entry != self.direct_url:
            log.info("Direct: %s", self.direct_url)
        if not sync.ok:
            log.warning("%s", sync.message)
            for line in sync.lines:
                log.warning("  add to hosts: %s", line)
        if self.proxy.port not in (None, 80):
            log.warning("Proxy is listening on port %s, so append :%s to the route addresses.",
                        self.proxy.port, self.proxy.port)
        return entry
