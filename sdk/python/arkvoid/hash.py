"""
ARKVOID Python SDK – Cryptographic Hash Utilities

Uses stdlib hashlib only. Zero external dependencies.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


# ─────────────────────────────────────────────
# Core SHA-256
# ─────────────────────────────────────────────

def sha256_hex(data: str | bytes) -> str:
    """Compute SHA-256 and return hex digest."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_prefixed(data: str | bytes) -> str:
    """Compute SHA-256 and return 'sha256:<hex>' string."""
    return f"sha256:{sha256_hex(data)}"


# ─────────────────────────────────────────────
# Value Hashing
# ─────────────────────────────────────────────

def hash_value(value: Any) -> str:
    """
    Hash any JSON-serialisable value.
    Keys are sorted for determinism.
    Returns 'sha256:<hex>'.
    """
    if isinstance(value, (str, bytes)):
        serialised = value if isinstance(value, str) else value.decode("utf-8")
    else:
        serialised = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)

    return sha256_prefixed(serialised)


def hash_value_raw(value: Any) -> str:
    """Like hash_value but returns raw hex (no prefix)."""
    return hash_value(value).removeprefix("sha256:")


# ─────────────────────────────────────────────
# Trace Integrity Hash
# ─────────────────────────────────────────────

def compute_trace_integrity_hash(agent_id: str, action: str, timestamp: str) -> str:
    """
    Compute the canonical trace integrity hash.

    Matches the server-side formula:
      SHA-256(agent_id + action + timestamp)

    Returns 'sha256:<hex>'.
    """
    raw = agent_id + action + timestamp
    return sha256_prefixed(raw)


# ─────────────────────────────────────────────
# API Key Hash
# ─────────────────────────────────────────────

def hash_api_key(api_key: str) -> str:
    """
    Compute SHA-256 of an API key (same as server uses).
    Returns raw hex.
    """
    return sha256_hex(api_key)


# ─────────────────────────────────────────────
# Comparison
# ─────────────────────────────────────────────

def strip_prefix(hash_str: str) -> str:
    """Strip 'sha256:' prefix if present."""
    return hash_str.removeprefix("sha256:")


def hashes_equal(a: str, b: str) -> bool:
    """
    Compare two hashes in constant time.
    Accepts hashes with or without 'sha256:' prefix.
    """
    return hmac.compare_digest(strip_prefix(a), strip_prefix(b))


# ─────────────────────────────────────────────
# Verification Helpers
# ─────────────────────────────────────────────

def is_valid_hash(hash_str: str) -> bool:
    """Check if a string is a valid ARKVOID hash (sha256:<64 hex chars>)."""
    if not hash_str.startswith("sha256:"):
        return False
    hex_part = hash_str[7:]
    return len(hex_part) == 64 and all(c in "0123456789abcdef" for c in hex_part)


def is_valid_trace_id(trace_id: str) -> bool:
    """Check if a string is a valid ARKVOID trace ID (ark_<32 hex chars>)."""
    if not trace_id.startswith("ark_"):
        return False
    hex_part = trace_id[4:]
    return len(hex_part) == 32 and all(c in "0123456789abcdef" for c in hex_part)
