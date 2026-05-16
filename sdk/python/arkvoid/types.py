"""
ARKVOID Python SDK – Type Definitions
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


# ─────────────────────────────────────────────
# Enums / Literals
# ─────────────────────────────────────────────

RiskLevel = Literal["low", "medium", "high", "critical"]
TraceStatus = Literal["verified", "failed", "pending_approval"]
ActionType = Literal["inference", "tool_call", "approval", "data_access", "custom"]
Environment = Literal["production", "staging", "development", "test"]
DataClassification = Literal["public", "internal", "confidential", "restricted"]
ToolStatus = Literal["success", "error", "timeout"]


# ─────────────────────────────────────────────
# Sub-Records
# ─────────────────────────────────────────────

@dataclass
class ToolCallRecord:
    """Represents a single tool/function call within a trace."""
    tool_name: str
    call_index: Optional[int] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    external_system: Optional[str] = None
    latency_ms: Optional[int] = None
    status: ToolStatus = "success"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"toolName": self.tool_name, "status": self.status}
        if self.call_index is not None:
            d["callIndex"] = self.call_index
        if self.input is not None:
            d["input"] = self.input
        if self.output is not None:
            d["output"] = self.output
        if self.external_system:
            d["externalSystem"] = self.external_system
        if self.latency_ms is not None:
            d["latencyMs"] = self.latency_ms
        return d


@dataclass
class DataAccessRecord:
    """Represents a data source access within a trace."""
    data_source: str
    data_classification: DataClassification = "internal"
    contains_pii: bool = False
    records_accessed: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "dataSource": self.data_source,
            "dataClassification": self.data_classification,
            "containsPii": self.contains_pii,
        }
        if self.records_accessed is not None:
            d["recordsAccessed"] = self.records_accessed
        return d


# ─────────────────────────────────────────────
# Trace Options
# ─────────────────────────────────────────────

@dataclass
class TraceOptions:
    """All options for sending a trace to ARKVOID."""
    action: str
    risk_level: RiskLevel = "low"
    agent: Optional[str] = None
    risk_score: Optional[int] = None
    input_data: Optional[Any] = None      # will be SHA-256 hashed
    output_data: Optional[Any] = None     # will be SHA-256 hashed
    input_hash: Optional[str] = None      # pre-computed hash
    output_hash: Optional[str] = None     # pre-computed hash
    duration_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[ToolCallRecord]] = None
    data_access: Optional[List[DataAccessRecord]] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    action_type: ActionType = "inference"
    tags: Optional[List[str]] = None
    session_id: Optional[str] = None
    parent_trace_id: Optional[str] = None
    required_human_approval: Optional[bool] = None


# ─────────────────────────────────────────────
# Response Types
# ─────────────────────────────────────────────

@dataclass
class TraceResponse:
    """Response from the ARKVOID traces endpoint."""
    trace_id: str
    timestamp: str
    status: TraceStatus
    hash: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceResponse":
        return cls(
            trace_id=data["trace_id"],
            timestamp=data["timestamp"],
            status=data["status"],
            hash=data["hash"],
        )

    def __repr__(self) -> str:
        return f"TraceResponse(trace_id={self.trace_id!r}, status={self.status!r})"


@dataclass
class VerifyResponse:
    """Response from trace verification."""
    trace_id: str
    valid: bool
    status: TraceStatus
    hash: str
    timestamp: str
    matches_expected: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], expected_hash: Optional[str] = None) -> "VerifyResponse":
        status: TraceStatus = data["status"]
        valid = status != "failed"
        matches_expected: Optional[bool] = None

        if expected_hash:
            server_hash = data.get("hash", "")
            # Strip sha256: prefix for comparison
            clean_expected = expected_hash.replace("sha256:", "")
            clean_server = server_hash.replace("sha256:", "")
            matches_expected = clean_expected == clean_server

        return cls(
            trace_id=data["trace_id"],
            valid=valid,
            status=status,
            hash=data.get("hash", ""),
            timestamp=data.get("timestamp", ""),
            matches_expected=matches_expected,
        )


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

@dataclass
class ArkvoidConfig:
    """Configuration for ArkvoidClient."""
    api_key: str
    agent: Optional[str] = None
    silent: bool = False
    base_url: str = "https://arkvoid.cherazen.com/api/v1"
    timeout: float = 10.0
    max_retries: int = 3
    environment: Environment = "production"
    sdk_version: str = "1.0.0"
    debug: bool = False
