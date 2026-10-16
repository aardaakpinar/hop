"""Command-line interface."""
from __future__ import annotations

import argparse
import logging
import re
import signal
from pathlib import Path

from .. import APP_NAME, __version__
from .app import Application
from .config import Settings
from .constants import CliFormat, CliOption

_LABEL_RE = re.compile(r"^[a-z0-9-]{1,63}$")


def _label(value: str) -> str:
    value = value.strip(".").lower()
    if not _LABEL_RE.match(value):
        raise argparse.ArgumentTypeError(f"invalid value: {value!r}")
    return value


def build_parser() -> argparse.ArgumentParser:
    d = Settings()
    p = argparse.ArgumentParser(prog=APP_NAME.lower(), description=CliFormat.DESCRIPTION)
    p.add_argument(CliOption.TLD, type=_label, default=d.tld, help=f"default suffix (default: {d.tld})")
    p.add_argument(CliOption.PANEL, type=_label, default=d.panel_label, help="panel name: <panel>.<tld>")
    p.add_argument(CliOption.UI_PORT, type=int, default=d.ui_port, help="direct access port of the panel")
    p.add_argument(CliOption.PROXY_PORT, type=int, default=0, help="proxy port (default: 80, falls back to 8080)")
    p.add_argument(CliOption.CONFIG_DIR, type=Path, default=d.config_dir, help="directory for stored routes")
    p.add_argument(CliOption.HOSTS_FILE, type=Path, default=d.hosts_path, help="path to the hosts file")
    p.add_argument(CliOption.NO_BROWSER, action="store_true", help="do not open the browser automatically")
    p.add_argument(CliOption.VERBOSE_SHORT, CliOption.VERBOSE_LONG, action="store_true", help="verbose logging")
    p.add_argument(CliOption.VERSION, action="version", version=f"{APP_NAME} {__version__}")
    return p


def _terminate(signum, frame):  # makes SIGTERM shut down cleanly too
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format=CliFormat.LOG_FORMAT,
        datefmt=CliFormat.DATE_FORMAT,
    )
    settings = Settings(
        tld=args.tld,
        ui_port=args.ui_port,
        proxy_port=args.proxy_port,
        panel_label=args.panel,
        open_browser=not args.no_browser,
        config_dir=args.config_dir,
        hosts_path=args.hosts_file,
    )
    signal.signal(signal.SIGTERM, _terminate)
    return Application(settings).run()
