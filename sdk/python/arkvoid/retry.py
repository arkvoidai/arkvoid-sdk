"""
ARKVOID Python SDK – Retry Logic with Exponential Backoff + Jitter
"""
from __future__ import annotations

import random
import time
from typing import Callable, Optional, TypeVar

from .errors import ArkvoidRateLimitError, is_retryable

T = TypeVar("T")

DEFAULT_BASE_DELAY = 0.5     # seconds
DEFAULT_MAX_DELAY = 10.0     # seconds
DEFAULT_MAX_RETRIES = 3


def with_retry(
    fn: Callable[[], T],
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    on_retry: Optional[Callable[[int, float, Exception], None]] = None,
) -> T:
    """
    Execute a callable with exponential backoff + full jitter retry.

    - Does NOT retry 4xx errors (except 429 rate limit).
    - Does NOT retry auth errors.
    - Respects retry_after_ms from rate limit errors.

    Args:
        fn: Callable to execute.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        on_retry: Optional callback (attempt, delay_seconds, error).

    Returns:
        Result of fn() on success.

    Raises:
        Last exception if all retries are exhausted.
    """
    last_error: Exception = RuntimeError("No attempts made")

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as error:
            last_error = error

            if not is_retryable(error):
                raise

            if attempt == max_retries:
                break

            # Calculate delay
            if isinstance(error, ArkvoidRateLimitError) and error.retry_after_ms:
                delay = error.retry_after_ms / 1000.0
            else:
                # Exponential backoff with full jitter
                exponential = base_delay * (2 ** attempt)
                jitter = random.random() * base_delay
                delay = min(exponential + jitter, max_delay)

            if on_retry:
                on_retry(attempt + 1, delay, error)

            time.sleep(delay)

    raise last_error


def calculate_delay(attempt: int, base_delay: float = DEFAULT_BASE_DELAY,
                    max_delay: float = DEFAULT_MAX_DELAY) -> float:
    """Calculate delay for a given attempt (deterministic, no jitter)."""
    return min(base_delay * (2 ** attempt), max_delay)
