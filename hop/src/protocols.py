"""Abstract protocols for Inversion of Control (IoC).

Defines clean behavioral contracts using typing.Protocol with zero runtime overhead.
Allows loose coupling, trivial test mocking, and flexible dependency injection.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Protocol, Sequence, runtime_checkable

from .hosts import SyncResult
from .models import Route


@runtime_checkable
class RouteRegistryProtocol(Protocol):
    """Protocol for reading and persisting route definitions."""

    def get(self, name: str) -> Route | None:
        ...

    def all(self) -> list[Route]:
        ...

    def names(self) -> list[str]:
        ...

    def upsert(self, route: Route) -> None:
        ...

    def remove(self, name: str) -> bool:
        ...


@runtime_checkable
class HostsManagerProtocol(Protocol):
    """Protocol for managing the operating system's hosts file."""

    def managed_names(self, text: str) -> list[str]:
        ...

    def render(self, text: str, names: list[str]) -> str:
        ...

    def sync(self, names: Iterable[str]) -> SyncResult:
        ...


@runtime_checkable
class RouteServiceProtocol(Protocol):
    """Protocol for coordinating routes and hosts synchronization."""

    def list_routes(self) -> dict[str, dict]:
        ...

    def save(self, payload: Mapping[str, Any]) -> SyncResult:
        ...

    def delete(self, name: str) -> SyncResult:
        ...

    def sync_hosts(self) -> SyncResult:
        ...


@runtime_checkable
class ReverseProxyProtocol(Protocol):
    """Protocol for the reverse proxy server."""

    @property
    def port(self) -> int | None:
        ...

    def url_for(self, name: str) -> str:
        ...

    def start(self, candidates: Sequence[int]) -> int | None:
        ...

    def stop(self) -> None:
        ...


@runtime_checkable
class PortScannerProtocol(Protocol):
    """Protocol for background port scanning."""

    def start(self, start: Any, end: Any, subnet: bool = False) -> None:
        ...

    def snapshot(self) -> dict:
        ...


@runtime_checkable
class WebServerProtocol(Protocol):
    """Protocol for the main web and API server."""

    def serve_forever(self) -> None:
        ...

    def close(self) -> None:
        ...
