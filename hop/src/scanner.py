"""Port scanning: TCP connect plus a lightweight HTTP probe."""
from __future__ import annotations

import concurrent.futures as cf
import ipaddress
import logging
import re
import socket
import threading
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .config import COMMON_PORTS, LOOPBACK
from .errors import ConflictError
from .models import ScanResult, validate_range
from .netutil import local_ip

log = logging.getLogger(__name__)
_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
_SERVER_RE = re.compile(rb"\r\nServer:\s*([^\r\n]+)", re.I)


@dataclass(frozen=True)
class _Job:
    host: str
    port: int
    timeout: float


def probe(host: str, port: int, timeout: float = 0.5, user_agent: str = "Hop") -> ScanResult | None:
    """Return a `ScanResult` with service details if the port is open, otherwise None."""
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        if sock.connect_ex((host, port)) != 0:
            return None
        result = ScanResult(host=host, port=port)
        _identify(sock, result, user_agent)
        return result
    except OSError:
        return None
    finally:
        sock.close()


def _identify(sock: socket.socket, result: ScanResult, user_agent: str) -> None:
    data = b""
    try:
        sock.settimeout(1.0)
        sock.sendall(f"GET / HTTP/1.0\r\nHost: {result.host}:{result.port}\r\n"
                     f"User-Agent: {user_agent}\r\n\r\n".encode())
        while len(data) < 16384:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass
    if data.startswith(b"HTTP/"):
        result.kind = "http"
        result.status = data.split(b"\r\n", 1)[0].decode("latin-1")[9:]
        if m := _SERVER_RE.search(data):
            result.server = m.group(1).decode("latin-1")[:60]
        if m := _TITLE_RE.search(data):
            result.title = re.sub(r"\s+", " ", m.group(1).decode("utf-8", "replace")).strip()[:80]
    elif data:
        result.server = re.sub(r"[^\x20-\x7e]", "", data[:40].decode("latin-1"))


class PortScanner:
    """Runs one background scan at a time; read its state with `snapshot()`."""

    MAX_WORKERS = 400

    def __init__(self, own_ports: Callable[[], set], user_agent: str = "Hop"):
        self._own_ports = own_ports
        self._user_agent = user_agent
        self._lock = threading.Lock()
        self._running = False
        self._done = 0
        self._total = 0
        self._results: list[ScanResult] = []

    def start(self, start: Any, end: Any, subnet: bool = False) -> None:
        first, last = validate_range(start, end)
        with self._lock:
            if self._running:
                raise ConflictError("A scan is already running")
            self._running, self._done, self._total, self._results = True, 0, 0, []
        jobs = self._build_jobs(first, last, subnet)
        with self._lock:
            self._total = len(jobs)
        threading.Thread(target=self._run, args=(jobs,), name="scanner", daemon=True).start()

    def snapshot(self) -> dict:
        with self._lock:
            return {"running": self._running, "done": self._done, "total": self._total,
                    "results": [asdict(r) for r in self._results]}

    @staticmethod
    def _build_jobs(first: int, last: int, subnet: bool) -> list[_Job]:
        jobs = [_Job(LOOPBACK, port, 0.5) for port in range(first, last + 1)]
        ip = local_ip() if subnet else None
        if ip:
            for host in ipaddress.ip_network(f"{ip}/24", strict=False).hosts():
                if str(host) != ip:
                    jobs += [_Job(str(host), port, 0.4) for port in COMMON_PORTS]
        return jobs

    def _run(self, jobs: list[_Job]) -> None:
        own = self._own_ports()

        def work(job: _Job) -> None:
            result = probe(job.host, job.port, job.timeout, self._user_agent)
            with self._lock:
                self._done += 1
                if result:
                    result.is_self = result.host == LOOPBACK and result.port in own
                    self._results.append(result)

        try:
            with cf.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as pool:
                list(pool.map(work, jobs))
        except Exception:
            log.exception("Scan stopped unexpectedly")
        finally:
            with self._lock:
                self._results.sort(key=lambda r: (r.host != LOOPBACK, r.host, r.port))
                self._running = False
