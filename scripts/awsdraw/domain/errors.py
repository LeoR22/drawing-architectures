"""Domain errors. Messages must tell the caller how to fix the problem."""


class SpecError(ValueError):
    """An input spec is malformed or inconsistent."""


class DocumentError(SpecError):
    """A supplied document cannot be read; the message says what to do instead."""
