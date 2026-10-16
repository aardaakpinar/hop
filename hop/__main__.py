"""Entry point for `python -m hop`."""
import sys

from .src.cli import main

sys.exit(main())
