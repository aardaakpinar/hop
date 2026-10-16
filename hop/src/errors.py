"""Application errors. The `status` attribute maps to an HTTP status code in the API layer."""


class HopError(Exception):
    status = 400


class ValidationError(HopError):
    status = 400


class NotFoundError(HopError):
    status = 404


class ConflictError(HopError):
    status = 409
