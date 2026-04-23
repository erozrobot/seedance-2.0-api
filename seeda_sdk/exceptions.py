"""Exception hierarchy for the seeda SDK."""

from __future__ import annotations

from typing import Any, Optional


class SeedaError(Exception):
    """Base class for all seeda SDK errors."""


class SeedaAuthError(SeedaError):
    """Raised when the API key is missing, malformed, or rejected (401)."""


class SeedaAPIError(SeedaError):
    """Raised when the seeda.app API returns a non-zero ``code`` or an HTTP error.

    Attributes:
        message: Human-readable error string (from the server when available).
        code: The ``code`` field returned by the API (or the HTTP status when
            the response could not be parsed).
        status_code: HTTP status code, if known.
        response: Raw response payload, if available.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[int] = None,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.response = response

    def __str__(self) -> str:
        parts = [self.message]
        if self.code is not None:
            parts.append(f"code={self.code}")
        if self.status_code is not None:
            parts.append(f"http={self.status_code}")
        return " | ".join(parts)


class SeedaInsufficientCreditsError(SeedaAPIError):
    """Raised when the account does not have enough credits for the request."""


class SeedaInvalidParamsError(SeedaAPIError):
    """Raised when the API rejects the request as malformed."""
