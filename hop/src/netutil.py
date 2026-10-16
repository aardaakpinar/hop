"""Platform-independent system helpers."""
from __future__ import annotations

import os
import socket

from .constants import NetConstant, OsPlatform


def is_admin() -> bool:
    try:
        if os.name == OsPlatform.NT:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def local_ip() -> str | None:
    """Local IP of the default route (no packet is actually sent)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((NetConstant.PROBE_TARGET_IP, 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def port_is_open(host: str, port: int, timeout: float = 0.3) -> bool:
    with socket.socket() as sock:
        sock.settimeout(timeout)
        try:
            return sock.connect_ex((host, port)) == 0
        except OSError:
            return False
