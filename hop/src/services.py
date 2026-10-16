"""Application services: keep the route registry and the hosts file consistent."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Mapping

from .config import Settings
from .hosts import HostsFile, SyncResult
from .models import Route, normalize_name, validate_host, validate_port
from .netutil import port_is_open
from .registry import RouteRegistry


class RouteService:
    def __init__(self, settings: Settings, registry: RouteRegistry, hosts: HostsFile):
        self._settings = settings
        self._registry = registry
        self._hosts = hosts

    def list_routes(self) -> dict[str, dict]:
        """All routes, plus whether each target is currently accepting connections."""
        routes = self._registry.all()
        with ThreadPoolExecutor(max_workers=16) as pool:
            alive = list(pool.map(lambda r: port_is_open(r.host, r.port), routes))
        return {r.name: {**r.to_dict(), "builtin": r.builtin, "up": up} for r, up in zip(routes, alive)}

    def save(self, payload: Mapping[str, Any]) -> SyncResult:
        route = Route(name=normalize_name(payload.get("name"), self._settings.tld),
                      host=validate_host(payload.get("host")),
                      port=validate_port(payload.get("port")),
                      rewrite_host=bool(payload.get("rewrite_host")))
        self._registry.upsert(route)
        return self.sync_hosts()

    def delete(self, name: str) -> SyncResult:
        self._registry.remove(name)
        return self.sync_hosts()

    def sync_hosts(self) -> SyncResult:
        return self._hosts.sync(self._registry.names())
