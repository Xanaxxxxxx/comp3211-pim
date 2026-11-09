"""Errors callers can present to a user without a traceback."""


class PIMError(Exception):
    """Base class for expected application failures."""


class ValidationError(PIMError):
    """A field or operation does not satisfy the model's rules."""


class RecordNotFound(PIMError):
    """No record has the requested identifier."""


class CriteriaError(PIMError):
    """A search expression is invalid."""


class StorageError(PIMError):
    """A .pim file cannot be read or written safely."""
