"""Custom exceptions for fc-audit."""

from __future__ import annotations


class FCAuditError(Exception):
    """Base exception for fc-audit."""


class InvalidFileError(FCAuditError):
    """Raised when a file is not a valid FCStd file."""


class XMLParseError(FCAuditError):
    """Raised when XML parsing fails."""


class ReferenceError(FCAuditError):
    """Raised when reference parsing fails."""


class ExpressionError(FCAuditError):
    """Raised when expression parsing fails."""
