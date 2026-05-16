"""
ARKVOID Python SDK – ArkvoidClient

Primary interface for sending AI traces to ARKVOID.
Supports both requests (preferred) and stdlib urllib as fallback.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .errors import (
    ArkvoidAuthError,
    ArkvoidNetworkError,
    ArkvoidTimeoutError,
    ArkvoidValidationError,
    create_error_from_response,
)
from .hash import hash_value, compute_trace_integrity_hash
from .retry import with_retry
from .types import (
    ArkvoidConfig,
    DataAccessRecord,
    Environment,
    RiskLevel,
    ToolCallRecord,
    TraceOptions,
    TraceResponse,
    VerifyResponse,
)

SDK_VERSION = "1.0.0"

# Optional dependency
try:
    import requests as _requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class ArkvoidClient:
    """
    ARKVOID AI Agent Governance Client.

    Usage:
        from arkvoid import ArkvoidClient

        client = ArkvoidClient(
            api_key="ARK_your_key_here",
            agent="my-agent",
        )

        result = client.trace(
            action="document_analysis",
            risk_level="low",
            model_provider="openai",
            model_name="gpt-4o",
            duration_ms=1823,
        )
        print(result.trace_id)  # ark_abc123...
    """

    BASE_URL = "https://arkvoid.cherazen.com/api/v1"

    def __init__(
        self,
        api_key: str,
        agent: Optional[str] = None,
        silent: bool = False,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        environment: Environment = "production",
        debug: bool = False,
    ) -> None:
        """
        Args:
            api_key: Your ARKVOID API key (must start with ARK_).
            agent: Default agent slug. Can be overridden per trace.
            silent: If True, suppress all errors. Returns None on failure.
            base_url: Override the API base URL.
            timeout: Request timeout in seconds. Default: 10.
            max_retries: Max retry attempts on transient failures. Default: 3.
            environment: Tag traces by environment.
            debug: Enable verbose debug logging.
        """
        if not api_key:
            raise ArkvoidValidationError(
                "api_key is required. Get yours at arkvoid.cherazen.com"
            )
        if not api_key.startswith("ARK_"):
            raise ArkvoidValidationError(
                'API key must start with "ARK_". Get yours at arkvoid.cherazen.com'
            )

        self._api_key = api_key
        self._default_agent = agent
        self._silent = silent
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._environment = environment
        self._debug = debug

        self._headers: Dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"arkvoid-python/{SDK_VERSION}",
            "X-Arkvoid-SDK": f"python/{SDK_VERSION}",
        }

        # Set up requests session if available
        self._session: Optional[Any] = None
        if HAS_REQUESTS:
            import requests

            self._session = requests.Session()
            self._session.headers.update(self._headers)

    # ─────────────────────────────────────────────
    # trace()
    # ─────────────────────────────────────────────

    def trace(
        self,
        action: str,
        risk_level: RiskLevel = "low",
        agent: Optional[str] = None,
        risk_score: Optional[int] = None,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
        input_hash: Optional[str] = None,
        output_hash: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[ToolCallRecord]] = None,
        data_access: Optional[List[DataAccessRecord]] = None,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        action_type: str = "inference",
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        parent_trace_id: Optional[str] = None,
        required_human_approval: Optional[bool] = None,
    ) -> Optional[TraceResponse]:
        """
        Send an AI action trace to ARKVOID.

        Args:
            action: What the agent did. e.g. "document_analysis", "user_query"
            risk_level: "low" | "medium" | "high" | "critical"
            agent: Agent slug override (uses default if not provided).
            risk_score: Numeric 0-100 score (optional).
            input_data: Raw input — will be SHA-256 hashed, NOT stored as plaintext.
            output_data: Raw output — will be SHA-256 hashed, NOT stored as plaintext.
            input_hash: Pre-computed SHA-256 hash of input (bypasses auto-hashing).
            output_hash: Pre-computed SHA-256 hash of output (bypasses auto-hashing).
            duration_ms: How long the action took in milliseconds.
            metadata: Arbitrary key-value metadata.
            tool_calls: List of ToolCallRecord objects.
            data_access: List of DataAccessRecord objects.
            model_provider: e.g. "openai", "anthropic", "mistral"
            model_name: e.g. "gpt-4o", "claude-3-5-sonnet-20241022"
            input_tokens: Prompt token count.
            output_tokens: Completion token count.
            action_type: "inference" | "tool_call" | "approval" | "data_access" | "custom"
            tags: List of string tags for filtering.
            session_id: Group related traces under a session.
            parent_trace_id: Link this trace as a child of another.
            required_human_approval: Whether human review is required.

        Returns:
            TraceResponse on success, None if silent=True and request fails.
        """
        agent_slug = agent or self._default_agent
        if not agent_slug:
            msg = (
                'Agent slug is required. Pass agent="slug" or set it in '
                'ArkvoidClient(agent="slug").'
            )
            if self._silent:
                self._debug_log(f"[WARN] {msg}")
                return None
            raise ArkvoidValidationError(msg)

        # Build payload
        payload: Dict[str, Any] = {
            "agent_slug": agent_slug,
            "action": action,
            "risk_level": risk_level,
            "action_type": action_type,
            "environment": self._environment,
            "sdk_version": SDK_VERSION,
        }

        if risk_score is not None:
            payload["risk_score"] = max(0, min(100, risk_score))

        # Compute hashes
        computed_input_hash = input_hash or (
            hash_value(input_data) if input_data is not None else None
        )
        computed_output_hash = output_hash or (
            hash_value(output_data) if output_data is not None else None
        )

        if computed_input_hash:
            payload["input_hash"] = computed_input_hash
        if computed_output_hash:
            payload["output_hash"] = computed_output_hash
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        if metadata:
            payload["metadata"] = metadata
        if tool_calls:
            payload["tool_calls"] = [tc.to_dict() for tc in tool_calls]
        if data_access:
            payload["data_access"] = [da.to_dict() for da in data_access]
        if model_provider:
            payload["model_provider"] = model_provider
        if model_name:
            payload["model_name"] = model_name
        if input_tokens is not None:
            payload["input_tokens"] = input_tokens
        if output_tokens is not None:
            payload["output_tokens"] = output_tokens
        if tags:
            payload["tags"] = tags
        if session_id:
            payload["session_id"] = session_id
        if parent_trace_id:
            payload["parent_trace_id"] = parent_trace_id
        if required_human_approval is not None:
            payload["required_human_approval"] = required_human_approval

        try:
            data = with_retry(
                lambda: self._post("/traces", payload),
                max_retries=self._max_retries,
                on_retry=lambda attempt, delay, err: self._debug_log(
                    f"Retry {attempt} in {delay:.1f}s: {err}"
                ),
            )
            response = TraceResponse.from_dict(data)
            self._debug_log(f"Trace recorded: {response.trace_id}")
            return response

        except Exception as error:
            if self._silent:
                self._debug_log(f"[WARN] Failed to send trace: {error}")
                return None
            raise

    # ─────────────────────────────────────────────
    # log_action()
    # ─────────────────────────────────────────────

    def log_action(
        self,
        fn,
        action: Optional[str] = None,
        risk_level: RiskLevel = "low",
        agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        capture_output: bool = False,
        **trace_kwargs: Any,
    ):
        """
        Execute a callable and automatically trace it.

        Args:
            fn: Callable to execute and trace.
            action: Action name. Defaults to fn.__name__.
            risk_level: Risk level for the trace.
            agent: Agent slug override.
            metadata: Additional metadata.
            capture_output: Hash and record function output.
            **trace_kwargs: Any additional TraceOptions keyword arguments.

        Returns:
            Return value of fn().

        Example:
            result = client.log_action(
                lambda: openai_client.chat.completions.create(...),
                action="chat_completion",
                risk_level="low",
            )
        """
        action_name = action or getattr(fn, "__name__", "unknown_action")
        start = time.time()
        result = None
        error: Optional[Exception] = None

        try:
            result = fn()
        except Exception as e:
            error = e
            raise
        finally:
            duration_ms = int((time.time() - start) * 1000)
            self.trace(
                action=action_name,
                risk_level="high" if error else risk_level,
                agent=agent,
                duration_ms=duration_ms,
                output_data=result if capture_output and result is not None else None,
                metadata={
                    **(metadata or {}),
                    "success": error is None,
                    **({"error": str(error), "error_type": type(error).__name__} if error else {}),
                },
                **trace_kwargs,
            )

        return result

    # ─────────────────────────────────────────────
    # verify()
    # ─────────────────────────────────────────────

    def verify(
        self, trace_id: str, expected_hash: Optional[str] = None
    ) -> VerifyResponse:
        """
        Verify that a trace exists and its hash is valid.

        Args:
            trace_id: The trace ID to verify (ark_...).
            expected_hash: Optional hash to compare against.

        Returns:
            VerifyResponse with valid=True if trace is authentic.
        """
        data = with_retry(
            lambda: self._get(f"/traces/{trace_id}"),
            max_retries=self._max_retries,
        )
        return VerifyResponse.from_dict(data, expected_hash=expected_hash)

    # ─────────────────────────────────────────────
    # HTTP internals
    # ─────────────────────────────────────────────

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        self._debug_log(f"→ POST {url}")

        if HAS_REQUESTS and self._session is not None:
            return self._post_requests(url, payload)
        return self._post_urllib(url, payload)

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        self._debug_log(f"→ GET {url}")

        if HAS_REQUESTS and self._session is not None:
            return self._get_requests(url)
        return self._get_urllib(url)

    def _post_requests(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import requests

        try:
            resp = self._session.post(url, json=payload, timeout=self._timeout)
        except requests.Timeout as e:
            raise ArkvoidTimeoutError(self._timeout) from e
        except requests.ConnectionError as e:
            raise ArkvoidNetworkError(e) from e

        return self._handle_response(resp.status_code, resp.text)

    def _get_requests(self, url: str) -> Dict[str, Any]:
        import requests

        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.Timeout as e:
            raise ArkvoidTimeoutError(self._timeout) from e
        except requests.ConnectionError as e:
            raise ArkvoidNetworkError(e) from e

        return self._handle_response(resp.status_code, resp.text)

    def _post_urllib(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers=self._headers, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                status = resp.status
        except TimeoutError as e:
            raise ArkvoidTimeoutError(self._timeout) from e
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else "{}"
            return self._handle_response(e.code, body)
        except urllib.error.URLError as e:
            raise ArkvoidNetworkError(e) from e

        return self._handle_response(status, body)

    def _get_urllib(self, url: str) -> Dict[str, Any]:
        req = urllib.request.Request(url, headers=self._headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
                status = resp.status
        except TimeoutError as e:
            raise ArkvoidTimeoutError(self._timeout) from e
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else "{}"
            return self._handle_response(e.code, body)
        except urllib.error.URLError as e:
            raise ArkvoidNetworkError(e) from e

        return self._handle_response(status, body)

    def _handle_response(self, status_code: int, body: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}

        self._debug_log(f"← {status_code}")

        if status_code >= 400:
            raise create_error_from_response(status_code, parsed)

        return parsed

    def _debug_log(self, msg: str) -> None:
        if self._debug:
            print(f"[ARKVOID] {msg}")
      
