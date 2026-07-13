"""Exception hierarchy for soon-format."""

from __future__ import annotations


class SoonError(Exception):
    """Base class for all soon-format errors."""


class SoonEncodeError(SoonError):
    """Raised when a value cannot be encoded as SOON."""


class SoonDecodeError(SoonError):
    """Raised when a document cannot be decoded as SOON."""
