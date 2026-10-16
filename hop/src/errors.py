"""Application errors. The `status` attribute maps to an HTTP status code in the API layer."""
from __future__ import annotations

from .constants import HttpStatus


class HopError(Exception):
    status = HttpStatus.BAD_REQUEST


class ValidationError(HopError):
    status = HttpStatus.BAD_REQUEST


class NotFoundError(HopError):
    status = HttpStatus.NOT_FOUND


class ConflictError(HopError):
    status = HttpStatus.CONFLICT
