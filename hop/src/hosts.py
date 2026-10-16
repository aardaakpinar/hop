"""Hosts file management: only ever touches Hop's own marked block."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ADDRESS = "127.0.0.1"
LOCALHOST_SUFFIX = ".localhost"      # browsers resolve these themselves, no hosts entry needed


@dataclass(frozen=True)
class SyncResult:
    ok: bool
    message: str
    lines: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"hosts_ok": self.ok, "message": self.message, "lines": list(self.lines)}


def _markers(name: str) -> tuple[str, str]:
    return f"# >>> {name} >>>", f"# <<< {name} <<<"


def _block_re(name: str) -> re.Pattern:
    begin, end = _markers(name)
    return re.compile(re.escape(begin) + r"(.*?)" + re.escape(end) + r"[ \t]*\n?", re.S)


class HostsFile:
    def __init__(self, path: Path, marker: str):
        self._path = Path(path)
        self._marker = marker
        self._block = _block_re(marker)

    def managed_names(self, text: str) -> list[str]:
        match = self._block.search(text)
        if not match:
            return []
        parts = (line.split() for line in match.group(1).splitlines())
        return sorted(p[1] for p in parts if len(p) >= 2)

    def render(self, text: str, names: list[str]) -> str:
        """Strip the existing block, then append the up-to-date one at the end (pure function)."""
        text = self._block.sub("", text)
        text = text.rstrip() + "\n"
        if names:
            begin, end = _markers(self._marker)
            block = [begin, *(f"{ADDRESS} {n}" for n in names), end]
            text += "\n" + "\n".join(block) + "\n"
        return text

    def sync(self, names: Iterable[str]) -> SyncResult:
        wanted = sorted({n for n in names if not n.endswith(LOCALHOST_SUFFIX)})
        lines = tuple(f"{ADDRESS} {n}" for n in wanted)
        try:
            text = self._path.read_text(encoding="utf-8", errors="surrogateescape")
            if self.managed_names(text) == wanted:
                return SyncResult(True, "hosts file is already up to date", lines)
            self._path.write_text(self.render(text, wanted), encoding="utf-8", errors="surrogateescape")
            return SyncResult(True, "hosts file updated", lines)
        except PermissionError:
            return SyncResult(False, f"Could not write the hosts file (administrator/root required): {self._path}", lines)
        except OSError as exc:
            return SyncResult(False, f"hosts file error: {exc}", lines)
