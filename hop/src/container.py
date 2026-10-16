"""High-performance, lightweight Inversion of Control (IoC) container.

Provides dependency injection with zero reflection overhead (O(1) dictionary lookups),
preserving peak execution performance while enabling inversion of control.
"""
from __future__ import annotations

from typing import Any, Callable, TypeVar, cast

from .. import APP_NAME
from .config import Settings
from .constants import NetConstant
from .hosts import HostsFile
from .models import Route
from .protocols import (
    HostsManagerProtocol,
    PortScannerProtocol,
    ReverseProxyProtocol,
    RouteRegistryProtocol,
    RouteServiceProtocol,
    WebServerProtocol,
)
from .proxy import ReverseProxy
from .registry import RouteRegistry
from .scanner import PortScanner
from .server import ServerContext, WebServer
from .services import RouteService

T = TypeVar("T")


class ContainerError(Exception):
    """Raised when dependency resolution fails."""


class Container:
    """Zero-reflection, dictionary-backed Inversion of Control (IoC) container."""

    def __init__(self) -> None:
        self._instances: dict[Any, Any] = {}
        self._singletons: dict[Any, Callable[[Container], Any]] = {}
        self._factories: dict[Any, Callable[[Container], Any]] = {}

    def register_instance(self, key: Any, instance: T) -> Container:
        """Register an existing object as an instance."""
        self._instances[key] = instance
        return self

    def register_singleton(self, key: Any, factory: Callable[[Container], T]) -> Container:
        """Register a factory whose result is cached on first resolution."""
        self._singletons[key] = factory
        return self

    def register_factory(self, key: Any, factory: Callable[[Container], T]) -> Container:
        """Register a transient factory evaluated on every resolution."""
        self._factories[key] = factory
        return self

    def alias(self, alias_key: Any, target_key: Any) -> Container:
        """Alias an interface or class token to another token."""
        self._factories[alias_key] = lambda c: c.resolve(target_key)
        return self

    def resolve(self, key: type[T] | Any) -> T:
        """Resolve a dependency by type, protocol, or key in O(1) time."""
        # 1. Direct instance / cached singleton
        if key in self._instances:
            return cast(T, self._instances[key])

        # 2. Lazy singleton factory
        if key in self._singletons:
            instance = self._singletons[key](self)
            self._instances[key] = instance
            return cast(T, instance)

        # 3. Transient factory / alias
        if key in self._factories:
            return cast(T, self._factories[key](self))

        raise ContainerError(f"No registration found for: {key!r}")

    def __contains__(self, key: Any) -> bool:
        return key in self._instances or key in self._singletons or key in self._factories


def create_container(settings: Settings) -> Container:
    """Assemble the application's default dependency injection graph."""
    container = Container()

    # Configuration
    container.register_instance(Settings, settings)

    # Route Registry (persisted routes + builtin panel)
    def _create_registry(c: Container) -> RouteRegistry:
        s = c.resolve(Settings)
        panel = Route(s.panel_name, NetConstant.LOOPBACK, s.ui_port, builtin=True)
        return RouteRegistry(s.routes_file, builtin=[panel])

    container.register_singleton(RouteRegistryProtocol, _create_registry)
    container.alias(RouteRegistry, RouteRegistryProtocol)

    # Hosts File Manager
    def _create_hosts(c: Container) -> HostsFile:
        s = c.resolve(Settings)
        return HostsFile(s.hosts_path, s.hosts_marker)

    container.register_singleton(HostsManagerProtocol, _create_hosts)
    container.alias(HostsFile, HostsManagerProtocol)

    # Route Service
    def _create_route_service(c: Container) -> RouteService:
        return RouteService(
            settings=c.resolve(Settings),
            registry=c.resolve(RouteRegistryProtocol),
            hosts=c.resolve(HostsManagerProtocol),
        )

    container.register_singleton(RouteServiceProtocol, _create_route_service)
    container.alias(RouteService, RouteServiceProtocol)

    # Reverse Proxy
    def _create_proxy(c: Container) -> ReverseProxy:
        s = c.resolve(Settings)
        direct_url = f"{NetConstant.HTTP_SCHEME}{NetConstant.LOOPBACK}:{s.ui_port}"
        return ReverseProxy(c.resolve(RouteRegistryProtocol), fallback_url=direct_url)

    container.register_singleton(ReverseProxyProtocol, _create_proxy)
    container.alias(ReverseProxy, ReverseProxyProtocol)

    # Port Scanner
    def _create_scanner(c: Container) -> PortScanner:
        s = c.resolve(Settings)
        proxy = c.resolve(ReverseProxyProtocol)
        return PortScanner(
            own_ports=lambda: {s.ui_port, proxy.port},
            user_agent=APP_NAME,
        )

    container.register_singleton(PortScannerProtocol, _create_scanner)
    container.alias(PortScanner, PortScannerProtocol)

    # Server Context
    def _create_server_context(c: Container) -> ServerContext:
        return ServerContext(
            settings=c.resolve(Settings),
            routes=c.resolve(RouteServiceProtocol),
            scanner=c.resolve(PortScannerProtocol),
            proxy=c.resolve(ReverseProxyProtocol),
        )

    container.register_singleton(ServerContext, _create_server_context)

    # Web Server
    def _create_web_server(c: Container) -> WebServer:
        return WebServer(c.resolve(ServerContext))

    container.register_singleton(WebServerProtocol, _create_web_server)
    container.alias(WebServer, WebServerProtocol)

    return container
