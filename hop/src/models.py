"""Domain models and input validation."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .config import LOOPBACK
from .constants import ErrorMessage, ModelKey, NetConstant, ScanKind
from .errors import ValidationError

_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")
_HOST_RE = re.compile(r"^[A-Za-z0-9._:-]{1,253}$")
RESERVED_NAMES = frozenset({NetConstant.LOCALHOST})


def normalize_name(raw: Any, tld: str) -> str:
    """'cti' -> 'cti.hop'; names that already contain a dot are kept as they are."""
    name = str(raw or "").strip().lower()
    if name and "." not in name:
        name = f"{name}.{tld}"
    if len(name) > 253 or not _NAME_RE.fullmatch(name) or name in RESERVED_NAMES:
        raise ValidationError(ErrorMessage.INVALID_NAME)
    return name


def validate_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise ValidationError(ErrorMessage.PORT_NOT_NUMBER) from None
    if not 1 <= port <= 65535:
        raise ValidationError(ErrorMessage.PORT_OUT_OF_BOUNDS)
    return port


def validate_host(value: Any) -> str:
    host = str(value or LOOPBACK).strip()
    if not _HOST_RE.fullmatch(host):
        raise ValidationError(ErrorMessage.INVALID_TARGET_ADDRESS)
    return host


def validate_range(start: Any, end: Any) -> tuple[int, int]:
    first, last = validate_port(start), validate_port(end)
    if first > last:
        raise ValidationError(ErrorMessage.START_PORT_GREATER)
    return first, last


@dataclass(frozen=True)
class Route:
    name: str
    host: str = LOOPBACK
    port: int = 0
    rewrite_host: bool = False
    builtin: bool = False           # the panel's own route: cannot be edited or deleted

    @property
    def target(self) -> str:
        return f"{self.host}:{self.port}"

    @classmethod
    def from_dict(cls, name: str, data: Mapping[str, Any]) -> "Route":
        return cls(
            name=name,
            host=validate_host(data.get(ModelKey.HOST)),
            port=validate_port(data.get(ModelKey.PORT)),
            rewrite_host=bool(data.get(ModelKey.REWRITE_HOST)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            ModelKey.HOST: self.host,
            ModelKey.PORT: self.port,
            ModelKey.REWRITE_HOST: self.rewrite_host,
        }


@dataclass
class ScanResult:
    host: str
    port: int
    kind: str = ScanKind.TCP               # ScanKind.HTTP | ScanKind.TCP
    title: str = ""
    server: str = ""
    status: str = ""
    is_self: bool = False
