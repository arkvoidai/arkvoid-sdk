<div align="center">

# ARKVOID SDK

**AI Agent Monitoring & Governance**

[![JavaScript SDK](https://img.shields.io/npm/v/arkvoid?label=npm%20arkvoid&color=black)](https://www.npmjs.com/package/arkvoid)
[![Python SDK](https://img.shields.io/pypi/v/arkvoid?label=pypi%20arkvoid&color=black)](https://pypi.org/project/arkvoid/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Capture cryptographic audit trails for every AI agent action.  
Zero-dependency. Works with OpenAI, Anthropic, LangChain, and any framework.

**[Website](https://arkvoid.cherazen.com)** · **[Dashboard](https://arkvoid.cherazen.com/dashboard)** · **[Docs](docs/quickstart.md)**

</div>

---

## What is ARKVOID?

ARKVOID is an AI governance platform that lets you:

- **Monitor** every LLM call, tool invocation, and data access your agents make
- **Verify** cryptographic integrity hashes on all traces
- **Audit** compliance across SOC2, GDPR, and EU AI Act frameworks
- **Govern** risk levels and require human approval for high-risk actions
- **Detect** anomalies and policy violations in real time

---

## SDK Installation

### JavaScript / TypeScript

```bash
npm install arkvoid
```

```typescript
import { ArkvoidClient } from "arkvoid";

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "my-agent",
});

await arkvoid.trace({
  action: "document_analysis",
  riskLevel: "low",
  modelProvider: "openai",
  modelName: "gpt-4o",
  inputTokens: 1200,
  outputTokens: 340,
  durationMs: 1823,
});
```

### Python

```bash
pip install arkvoid
```

```python
from arkvoid import ArkvoidClient

client = ArkvoidClient(api_key="ARK_...", agent="my-agent")

client.trace(
    action="document_analysis",
    risk_level="low",
    model_provider="openai",
    model_name="gpt-4o",
    input_tokens=1200,
    output_tokens=340,
    duration_ms=1823,
)
```

---

## Zero-Boilerplate Options

### JavaScript – `logAction()`

```typescript
const result = await arkvoid.logAction(
  () => openai.chat.completions.create({ model: "gpt-4o", messages }),
  { action: "gpt4o_call", riskLevel: "low" }
);
```

### Python – `@trace` Decorator

```python
from arkvoid import trace

@trace(agent="my-agent", action="analyze_document", risk_level="low")
def analyze_document(text: str) -> str:
    return llm.complete(text)  # traced automatically — zero extra code
```

---

## Repository Structure

```
arkvoid/
│
├── sdk/
│   ├── javascript/             # npm package: arkvoid
│   │   ├── src/
│   │   │   ├── index.ts        # Main exports + functional API
│   │   │   ├── client.ts       # ArkvoidClient class
│   │   │   ├── types.ts        # TypeScript interfaces
│   │   │   ├── hash.ts         # SHA-256 utilities (Web Crypto API)
│   │   │   ├── verify.ts       # Trace verification
│   │   │   ├── retry.ts        # Exponential backoff + jitter
│   │   │   ├── http.ts         # Fetch-based HTTP client
│   │   │   ├── errors.ts       # Custom error classes
│   │   │   └── logger.ts       # Debug logger
│   │   ├── examples/
│   │   │   ├── openai-monitoring.ts
│   │   │   ├── langchain-integration.ts
│   │   │   ├── custom-agent.ts
│   │   │   ├── document-analysis.ts
│   │   │   └── tool-tracing.ts
│   │   ├── dist/               # Built output (ESM + CJS)
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── tsup.config.ts
│   │   └── README.md
│   │
│   └── python/                 # PyPI package: arkvoid
│       ├── arkvoid/
│       │   ├── __init__.py     # Public API surface
│       │   ├── client.py       # ArkvoidClient (sync)
│       │   ├── async_client.py # AsyncArkvoidClient
│       │   ├── decorators.py   # @trace, @trace_tool
│       │   ├── types.py        # Dataclasses + type aliases
│       │   ├── hash.py         # SHA-256 utilities (hashlib)
│       │   ├── errors.py       # Custom exceptions
│       │   ├── retry.py        # Retry with backoff
│       │   └── py.typed        # PEP 561 marker
│       ├── examples/
│       │   ├── openai_monitoring.py
│       │   ├── langchain_integration.py
│       │   ├── custom_agent.py
│       │   ├── document_analysis.py
│       │   └── tool_tracing.py
│       ├── pyproject.toml
│       └── README.md
│
├── docs/
│   ├── quickstart.md
│   ├── api-reference.md
│   └── integrations.md
│
├── LICENSE
├── .gitignore
└── README.md               ← you are here
```

---

## Features

| Feature | JavaScript | Python |
|---------|-----------|--------|
| Sync tracing | ✅ | ✅ |
| Async tracing | ✅ | ✅ (`AsyncArkvoidClient`) |
| Decorator / wrapper | ✅ `client.wrap()` | ✅ `@trace` |
| SHA-256 hashing | ✅ Web Crypto API | ✅ hashlib |
| Trace verification | ✅ online + offline | ✅ online + offline |
| Retry + backoff | ✅ | ✅ |
| Timeout handling | ✅ AbortSignal | ✅ |
| ESM + CommonJS | ✅ | — |
| TypeScript types | ✅ full | — |
| PEP 561 typed | — | ✅ |
| Zero dependencies | ✅ | ✅ |
| Node.js 18+ | ✅ | ✅ |
| Edge runtimes | ✅ | — |
| Tool call tracing | ✅ | ✅ |
| Data access logging | ✅ | ✅ |
| Session grouping | ✅ | ✅ |
| Parent/child traces | ✅ | ✅ |

---

## Supported Runtimes

**JavaScript SDK** works in:
- Node.js 18+
- Deno
- Bun
- Cloudflare Workers
- Vercel Edge Functions
- Any runtime with `fetch` + `crypto.subtle`

**Python SDK** works in:
- Python 3.8+
- AWS Lambda
- Google Cloud Functions
- Azure Functions
- FastAPI / Django / Flask

---

## Build from Source

### JavaScript

```bash
cd sdk/javascript
npm install
npm run build      # Outputs ESM + CJS to ./dist/
npm run typecheck
```

### Python

```bash
cd sdk/python
pip install -e ".[dev]"
pytest
mypy arkvoid/
```

---

## Publishing

### npm

```bash
cd sdk/javascript
npm run prepublishOnly   # clean + build + typecheck
npm publish              # publishes as "arkvoid"
```

### PyPI

```bash
cd sdk/python
pip install build twine
python -m build
twine upload dist/*
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run tests and type checks
5. Open a pull request

---

## License

MIT © [ARKVOID Inc.](https://arkvoid.cherazen.com)  
Built by [Manish Talukdar](https://x.com/zenithmanish) — Cherazen Inc.
