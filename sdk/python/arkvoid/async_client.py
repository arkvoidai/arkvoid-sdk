"""
ARKVOID Python SDK – Async Client

Full async/await version of ArkvoidClient.
Requires Python 3.8+ and aiohttp (pip install aiohttp).
Falls back to asyncio + urllib for environments without aiohttp.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from .client import SDK_VERSION
from .errors import (
    ArkvoidNetworkError,
    ArkvoidTimeoutError,
    ArkvoidValidationError,
    create_error_from_response,
)
from .hash import hash_value
from .types import (
    DataAccessRecord,
    Environment,
    RiskLevel,
    ToolCallRecord,
    TraceResponse,
    VerifyResponse,
)

try:
    import aiohttp as _aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


async def _async_retry(fn, max_retries: int = 3, base_delay: float = 0.5):
    """Async version of retry with exponential backoff."""
    import random
    from .errors import is_retryable, ArkvoidRateLimitError

    last_error: Exception = RuntimeError("No attempts made")

    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as error:
            last_error = error

            if not is_retryable(error):
                raise

            if attempt == max_retries:
                break

            if isinstance(error, ArkvoidRateLimitError) and error.retry_after_ms:
                delay = error.retry_after_ms / 1000.0
            else:
                exponential = base_delay * (2 ** attempt)
                jitter = random.random() * base_delay
                delay = min(exponential + jitter, 10.0)

            await asyncio.sleep(delay)

    raise last_error


class AsyncArkvoidClient:
    """
    Async version of ArkvoidClient using aiohttp.

    Usage:
        from arkvoid import AsyncArkvoidClient

        async def main():
            async with AsyncArkvoidClient(api_key="ARK_...") as client:
                result = await client.trace(
                    action="chat_completion",
                    agent="my-agent",
                    risk_level="low",
                    duration_ms=1200,
                )
                print(result.trace_id)

        asyncio.run(main())

    Or without context manager:
        client = AsyncArkvoidClient(api_key="ARK_...")
        result = await client.trace(...)
        await client.close()
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
        if not api_key or not api_key.startswith("ARK_"):
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
        self._session: Optional[Any] = None  # aiohttp.ClientSession

        self._headers: Dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"arkvoid-python/{SDK_VERSION}",
            "X-Arkvoid-SDK": f"python-async/{SDK_VERSION}",
        }

    async def __aenter__(self) -> "AsyncArkvoidClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._session and HAS_AIOHTTP:
            await self._session.close()
            self._session = None

    async def _ensure_session(self) -> None:
        if HAS_AIOHTTP and self._session is None:
            import aiohttp

            connector = aiohttp.TCPConnector(limit=100)
            timeout_cfg = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                connector=connector,
                timeout=timeout_cfg,
            )

    # ─────────────────────────────────────────────
    # trace()
    # ─────────────────────────────────────────────

    async def trace(
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
    ) -> Optional[TraceResponse]:
        """Async version of trace(). See ArkvoidClient.trace() for full docs."""
        agent_slug = agent or self._default_agent
        if not agent_slug:
            msg = 'Agent slug required. Pass agent="slug".'
            if self._silent:
                return None
            raise ArkvoidValidationError(msg)

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

        try:
            await self._ensure_session()
            data = await _async_retry(
                lambda: self._post("/traces", payload),
                max_retries=self._max_retries,
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

    async def log_action(
        self,
        fn,
        action: Optional[str] = None,
        risk_level: RiskLevel = "low",
        agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **trace_kwargs: Any,
    ) -> Any:
        """Async version of log_action(). Awaits fn() automatically."""
        action_name = action or getattr(fn, "__name__", "unknown")
        start = time.time()
        result = None
        error: Optional[Exception] = None

        try:
            result = await fn()
            return result
        except Exception as e:
            error = e
            raise
        finally:
            await self.trace(
                action=action_name,
                risk_level="high" if error else risk_level,
                agent=agent,
                duration_ms=int((time.time() - start) * 1000),
                metadata={
                    **(metadata or {}),
                    "success": error is None,
                    **({"error": str(error)} if error else {}),
                },
                **trace_kwargs,
            )

    # ─────────────────────────────────────────────
    # HTTP
    # ─────────────────────────────────────────────

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"

        if HAS_AIOHTTP and self._session:
            return await self._post_aiohttp(url, payload)
        return await self._post_asyncio(url, payload)

    async def _post_aiohttp(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import aiohttp

        try:
            async with self._session.post(url, json=payload) as resp:
                body = await resp.text()
                return self._handle_response(resp.status, body)
        except aiohttp.ClientConnectorError as e:
            raise ArkvoidNetworkError(e) from e
        except asyncio.TimeoutError as e:
            raise ArkvoidTimeoutError(self._timeout) from e

    async def _post_asyncio(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pure asyncio fallback using loop.run_in_executor."""
        import urllib.request

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers, method="POST")

        loop = asyncio.get_event_loop()

        def _do_request():
            import urllib.error
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    return resp.status, resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8") if e.fp else "{}"
                return e.code, body

        try:
            status, body = await loop.run_in_executor(None, _do_request)
        except TimeoutError as e:
            raise ArkvoidTimeoutError(self._timeout) from e
        except OSError as e:
            raise ArkvoidNetworkError(e) from e

        return self._handle_response(status, body)

    def _handle_response(self, status_code: int, body: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}

        if status_code >= 400:
            raise create_error_from_response(status_code, parsed)

        return parsed

    def _debug_log(self, msg: str) -> None:
        if self._debug:
            print(f"[ARKVOID] {msg}")
