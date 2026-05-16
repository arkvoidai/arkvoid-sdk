# ARKVOID SDK – API Reference

## REST API

**Base URL**: `https://arkvoid.cherazen.com/api/v1`

All requests must include:
```
Authorization: Bearer ARK_your_key_here
Content-Type: application/json
```

---

## POST /traces

Create a new trace record.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_slug` | `string` | ✅ | Your registered agent slug |
| `action` | `string` | ✅ | What the agent did |
| `risk_level` | `string` | ✅ | `"low"` \| `"medium"` \| `"high"` \| `"critical"` |
| `risk_score` | `integer` | ❌ | Numeric score 0–100 |
| `input_hash` | `string` | ❌ | SHA-256 hash of input (`sha256:<hex>`) |
| `output_hash` | `string` | ❌ | SHA-256 hash of output |
| `duration_ms` | `integer` | ❌ | Action duration in milliseconds |
| `metadata` | `object` | ❌ | Arbitrary key-value data |
| `model_provider` | `string` | ❌ | `"openai"`, `"anthropic"`, etc. |
| `model_name` | `string` | ❌ | `"gpt-4o"`, `"claude-3-5-sonnet"`, etc. |
| `input_tokens` | `integer` | ❌ | Prompt token count |
| `output_tokens` | `integer` | ❌ | Completion token count |
| `action_type` | `string` | ❌ | `"inference"` \| `"tool_call"` \| `"data_access"` \| `"approval"` |
| `tags` | `string[]` | ❌ | Array of string tags |
| `session_id` | `string` | ❌ | Group traces under a session |
| `parent_trace_id` | `string` | ❌ | Link as child of another trace |
| `required_human_approval` | `boolean` | ❌ | Flag for human review |
| `tool_calls` | `ToolCall[]` | ❌ | Tool invocations in this trace |
| `data_access` | `DataAccess[]` | ❌ | Data sources accessed |
| `environment` | `string` | ❌ | `"production"` \| `"staging"` \| `"development"` |
| `sdk_version` | `string` | ❌ | SDK version string |

### ToolCall Object

```json
{
  "toolName": "web_search",
  "callIndex": 0,
  "input": { "query": "AI governance" },
  "output": { "resultCount": 10 },
  "externalSystem": "serpapi",
  "latencyMs": 340,
  "status": "success"
}
```

### DataAccess Object

```json
{
  "dataSource": "user_database",
  "dataClassification": "confidential",
  "containsPii": true,
  "recordsAccessed": 1
}
```

### Response `201 Created`

```json
{
  "trace_id": "ark_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "timestamp": "2025-01-15T10:23:45.123Z",
  "status": "verified",
  "hash": "sha256:a3f1b2c4d5e6f7..."
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| `400` | `VALIDATION_ERROR` | Missing required fields |
| `401` | `AUTH_ERROR` | Invalid or revoked API key |
| `404` | `NOT_FOUND` | Agent not found |
| `429` | `RATE_LIMIT` | Too many requests |
| `500` | `SERVER_ERROR` | Internal server error |

---

## GET /traces/:traceId

Retrieve and verify a specific trace.

### Response `200 OK`

```json
{
  "trace_id": "ark_abc123...",
  "timestamp": "2025-01-15T10:23:45.123Z",
  "status": "verified",
  "hash": "sha256:...",
  "action": "document_analysis",
  "risk_level": "low",
  "risk_score": 12,
  "agent_id": "uuid...",
  "duration_ms": 1823
}
```

---

## Cryptographic Hash Format

Every trace is assigned an integrity hash using the formula:

```
SHA-256(agent_id + action + timestamp)
```

The hash is returned as `sha256:<64-hex-character-string>`.

You can verify traces locally without an API call:

```python
from arkvoid import compute_trace_integrity_hash, hashes_equal

computed = compute_trace_integrity_hash(
    agent_id="your-agent-uuid",
    action="document_analysis",
    timestamp="2025-01-15T10:23:45.123Z"
)
is_valid = hashes_equal(computed, trace_response.hash)
```

---

## Rate Limits

| Plan | Traces/minute | Traces/month |
|------|--------------|--------------|
| Free | 60 | 10,000 |
| Starter | 600 | 500,000 |
| Enterprise | Unlimited | Unlimited |

---

## SDK Versions

| SDK | Min Version | Package |
|-----|------------|---------|
| JavaScript | 1.0.0 | `npm install arkvoid` |
| Python | 1.0.0 | `pip install arkvoid` |
