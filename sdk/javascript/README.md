# ARKVOID JavaScript SDK

[![npm version](https://img.shields.io/npm/v/arkvoid.svg)](https://www.npmjs.com/package/arkvoid)
[![npm downloads](https://img.shields.io/npm/dm/arkvoid.svg)](https://www.npmjs.com/package/arkvoid)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-Ready-blue.svg)](https://www.typescriptlang.org/)

Official JavaScript/TypeScript SDK for **ARKVOID** — AI Agent Monitoring & Governance.

Capture cryptographic audit trails for every AI action. Zero external dependencies.

---

## Installation

```bash
npm install arkvoid
# or
yarn add arkvoid
# or
pnpm add arkvoid
```

**Requirements**: Node.js 18+, Bun, Deno, or any modern Edge runtime.

---

## Quick Start

```typescript
import { ArkvoidClient } from "arkvoid";

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!, // starts with ARK_
  agent: "my-agent",                    // register at arkvoid.cherazen.com
});

const trace = await arkvoid.trace({
  action: "document_analysis",
  riskLevel: "low",
  modelProvider: "openai",
  modelName: "gpt-4o",
  inputTokens: 1200,
  outputTokens: 340,
  durationMs: 1823,
});

console.log(trace?.traceId); // ark_a1b2c3d4...
console.log(trace?.hash);    // sha256:...
```

Get your API key at [arkvoid.cherazen.com](https://arkvoid.cherazen.com/dashboard/api-keys).

---

## API Reference

### `new ArkvoidClient(options)`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `apiKey` | `string` | **required** | Your ARKVOID API key (`ARK_...`) |
| `agent` | `string` | — | Default agent slug |
| `silent` | `boolean` | `false` | Suppress all errors (fire-and-forget) |
| `environment` | `string` | `"production"` | `"production"` \| `"staging"` \| `"development"` \| `"test"` |
| `timeout` | `number` | `10000` | Request timeout in ms |
| `maxRetries` | `number` | `3` | Max retry attempts on transient failures |
| `baseUrl` | `string` | — | Override the API base URL |
| `debug` | `boolean` | `false` | Enable verbose debug logging |

---

### `client.trace(options)`

Send an AI action trace.

```typescript
const trace = await arkvoid.trace({
  action: "chat_completion",         // required: what the agent did
  riskLevel: "low",                  // "low" | "medium" | "high" | "critical"
  agent: "my-agent",                 // override default agent
  riskScore: 12,                     // 0–100 numeric score
  modelProvider: "openai",
  modelName: "gpt-4o",
  inputTokens: 850,
  outputTokens: 210,
  durationMs: 1423,
  inputData: messages,               // SHA-256 hashed automatically (not stored raw)
  outputData: response,              // SHA-256 hashed automatically
  sessionId: "sess_abc",
  parentTraceId: "ark_xyz",
  toolCalls: [
    {
      toolName: "web_search",
      input: { query: "AI governance" },
      output: { resultCount: 10 },
      latencyMs: 340,
      status: "success",
    },
  ],
  dataAccess: [
    {
      dataSource: "user_database",
      dataClassification: "confidential",
      containsPii: true,
      recordsAccessed: 1,
    },
  ],
  metadata: { userId: "u_123", region: "us-east-1" },
  tags: ["chat", "support"],
});
```

Returns `TraceResponse | null`:

```typescript
{
  traceId: "ark_a1b2c3d4e5f6...",
  timestamp: "2025-01-15T10:23:45.123Z",
  status: "verified",
  hash: "sha256:a3f1b2..."
}
```

---

### `client.logAction(fn, options)`

Execute a function and automatically trace it.

```typescript
const result = await arkvoid.logAction(
  () => openai.chat.completions.create({ model: "gpt-4o", messages }),
  {
    action: "gpt4o_completion",
    riskLevel: "low",
    modelProvider: "openai",
    modelName: "gpt-4o",
    metadata: { userId: "u_123" },
  }
);
```

Traces success/failure, duration, and error details automatically.

---

### `client.wrap(fn, options)`

Permanently wrap a function to trace every call.

```typescript
async function searchDocuments(query: string) {
  // your logic
}

const tracedSearch = arkvoid.wrap(searchDocuments, {
  action: "document_search",
  riskLevel: "low",
});

// Use exactly like the original:
const results = await tracedSearch("quantum computing");
```

---

### `client.verify(options)`

Verify a trace exists and its hash is valid.

```typescript
const result = await arkvoid.verify({
  traceId: "ark_a1b2c3...",
  expectedHash: "sha256:...", // optional: compare against expected
});

console.log(result.valid);           // true
console.log(result.hash);            // sha256:...
console.log(result.matchesExpected); // true (if expectedHash provided)
```

---

### Functional API (module-level)

For simpler setups:

```typescript
import { configure, trace, verify, logAction } from "arkvoid";

configure({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "my-agent",
});

// Then use directly:
await trace({ action: "user_query", riskLevel: "low" });
```

---

## OpenAI Integration

```typescript
import OpenAI from "openai";
import { ArkvoidClient } from "arkvoid";

const openai = new OpenAI();
const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "gpt4-agent",
});

async function chat(prompt: string) {
  const start = Date.now();

  const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: prompt }],
  });

  await arkvoid.trace({
    action: "chat_completion",
    riskLevel: "low",
    modelProvider: "openai",
    modelName: "gpt-4o",
    inputTokens: completion.usage?.prompt_tokens,
    outputTokens: completion.usage?.completion_tokens,
    durationMs: Date.now() - start,
  });

  return completion.choices[0]?.message.content;
}
```

---

## Hash Utilities

```typescript
import { sha256, hashValue, verifyTraceLocally, isValidTraceId } from "arkvoid";

// Hash any value
const { hex, prefixed } = await hashValue({ prompt: "hello", model: "gpt-4o" });
// prefixed = "sha256:a3f1b2..."

// Verify a trace locally (no network call)
const valid = await verifyTraceLocally({
  agentId: "uuid-of-agent",
  action: "document_analysis",
  timestamp: "2025-01-15T10:23:45.123Z",
  hash: "sha256:...",
});

// Validate IDs
isValidTraceId("ark_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"); // true
```

---

## Error Handling

```typescript
import {
  ArkvoidClient,
  ArkvoidAuthError,
  ArkvoidNotFoundError,
  ArkvoidRateLimitError,
  ArkvoidTimeoutError,
} from "arkvoid";

try {
  await arkvoid.trace({ action: "...", riskLevel: "low" });
} catch (e) {
  if (e instanceof ArkvoidAuthError) {
    console.error("Invalid API key");
  } else if (e instanceof ArkvoidNotFoundError) {
    console.error("Agent not registered at arkvoid.cherazen.com");
  } else if (e instanceof ArkvoidRateLimitError) {
    console.error(`Rate limited. Retry after ${e.retryAfterMs}ms`);
  } else if (e instanceof ArkvoidTimeoutError) {
    console.error("Request timed out");
  }
}
```

### Silent Mode (fire-and-forget)

```typescript
const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  silent: true, // Never throws. Returns null on failure.
});

// Will not throw even if API is down
const trace = await arkvoid.trace({ action: "query", riskLevel: "low" });
// trace === null if request failed
```

---

## ESM & CommonJS

The SDK ships dual ESM + CJS bundles and works in both module systems:

```javascript
// ESM
import { ArkvoidClient } from "arkvoid";

// CommonJS
const { ArkvoidClient } = require("arkvoid");
```

---

## Serverless & Edge Runtimes

Works out-of-the-box in:

- **Vercel Edge Functions**
- **Cloudflare Workers**
- **AWS Lambda** (Node.js 18+)
- **Deno Deploy**
- **Bun**
- **Next.js** (App Router & Pages)

No native modules. Uses only Web APIs (`fetch`, `crypto.subtle`).

---

## Environment Variables

```bash
ARKVOID_API_KEY=ARK_your_key_here
ARKVOID_AGENT=my-agent
ARKVOID_ENV=production
```

---

## Build from Source

```bash
git clone https://github.com/arkvoidai/arkvoid.git
cd arkvoid/sdk/javascript
npm install
npm run build       # Outputs to ./dist/
npm run typecheck   # Type-check only
```

---

## License

MIT © [ARKVOID Inc.](https://arkvoid.cherazen.com)
