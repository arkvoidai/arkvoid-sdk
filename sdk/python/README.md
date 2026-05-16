# ARKVOID Python SDK

[![PyPI version](https://img.shields.io/pypi/v/arkvoid.svg)](https://pypi.org/project/arkvoid/)
[![Python](https://img.shields.io/pypi/pyversions/arkvoid.svg)](https://pypi.org/project/arkvoid/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)

Official Python SDK for **ARKVOID** — AI Agent Monitoring & Governance.

Zero required dependencies. Uses Python stdlib only (`hashlib`, `urllib`).  
Optionally install `requests` for connection pooling or `aiohttp` for async.

---

## Installation

```bash
pip install arkvoid

# With requests (recommended for sync usage):
pip install arkvoid[requests]

# With aiohttp (for async):
pip install arkvoid[async]

# Everything:
pip install arkvoid[all]
```

---

## Quick Start

```python
from arkvoid import ArkvoidClient

client = ArkvoidClient(
    api_key="ARK_your_key_here",  # get at arkvoid.cherazen.com
    agent="my-agent",
)

result = client.trace(
    action="document_analysis",
    risk_level="low",
    model_provider="openai",
    model_name="gpt-4o",
    input_tokens=1200,
    output_tokens=340,
    duration_ms=1823,
)

print(result.trace_id)  # ark_a1b2c3d4...
print(result.hash)      # sha256:...
```

---

## API Reference

### `ArkvoidClient(api_key, agent, ...)`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | `str` | **required** | Your API key (`ARK_...`) |
| `agent` | `str` | `None` | Default agent slug |
| `silent` | `bool` | `False` | Never raise. Returns `None` on failure |
| `timeout` | `float` | `10.0` | Request timeout in seconds |
| `max_retries` | `int` | `3` | Retry attempts on transient failures |
| `environment` | `str` | `"production"` | `"production"` \| `"staging"` \| `"development"` |
| `debug` | `bool` | `False` | Verbose logging |

---

### `client.trace(...)`

```python
result = client.trace(
    action="chat_completion",         # required
    risk_level="low",                 # "low"|"medium"|"high"|"critical"
    agent="my-agent",                 # override default
    risk_score=15,                    # 0–100
    input_data=messages,              # SHA-256 hashed automatically
    output_data=response_text,        # SHA-256 hashed automatically
    duration_ms=1423,
    model_provider="openai",
    model_name="gpt-4o",
    input_tokens=850,
    output_tokens=210,
    metadata={"user_id": "u_123"},
    tool_calls=[
        ToolCallRecord(
            tool_name="web_search",
            input={"query": "AI governance"},
            output={"count": 10},
            latency_ms=340,
            status="success",
        )
    ],
    tags=["chat", "production"],
    session_id="sess_abc",
    parent_trace_id="ark_xyz",
)
# result: TraceResponse(trace_id="ark_...", status="verified", hash="sha256:...")
```

---

### `@trace` Decorator

```python
import os
from arkvoid import trace

@trace(
    agent="my-agent",
    action="analyze_document",
    risk_level="low",
    model_provider="openai",
    model_name="gpt-4o",
    tags=["analysis"],
)
def analyze_document(text: str) -> str:
    return llm.complete(text)  # traced automatically

# Async functions work identically:
@trace(agent="my-agent")
async def async_query(prompt: str) -> str:
    return await async_llm.complete(prompt)
```

---

### `@trace_tool` Decorator

For tool/function calls within agents:

```python
from arkvoid import trace_tool

@trace_tool(
    agent="my-agent",
    tool_name="web_search",
    external_system="serpapi",
    risk_level="low",
)
def web_search(query: str) -> dict:
    return serpapi.search(query)
```

---

### `client.log_action(fn, ...)`

Run a callable and auto-trace it:

```python
result = client.log_action(
    lambda: openai_client.chat.completions.create(model="gpt-4o", messages=msgs),
    action="gpt4o_call",
    risk_level="low",
    model_provider="openai",
    model_name="gpt-4o",
)
```

---

### `client.verify(trace_id, expected_hash=None)`

```python
result = client.verify(trace_id="ark_abc123")
print(result.valid)  # True
print(result.hash)   # sha256:...
```

---

## Async Client

```python
import asyncio
from arkvoid import AsyncArkvoidClient

async def main():
    async with AsyncArkvoidClient(api_key="ARK_...") as client:
        result = await client.trace(
            action="async_query",
            agent="my-agent",
            risk_level="low",
        )
        print(result.trace_id)

asyncio.run(main())
```

---

## Hash Utilities

```python
from arkvoid import sha256_hex, hash_value, compute_trace_integrity_hash, hashes_equal

# Hash any value (deterministic, sorted keys)
h = hash_value({"prompt": "hello", "model": "gpt-4o"})
# "sha256:a3f1b2..."

# Verify local trace integrity
expected = compute_trace_integrity_hash(
    agent_id="...", action="document_analysis", timestamp="2025-01-15T10:00:00Z"
)
print(hashes_equal(expected, result.hash))  # True
```

---

## Error Handling

```python
from arkvoid import (
    ArkvoidAuthError,
    ArkvoidNotFoundError,
    ArkvoidRateLimitError,
    ArkvoidTimeoutError,
)

try:
    result = client.trace(action="query", risk_level="low")
except ArkvoidAuthError:
    print("Invalid API key")
except ArkvoidNotFoundError:
    print("Agent not registered — visit arkvoid.cherazen.com")
except ArkvoidRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after_ms}ms")
except ArkvoidTimeoutError:
    print("Request timed out")
```

### Silent Mode

```python
client = ArkvoidClient(api_key="ARK_...", silent=True)
result = client.trace(action="query", risk_level="low")
# result is None if the request failed — never raises
```

---

## Environment Variables

```bash
export ARKVOID_API_KEY=ARK_your_key_here
export ARKVOID_AGENT=my-agent
```

```python
import os
from arkvoid import ArkvoidClient

client = ArkvoidClient(api_key=os.environ["ARKVOID_API_KEY"])
```

---

## License

MIT © [ARKVOID Inc.](https://arkvoid.cherazen.com)
