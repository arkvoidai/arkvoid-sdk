"""
ARKVOID Python SDK – Custom Exceptions
"""
from typing import Any, Optional


class ArkvoidError(Exception):
    """Base exception for all ARKVOID SDK errors."""
    code: str = "ARKVOID_ERROR"
    status_code: Optional[int] = None

    def __init__(self, message: str, code: Optional[str] = None,
                 status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        if code:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={str(self)!r})"


class ArkvoidAuthError(ArkvoidError):
    """Raised when API key is invalid or revoked."""
    code = "AUTH_ERROR"
    status_code = 401

    def __init__(self, message: str = "Invalid or revoked API key"):
        super().__init__(message)


class ArkvoidNotFoundError(ArkvoidError):
    """Raised when an agent or resource is not found."""
    code = "NOT_FOUND"
    status_code = 404

    def __init__(self, resource: str = "Agent"):
        super().__init__(
            f"{resource} not found. Make sure it's registered at arkvoid.cherazen.com"
        )


class ArkvoidValidationError(ArkvoidError):
    """Raised when request payload is invalid."""
    code = "VALIDATION_ERROR"
    status_code = 400

    def __init__(self, message: str, details: Any = None):
        super().__init__(message, details=details)


class ArkvoidRateLimitError(ArkvoidError):
    """Raised when rate limit is exceeded."""
    code = "RATE_LIMIT"
    status_code = 429

    def __init__(self, retry_after_ms: Optional[int] = None):
        super().__init__("Rate limit exceeded. Please slow down your requests.")
        self.retry_after_ms = retry_after_ms


class ArkvoidTimeoutError(ArkvoidError):
    """Raised when a request times out."""
    code = "TIMEOUT"
    status_code = 408

    def __init__(self, timeout_seconds: float):
        super().__init__(f"Request timed out after {timeout_seconds}s")
        self.timeout_seconds = timeout_seconds


class ArkvoidNetworkError(ArkvoidError):
    """Raised on network/connection errors."""
    code = "NETWORK_ERROR"

    def __init__(self, cause: Optional[Exception] = None):
        msg = f"Network error: {cause}" if cause else "Unable to connect to ARKVOID"
        super().__init__(msg)
        self.__cause__ = cause


class ArkvoidServerError(ArkvoidError):
    """Raised on 5xx server errors."""
    code = "SERVER_ERROR"

    def __init__(self, status_code: int, details: Any = None):
        super().__init__(f"ARKVOID server error (HTTP {status_code})",
                         status_code=status_code, details=details)


def create_error_from_response(status_code: int, body: dict) -> ArkvoidError:
    """Map HTTP status codes to specific exception types."""
    message = body.get("error") or f"HTTP {status_code}"

    if status_code == 401:
        return ArkvoidAuthError(message)
    elif status_code == 404:
        return ArkvoidNotFoundError("Agent")
    elif status_code == 400:
        return ArkvoidValidationError(message, body.get("details"))
    elif status_code == 429:
        retry_after = body.get("retry_after")
        return ArkvoidRateLimitError(
            int(retry_after * 1000) if retry_after else None
        )
    else:
        return ArkvoidServerError(status_code, body)


def is_retryable(error: Exception) -> bool:
    """Returns True if the error is transient and should be retried."""
    if isinstance(error, ArkvoidRateLimitError):
        return True
    if isinstance(error, ArkvoidTimeoutError):
        return True
    if isinstance(error, ArkvoidNetworkError):
        return True
    if isinstance(error, ArkvoidServerError):
        return error.status_code is not None and error.status_code >= 500
    return False
