"""Reverse proxy that routes requests by Host header.

Works over raw TCP: the head of the first request is read to pick a target, then bytes are
piped in both directions. Because of this, WebSocket and HMR traffic pass through without
any extra handling.
"""
from __future__ import annotations

import logging
import os
import re
import socket
import threading
from html import escape
from typing import Sequence

from .config import LOOPBACK
from .constants import (
    Encoding,
    ErrorMessage,
    FileName,
    HeaderValue,
    HttpStatusPhrase,
    LogMessage,
    MessageTemplate,
    MimeType,
    NetConstant,
    OsPlatform,
    ThreadName,
)
from .protocols import RouteRegistryProtocol

log = logging.getLogger(__name__)

HEADER_LIMIT = 64 * 1024
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 15
_HOST_RE = re.compile(rb"(\r\nHost:)[ \t]*([^\r\n]+)", re.I)


class ReverseProxy:
    def __init__(self, registry: RouteRegistryProtocol, fallback_url: str):
        self._registry = registry
        self._fallback_url = fallback_url
        self._sock: socket.socket | None = None
        self._port: int | None = None

    @property
    def port(self) -> int | None:
        return self._port

    def url_for(self, name: str) -> str:
        suffix = "" if self._port in (None, 80) else f":{self._port}"
        return f"{NetConstant.HTTP_SCHEME}{name}{suffix}"

    def start(self, candidates: Sequence[int]) -> int | None:
        """Bind to the first port that works; return None if none of them do."""
        for port in candidates:
            sock = socket.socket()
            try:
                if os.name != OsPlatform.NT:                 # on Windows, SO_REUSEADDR would allow stealing a used port
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((LOOPBACK, port))
                sock.listen(128)
            except OSError:
                sock.close()
                continue
            self._sock, self._port = sock, sock.getsockname()[1]
            threading.Thread(target=self._accept_loop, args=(sock,), name=ThreadName.PROXY, daemon=True).start()
            return self._port
        log.error(LogMessage.PROXY_START_ERROR, ", ".join(map(str, candidates)))
        return None

    def stop(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None

    # -- connection handling -------------------------------------------
    def _accept_loop(self, sock: socket.socket) -> None:
        while True:
            try:
                client, _ = sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(client,), daemon=True).start()

    def _handle(self, client: socket.socket) -> None:
        upstream = None
        try:
            client.settimeout(READ_TIMEOUT)
            head = self._read_head(client)
            if head is None:
                return
            host = self._extract_host(head)
            route = self._registry.get(host)
            if route is None:
                client.sendall(self._page(
                    HttpStatusPhrase.NOT_FOUND,
                    ErrorMessage.ROUTE_NOT_FOUND,
                    MessageTemplate.no_route_configured(host),
                ))
                return
            try:
                upstream = socket.create_connection((route.host, route.port), timeout=CONNECT_TIMEOUT)
            except OSError:
                client.sendall(self._page(
                    HttpStatusPhrase.BAD_GATEWAY,
                    ErrorMessage.TARGET_DOWN,
                    MessageTemplate.target_not_responding(host, route.target),
                ))
                return
            if route.rewrite_host:
                target = route.target.encode()
                head = _HOST_RE.sub(lambda m: m.group(1) + b" " + target, head, count=1)
            upstream.sendall(head)
            client.settimeout(None)
            upstream.settimeout(None)
            back = threading.Thread(target=self._pipe, args=(upstream, client), daemon=True)
            back.start()
            self._pipe(client, upstream)
            back.join(timeout=5)
        except OSError as exc:
            log.debug(LogMessage.PROXY_CONNECTION_CLOSED, exc)
        finally:
            for s in (client, upstream):
                if s:
                    try:
                        s.close()
                    except OSError:
                        pass

    @staticmethod
    def _read_head(client: socket.socket) -> bytes | None:
        data = b""
        while b"\r\n\r\n" not in data and len(data) < HEADER_LIMIT:
            chunk = client.recv(8192)
            if not chunk:
                return None
            data += chunk
        return data

    @staticmethod
    def _extract_host(head: bytes) -> str:
        m = _HOST_RE.search(head)
        host = m.group(2).decode(Encoding.LATIN1).strip().lower() if m else ""
        return host.rsplit(":", 1)[0] if ":" in host else host

    @staticmethod
    def _pipe(src: socket.socket, dst: socket.socket) -> None:
        try:
            while chunk := src.recv(65536):
                dst.sendall(chunk)
        except OSError:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    def _page(self, status: str, title: str, message: str) -> bytes:
        body = (
            f"<!doctype html><meta charset={Encoding.UTF8}><title>{escape(title)}</title>"
            f'<link rel="icon" href="{escape(self._fallback_url)}/static/{FileName.LOGO_SVG}" type="{MimeType.SVG}" />'
            "<body style='font-family:system-ui,sans-serif;background:#0f1115;color:#e9ecf3;padding:48px'>"
            f"<h2>{escape(title)}</h2><p>{escape(message)}</p>"
        ).encode(Encoding.UTF8)
        head = (
            f"HTTP/1.1 {status}\r\nContent-Type: {MimeType.HTML}; charset={Encoding.UTF8}\r\n"
            f"Content-Length: {len(body)}\r\nConnection: {HeaderValue.CLOSE}\r\n\r\n"
        ).encode(Encoding.UTF8)
        return head + body
