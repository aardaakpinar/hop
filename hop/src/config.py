"""Settings and constants."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .. import APP_NAME

DEFAULT_TLD = "hop"
DEFAULT_UI_PORT = 7777
PROXY_PORT_CANDIDATES = (80, 8080)
LOOPBACK = "127.0.0.1"
COMMON_PORTS = (21, 22, 80, 443, 445, 1433, 3000, 3001, 3100, 3306, 3389, 4200, 5000, 5173,
                5432, 5900, 6379, 8000, 8008, 8080, 8081, 8443, 8888, 9000, 9090, 27017)


def default_hosts_path() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    return Path("/etc/hosts")


@dataclass(frozen=True)
class Settings:
    tld: str = DEFAULT_TLD
    ui_port: int = DEFAULT_UI_PORT
    proxy_port: int = 0                       # 0 = try 80, then 8080
    panel_label: str = APP_NAME.lower()       # the panel is served at <label>.<tld>
    open_browser: bool = True
    config_dir: Path = field(default_factory=lambda: Path.home() / ".hop")
    hosts_path: Path = field(default_factory=default_hosts_path)

    @property
    def routes_file(self) -> Path:
        return self.config_dir / "routes.json"

    @property
    def panel_name(self) -> str:
        return f"{self.panel_label}.{self.tld}"

    @property
    def hosts_marker(self) -> str:
        return APP_NAME.lower()

    @property
    def proxy_candidates(self) -> tuple[int, ...]:
        return (self.proxy_port,) if self.proxy_port else PROXY_PORT_CANDIDATES
