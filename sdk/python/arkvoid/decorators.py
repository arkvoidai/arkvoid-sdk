"""
ARKVOID Python SDK – Decorators

@trace decorator for automatic function tracing.
Works with sync and async functions.
"""
from __future__ import annotations

import functools
import os
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, overload

from .client import ArkvoidClient
from .types import RiskLevel, ToolCallRecord, DataAccessRecord

F = TypeVar("F", bound=Callable[..., Any])

# ─────────────────────────────────────────────
# @trace decorator
# ─────────────────────────────────────────────

def trace(
    agent: str,
    action: Optional[str] = None,
    risk_level: RiskLevel = "low",
    api_key: Optional[str] = None,
    silent: bool = True,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    capture_input: bool = False,
    capture_output: bool = False,
    environment: str = "production",
) -> Callable[[F], F]:
    """
    Decorator that automatically traces function calls to ARKVOID.

    Works with both sync and async functions.

    Args:
        agent: Agent slug (register at arkvoid.cherazen.com).
        action: Action name. Defaults to function name.
        risk_level: "low" | "medium" | "high" | "critical"
        api_key: API key. Defaults to ARKVOID_API_KEY env var.
        silent: If True, never raise SDK errors. Default: True.
        model_provider: e.g. "openai", "anthropic"
        model_name: e.g. "gpt-4o"
        tags: List of string tags.
        metadata: Static metadata merged into every trace.
        capture_input: Hash and record function args. Default: False.
        capture_output: Hash and record function return value. Default: False.
        environment: "production" | "staging" | "development" | "test"

    Usage:
        import os
        from arkvoid import trace

        @trace(agent="my-agent", api_key=os.environ["ARKVOID_API_KEY"])
        def analyze_document(text: str) -> str:
            return llm.complete(text)

        # Async functions work identically:
        @trace(agent="my-agent")
        async def async_query(prompt: str) -> str:
            return await async_llm.complete(prompt)
    """
    key = api_key or os.environ.get("ARKVOID_API_KEY")

    if not key and not silent:
        raise ValueError(
            "Set the ARKVOID_API_KEY environment variable or pass api_key= to @trace"
        )

    client = ArkvoidClient(
        api_key=key or "ARK_missing",
        agent=agent,
        silent=silent,
        environment=environment,  # type: ignore[arg-type]
    )

    def decorator(fn: F) -> F:
        func_action = action or fn.__name__.replace("_", " ")
        is_async = _is_async(fn)

        if is_async:
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.time()
                result = None
                error: Optional[Exception] = None

                try:
                    result = await fn(*args, **kwargs)
                    return result
                except Exception as e:
                    error = e
                    raise
                finally:
                    duration_ms = int((time.time() - start) * 1000)
                    client.trace(
                        action=func_action,
                        risk_level=risk_level,
                        duration_ms=duration_ms,
                        model_provider=model_provider,
                        model_name=model_name,
                        tags=tags,
                        input_data=args[0] if capture_input and args else None,
                        output_data=result if capture_output and result is not None else None,
                        metadata={
                            **(metadata or {}),
                            "function": fn.__name__,
                            "success": error is None,
                            **({"error": str(error), "error_type": type(error).__name__} if error else {}),
                        },
                    )

            return async_wrapper  # type: ignore[return-value]

        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.time()
                result = None
                error: Optional[Exception] = None

                try:
                    result = fn(*args, **kwargs)
                    return result
                except Exception as e:
                    error = e
                    raise
                finally:
                    duration_ms = int((time.time() - start) * 1000)
                    client.trace(
                        action=func_action,
                        risk_level=risk_level,
                        duration_ms=duration_ms,
                        model_provider=model_provider,
                        model_name=model_name,
                        tags=tags,
                        input_data=args[0] if capture_input and args else None,
                        output_data=result if capture_output and result is not None else None,
                        metadata={
                            **(metadata or {}),
                            "function": fn.__name__,
                            "success": error is None,
                            **({"error": str(error), "error_type": type(error).__name__} if error else {}),
                        },
                    )

            return sync_wrapper  # type: ignore[return-value]

    return decorator


# ─────────────────────────────────────────────
# @trace_tool decorator (for tool functions)
# ─────────────────────────────────────────────

def trace_tool(
    agent: str,
    tool_name: Optional[str] = None,
    external_system: Optional[str] = None,
    risk_level: RiskLevel = "medium",
    api_key: Optional[str] = None,
    silent: bool = True,
) -> Callable[[F], F]:
    """
    Decorator specifically for tool/function calls within an agent.
    Records the call as action_type="tool_call" with detailed tool metadata.

    Usage:
        @trace_tool(agent="my-agent", tool_name="web_search", external_system="serpapi")
        def web_search(query: str) -> dict:
            return serpapi.search(query)
    """
    key = api_key or os.environ.get("ARKVOID_API_KEY")

    client = ArkvoidClient(
        api_key=key or "ARK_missing",
        agent=agent,
        silent=silent,
    )

    def decorator(fn: F) -> F:
        name = tool_name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            result = None
            status: str = "success"
            error: Optional[Exception] = None

            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                status = "error"
                raise
            finally:
                duration_ms = int((time.time() - start) * 1000)
                tool_input = {"args": list(args), "kwargs": kwargs} if args or kwargs else {}
                tool_output = {"result": str(result)[:500]} if result is not None else {}

                client.trace(
                    action=f"tool_call.{name}",
                    risk_level=risk_level,
                    action_type="tool_call",
                    duration_ms=duration_ms,
                    tool_calls=[
                        ToolCallRecord(
                            tool_name=name,
                            call_index=0,
                            input=tool_input,
                            output=tool_output if not error else {"error": str(error)},
                            external_system=external_system,
                            latency_ms=duration_ms,
                            status=status,  # type: ignore[arg-type]
                        )
                    ],
                    metadata={
                        "function": fn.__name__,
                        "success": error is None,
                    },
                )

        return wrapper  # type: ignore[return-value]

    return decorator


# ─────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────

def _is_async(fn: Callable[..., Any]) -> bool:
    import asyncio
    import inspect
    return asyncio.iscoroutinefunction(fn) or inspect.iscoroutinefunction(fn)
