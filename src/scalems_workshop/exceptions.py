"""Custom exceptions thrown by modules in this package."""


class UsageError(Exception):
    """A module feature is being misused."""


class MissingImplementationError(Exception):
    """The requested feature is not (yet) implemented."""
