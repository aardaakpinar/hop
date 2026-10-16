"""Route registry: a thread-safe JSON store written atomically."""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Iterable

from .constants import Encoding, FileExt, LogMessage, MessageTemplate
from .errors import ConflictError, HopError
from .models import Route

log = logging.getLogger(__name__)


class RouteRegistry:
    """User routes are persisted to disk; `builtin` routes (the panel) live in memory only."""

    def __init__(self, path: Path, builtin: Iterable[Route] = ()):
        self._path = Path(path)
        self._lock = threading.RLock()
        self._builtin = {r.name: r for r in builtin}
        self._user: dict[str, Route] = {}
        self._load()

    # -- read ----------------------------------------------------------
    def get(self, name: str) -> Route | None:
        with self._lock:
            return self._builtin.get(name) or self._user.get(name)

    def all(self) -> list[Route]:
        with self._lock:
            return [*self._builtin.values(), *sorted(self._user.values(), key=lambda r: r.name)]

    def names(self) -> list[str]:
        return [r.name for r in self.all()]

    # -- write ---------------------------------------------------------
    def upsert(self, route: Route) -> None:
        with self._lock:
            if route.name in self._builtin:
                raise ConflictError(MessageTemplate.reserved_by_system(route.name))
            self._user[route.name] = route
            self._save()

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._builtin:
                raise ConflictError(MessageTemplate.cannot_be_deleted(name))
            removed = self._user.pop(name, None) is not None
            if removed:
                self._save()
            return removed

    # -- persistence ---------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text(encoding=Encoding.UTF8))
            self._user = {n: Route.from_dict(n, d) for n, d in data.items() if n not in self._builtin}
        except (OSError, ValueError, TypeError, AttributeError, HopError) as exc:
            log.debug(LogMessage.COULD_NOT_READ_ROUTES, self._path, exc)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(FileExt.TMP)
        payload = {r.name: r.to_dict() for r in self._user.values()}
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding=Encoding.UTF8)
        os.replace(tmp, self._path)
