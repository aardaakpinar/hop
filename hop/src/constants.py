"""Strongly-typed constants, enums, and message templates.

Centralizes all string literals across the application to prevent hardcoded magic strings,
enable IDE autocompletion, prevent typos, and maintain strict consistency.
"""
from __future__ import annotations

import sys
from enum import Enum
from typing import Any

# Compatible StrEnum for Python 3.9+
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    class StrEnum(str, Enum):
        """String enum for Python < 3.11."""
        def __str__(self) -> str:
            return str(self.value)


class HttpVerb(StrEnum):
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HttpStatus(int, Enum):
    OK = 200
    BAD_REQUEST = 400
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502


class HttpStatusPhrase(StrEnum):
    OK = "200 OK"
    BAD_REQUEST = "400 Bad Request"
    FORBIDDEN = "403 Forbidden"
    NOT_FOUND = "404 Not Found"
    METHOD_NOT_ALLOWED = "405 Method Not Allowed"
    CONFLICT = "409 Conflict"
    INTERNAL_SERVER_ERROR = "500 Internal Server Error"
    BAD_GATEWAY = "502 Bad Gateway"


class HttpHeader(StrEnum):
    HOST = "Host"
    ORIGIN = "Origin"
    CONTENT_LENGTH = "Content-Length"
    CONTENT_TYPE = "Content-Type"
    CONNECTION = "Connection"
    USER_AGENT = "User-Agent"
    X_CONTENT_TYPE_OPTIONS = "X-Content-Type-Options"
    X_FRAME_OPTIONS = "X-Frame-Options"
    REFERRER_POLICY = "Referrer-Policy"
    CACHE_CONTROL = "Cache-Control"


class HeaderValue(StrEnum):
    NOSNIFF = "nosniff"
    DENY = "DENY"
    NO_REFERRER = "no-referrer"
    NO_CACHE = "no-cache"
    CLOSE = "close"
    CHARSET_UTF8 = "charset=utf-8"


class MimeType(StrEnum):
    HTML = "text/html"
    JSON = "application/json"
    CSS = "text/css"
    JAVASCRIPT = "application/javascript"
    SVG = "image/svg+xml"
    OCTET_STREAM = "application/octet-stream"


class Encoding(StrEnum):
    UTF8 = "utf-8"
    LATIN1 = "latin-1"
    REPLACE = "replace"
    SURROGATEESCAPE = "surrogateescape"


class ModelKey(StrEnum):
    HOST = "host"
    PORT = "port"
    REWRITE_HOST = "rewrite_host"
    BUILTIN = "builtin"
    NAME = "name"
    UP = "up"
    OK = "ok"
    ERROR = "error"
    MESSAGE = "message"
    LINES = "lines"
    HOSTS_OK = "hosts_ok"
    RUNNING = "running"
    DONE = "done"
    TOTAL = "total"
    RESULTS = "results"
    START = "start"
    END = "end"
    SUBNET = "subnet"
    APP = "app"
    VERSION = "version"
    TLD = "tld"
    UI_PORT = "ui_port"
    PROXY_PORT = "proxy_port"
    ADMIN = "admin"
    LOCAL_IP = "local_ip"
    HOSTS_PATH = "hosts_path"
    PANEL_NAME = "panel_name"
    PANEL_URL = "panel_url"
    KIND = "kind"
    TITLE = "title"
    SERVER = "server"
    STATUS = "status"
    IS_SELF = "is_self"


class ScanKind(StrEnum):
    TCP = "tcp"
    HTTP = "http"


class ApiPath(StrEnum):
    ROOT = "/"
    STATIC_PATTERN = r"/static/([\w.-]+)"
    STATUS = "/api/status"
    ROUTES = "/api/routes"
    ROUTE_ITEM_PATTERN = r"/api/routes/([a-z0-9.-]+)"
    SCAN = "/api/scan"


class FileExt(StrEnum):
    JSON = ".json"
    TMP = ".tmp"
    CSS = ".css"
    JS = ".js"
    SVG = ".svg"
    HTML = ".html"


class FileName(StrEnum):
    INDEX_HTML = "index.html"
    ROUTES_JSON = "routes.json"
    LOGO_SVG = "logo.svg"
    APP_CSS = "app.css"
    HOSTS = "hosts"


class NetConstant(StrEnum):
    LOOPBACK = "127.0.0.1"
    LOCALHOST = "localhost"
    LOCALHOST_SUFFIX = ".localhost"
    HTTP_SCHEME = "http://"
    HTTPS_SCHEME = "https://"
    ALL_INTERFACES = "0.0.0.0"
    PROBE_TARGET_IP = "8.8.8.8"
    CIDR_24 = "/24"


class OsPlatform(StrEnum):
    NT = "nt"
    POSIX = "posix"


