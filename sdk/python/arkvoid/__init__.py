"""
ARKVOID Python SDK
AI Agent Monitoring & Governance

https://arkvoid.cherazen.com

Quick start:
    from arkvoid import ArkvoidClient

    client = ArkvoidClient(api_key="ARK_your_key_here", agent="my-agent")
    result = client.trace(action="document_analysis", risk_level="low", duration_ms=1200)
    print(result.trace_id)  # ark_abc123...

Decorator usage:
    from arkvoid import trace

    @trace(agent="my-agent")
    def analyze_document(text: str) -> str:
        return llm.complete(text)

Async:
    from arkvoid import AsyncArkvoidClient

    async with AsyncArkvoidClient(api_key="ARK_...") as client:
        await client.trace(action="chat_completion", agent="my-agent")
"""

__version__ = "1.0.0"
__author__ = "ARKVOID Inc."
__email__ = "cherazen.ai@gmail.com"
__license__ = "MIT"
__url__ = "https://arkvoid.cherazen.com"

# ─────────────────────────────────────────────
# Core Client
# ─────────────────────────────────────────────

from .client import ArkvoidClient

# ─────────────────────────────────────────────
# Async Client
# ─────────────────────────────────────────────

from .async_client import AsyncArkvoidClient

# ─────────────────────────────────────────────
# Decorators
# ─────────────────────────────────────────────

from .decorators import trace, trace_tool

# ─────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────

from .types import (
    TraceOptions,
    TraceResponse,
    VerifyResponse,
    ToolCallRecord,
    DataAccessRecord,
    ArkvoidConfig,
    RiskLevel,
    TraceStatus,
    ActionType,
    Environment,
    DataClassification,
)

# ─────────────────────────────────────────────
# Errors
# ─────────────────────────────────────────────

from .errors import (
    ArkvoidError,
    ArkvoidAuthError,
    ArkvoidNotFoundError,
    ArkvoidValidationError,
    ArkvoidRateLimitError,
    ArkvoidTimeoutError,
    ArkvoidNetworkError,
    ArkvoidServerError,
)

# ─────────────────────────────────────────────
# Hash Utilities
# ─────────────────────────────────────────────

from .hash import (
    sha256_hex,
    sha256_prefixed,
    hash_value,
    hash_value_raw,
    compute_trace_integrity_hash,
    hash_api_key,
    hashes_equal,
    is_valid_hash,
    is_valid_trace_id,
    strip_prefix,
)

# ─────────────────────────────────────────────
# Public API surface
# ─────────────────────────────────────────────

__all__ = [
    # Clients
    "ArkvoidClient",
    "AsyncArkvoidClient",
    # Decorators
    "trace",
    "trace_tool",
    # Types
    "TraceOptions",
    "TraceResponse",
    "VerifyResponse",
    "ToolCallRecord",
    "DataAccessRecord",
    "ArkvoidConfig",
    # Type aliases
    "RiskLevel",
    "TraceStatus",
    "ActionType",
    "Environment",
    "DataClassification",
    # Errors
    "ArkvoidError",
    "ArkvoidAuthError",
    "ArkvoidNotFoundError",
    "ArkvoidValidationError",
    "ArkvoidRateLimitError",
    "ArkvoidTimeoutError",
    "ArkvoidNetworkError",
    "ArkvoidServerError",
    # Hash utilities
    "sha256_hex",
    "sha256_prefixed",
    "hash_value",
    "hash_value_raw",
    "compute_trace_integrity_hash",
    "hash_api_key",
    "hashes_equal",
    "is_valid_hash",
    "is_valid_trace_id",
    "strip_prefix",
    # Meta
    "__version__",
]
