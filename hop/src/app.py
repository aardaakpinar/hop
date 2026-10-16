"""Composition root: builds the components, wires them together and manages the lifecycle."""
from __future__ import annotations

import logging
import threading
import webbrowser

from .. import APP_NAME, __version__
from .config import LOOPBACK, Settings
from .constants import LogMessage, NetConstant
from .container import Container, create_container
from .hosts import SyncResult
from .protocols import (
    HostsManagerProtocol,
    PortScannerProtocol,
    ReverseProxyProtocol,
    RouteRegistryProtocol,
    RouteServiceProtocol,
    WebServerProtocol,
)

log = logging.getLogger(__name__)


class Application:
    """Application lifecycle manager using Inversion of Control (IoC)."""

    def __init__(self, target: Settings | Container):
        if isinstance(target, Container):
            self.container = target
            self.settings = self.container.resolve(Settings)
        else:
            self.settings = target
            self.container = create_container(self.settings)

        self.registry: RouteRegistryProtocol = self.container.resolve(RouteRegistryProtocol)
        self.hosts: HostsManagerProtocol = self.container.resolve(HostsManagerProtocol)
        self.routes: RouteServiceProtocol = self.container.resolve(RouteServiceProtocol)
        self.proxy: ReverseProxyProtocol = self.container.resolve(ReverseProxyProtocol)
        self.scanner: PortScannerProtocol = self.container.resolve(PortScannerProtocol)

    @property
    def direct_url(self) -> str:
        return f"{NetConstant.HTTP_SCHEME}{LOOPBACK}:{self.settings.ui_port}"

    def run(self) -> int:
        try:
            server: WebServerProtocol = self.container.resolve(WebServerProtocol)
        except OSError as exc:
            log.error(LogMessage.PANEL_PORT_UNAVAILABLE, self.settings.ui_port, exc)
            return 1

        self.proxy.start(self.settings.proxy_candidates)
        sync = self.routes.sync_hosts()          # the panel name is part of this block too
        entry_url = self._report(sync)
        if self.settings.open_browser:
            threading.Timer(0.6, webbrowser.open, args=(entry_url,)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info(LogMessage.SHUTTING_DOWN)
        finally:
            server.close()
            self.proxy.stop()
        return 0

    def _report(self, sync: SyncResult) -> str:
        pretty = self.proxy.url_for(self.settings.panel_name) if self.proxy.port else None
        entry = pretty if (pretty and sync.ok) else self.direct_url
        log.info(LogMessage.APP_VERSION_INFO, APP_NAME, __version__)
        log.info(LogMessage.PANEL_URL_INFO, entry)
        if entry != self.direct_url:
            log.info(LogMessage.DIRECT_URL_INFO, self.direct_url)
        if not sync.ok:
            log.warning(LogMessage.SYNC_WARNING, sync.message)
            for line in sync.lines:
                log.warning(LogMessage.ADD_TO_HOSTS, line)
        if self.proxy.port not in (None, 80):
            log.warning(LogMessage.PROXY_PORT_WARNING, self.proxy.port, self.proxy.port)
        return entry