class WindowsSystemPath(StrEnum):
    SYSTEM_ROOT_ENV = "SystemRoot"
    DEFAULT_SYSTEM_ROOT = r"C:\Windows"
    SYSTEM32 = "System32"
    DRIVERS = "drivers"
    ETC = "etc"
    HOSTS = "hosts"


class PosixSystemPath(StrEnum):
    HOSTS_PATH = "/etc/hosts"


class DefaultConfig:
    DEFAULT_TLD = "hop"
    DEFAULT_UI_PORT = 7777
    PROXY_PORT_CANDIDATES = (80, 8080)


class ErrorMessage(StrEnum):
    INVALID_NAME = "Invalid name. Example: cti"
    PORT_NOT_NUMBER = "Port must be a number"
    PORT_OUT_OF_BOUNDS = "Port must be between 1 and 65535"
    INVALID_TARGET_ADDRESS = "Invalid target address"
    START_PORT_GREATER = "Start port cannot be greater than end port"
    FORBIDDEN = "forbidden"
    METHOD_NOT_ALLOWED = "method not allowed"
    NOT_FOUND = "not found"
    FILE_NOT_FOUND = "File not found"
    INVALID_JSON = "Invalid JSON"
    SERVER_ERROR = "Server error"
    INVALID_CONTENT_LENGTH = "Invalid Content-Length"
    REQUEST_TOO_LARGE = "Request too large"
    EXPECTED_JSON_OBJECT = "Expected a JSON object"
    SCAN_ALREADY_RUNNING = "A scan is already running"
    HOSTS_UP_TO_DATE = "hosts file is already up to date"
    HOSTS_UPDATED = "hosts file updated"
    TARGET_DOWN = "Target is down"
    ROUTE_NOT_FOUND = "Route not found"


class MessageTemplate:
    RESERVED_BY_SYSTEM = "{name} is reserved by the system"
    CANNOT_BE_DELETED = "{name} cannot be deleted"
    HOSTS_PERMISSION = "Could not write the hosts file (administrator/root required): {path}"
    HOSTS_ERROR = "hosts file error: {exc}"
    NO_ROUTE_CONFIGURED = "No route is configured for {host}."
    TARGET_NOT_RESPONDING = "{host} ({target}) is not responding."

    @staticmethod
    def reserved_by_system(name: str) -> str:
        return MessageTemplate.RESERVED_BY_SYSTEM.format(name=name)

    @staticmethod
    def cannot_be_deleted(name: str) -> str:
        return MessageTemplate.CANNOT_BE_DELETED.format(name=name)

    @staticmethod
    def hosts_permission(path: Any) -> str:
        return MessageTemplate.HOSTS_PERMISSION.format(path=path)

    @staticmethod
    def hosts_error(exc: Any) -> str:
        return MessageTemplate.HOSTS_ERROR.format(exc=exc)

    @staticmethod
    def no_route_configured(host: str) -> str:
        return MessageTemplate.NO_ROUTE_CONFIGURED.format(host=host or "(empty host)")

    @staticmethod
    def target_not_responding(host: str, target: str) -> str:
        return MessageTemplate.TARGET_NOT_RESPONDING.format(host=host, target=target)


class LogMessage:
    PANEL_PORT_UNAVAILABLE = "Panel port (%s) is unavailable: %s"
    SHUTTING_DOWN = "Shutting down..."
    APP_VERSION_INFO = "%s %s"
    PANEL_URL_INFO = "Panel : %s"
    DIRECT_URL_INFO = "Direct: %s"
    SYNC_WARNING = "%s"
    ADD_TO_HOSTS = "  add to hosts: %s"
    PROXY_PORT_WARNING = "Proxy is listening on port %s, so append :%s to the route addresses."
    PROXY_START_ERROR = "Proxy could not start (tried ports: %s)"
    COULD_NOT_READ_ROUTES = "Could not read routes (%s): %s"
    REQUEST_FAILED = "Request failed: %s %s"
    SCAN_STOPPED_UNEXPECTEDLY = "Scan stopped unexpectedly"
    PROXY_CONNECTION_CLOSED = "Proxy connection closed: %s"


class ThreadName(StrEnum):
    PROXY = "proxy"
    SCANNER = "scanner"


class TemplatePlaceholder(StrEnum):
    APP_NAME = "__APP__"


class CliOption(StrEnum):
    TLD = "--tld"
    PANEL = "--panel"
    UI_PORT = "--ui-port"
    PROXY_PORT = "--proxy-port"
    CONFIG_DIR = "--config-dir"
    HOSTS_FILE = "--hosts-file"
    NO_BROWSER = "--no-browser"
    VERBOSE_SHORT = "-v"
    VERBOSE_LONG = "--verbose"
    VERSION = "--version"


class CliFormat(StrEnum):
    LOG_FORMAT = "%(asctime)s %(levelname)-7s %(message)s"
    DATE_FORMAT = "%H:%M:%S"
    DESCRIPTION = "Local port scanner and name router"
