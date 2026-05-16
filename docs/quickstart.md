# ARKVOID SDK – Quickstart Guide

Get up and running with ARKVOID in under 5 minutes.

---

## 1. Get Your API Key

1. Go to [arkvoid.cherazen.com](https://arkvoid.cherazen.com)
2. Sign up or log in
3. Navigate to **Dashboard → API Keys**
4. Click **Generate New Key**
5. Copy your key — it starts with `ARK_`

---

## 2. Register an Agent

Before sending traces, you need a registered agent:

1. Go to **Dashboard → Agents → New Agent**
2. Give it a name and a **slug** (e.g. `my-chatbot`)
3. Copy the slug — you'll use it in the SDK

---

## 3. Install the SDK

### JavaScript / TypeScript

```bash
npm install arkvoid
```

### Python

```bash
pip install arkvoid
# Or with requests for connection pooling:
pip install arkvoid[requests]
```

---

## 4. Send Your First Trace

### JavaScript

```typescript
import { ArkvoidClient } from "arkvoid";

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "my-chatbot",
});

const trace = await arkvoid.trace({
  action: "user_message_processed",
  riskLevel: "low",
  durationMs: 850,
});

console.log(trace?.traceId);  // ark_abc123...
```

### Python

```python
from arkvoid import ArkvoidClient

client = ArkvoidClient(
    api_key="ARK_your_key_here",
    agent="my-chatbot",
)

result = client.trace(
    action="user_message_processed",
    risk_level="low",
    duration_ms=850,
)

print(result.trace_id)  # ark_abc123...
```

---

## 5. View Traces in the Dashboard

Go to **Dashboard → Traces** to see your traces with:
- Cryptographic hash verification
- Risk scores and flags
- Token usage and latency
- Tool call details
- Data access logs

---

## Next Steps

- [API Reference](api-reference.md)
- [Integration Examples](examples.md)
- [Framework Integrations](integrations.md)
- [JavaScript SDK README](../sdk/javascript/README.md)
- [Python SDK README](../sdk/python/README.md)
