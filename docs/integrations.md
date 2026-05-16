# ARKVOID SDK – Integration Guide

How to integrate ARKVOID with popular AI frameworks and providers.

---

## OpenAI

### Python – Manual trace

```python
import time
from openai import OpenAI
from arkvoid import ArkvoidClient

openai = OpenAI()
arkvoid = ArkvoidClient(api_key="ARK_...", agent="my-bot")

def chat(prompt: str) -> str:
    start = time.time()
    completion = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    arkvoid.trace(
        action="chat_completion",
        risk_level="low",
        model_provider="openai",
        model_name="gpt-4o",
        input_tokens=completion.usage.prompt_tokens,
        output_tokens=completion.usage.completion_tokens,
        duration_ms=int((time.time() - start) * 1000),
    )
    return completion.choices[0].message.content
```

### Python – Decorator

```python
from arkvoid import trace

@trace(agent="my-bot", model_provider="openai", model_name="gpt-4o-mini")
def analyze(text: str) -> str:
    return openai.chat.completions.create(...).choices[0].message.content
```

### JavaScript – Wrapper

```typescript
const tracedAnalyze = arkvoid.wrap(analyzeWithOpenAI, {
  action: "openai_analysis",
  riskLevel: "low",
});
```

---

## Anthropic / Claude

```python
import anthropic
from arkvoid import ArkvoidClient
import time

client = anthropic.Anthropic()
arkvoid = ArkvoidClient(api_key="ARK_...", agent="claude-agent")

def ask_claude(prompt: str) -> str:
    start = time.time()
    msg = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    arkvoid.trace(
        action="anthropic_completion",
        risk_level="low",
        model_provider="anthropic",
        model_name="claude-3-5-sonnet-20241022",
        input_tokens=msg.usage.input_tokens,
        output_tokens=msg.usage.output_tokens,
        duration_ms=int((time.time() - start) * 1000),
    )
    return msg.content[0].text
```

---

## LangChain (Python)

See the full example at [examples/langchain_integration.py](../sdk/python/examples/langchain_integration.py).

```python
from arkvoid import ArkvoidClient
from langchain_openai import ChatOpenAI
# Use ArkvoidCallbackHandler from examples/langchain_integration.py

arkvoid = ArkvoidClient(api_key="ARK_...", agent="lc-agent")
handler = ArkvoidCallbackHandler(client=arkvoid, agent_slug="lc-agent")
llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])
```

---

## LangChain (JavaScript)

See [examples/langchain-integration.ts](../sdk/javascript/examples/langchain-integration.ts).

```typescript
import { ArkvoidLangChainHandler } from "./examples/langchain-integration";

const handler = new ArkvoidLangChainHandler(arkvoid, "lc-agent");
const llm = new ChatOpenAI({ model: "gpt-4o", callbacks: [handler] });
```

---

## Next.js

### App Router (Edge-compatible)

```typescript
// app/api/chat/route.ts
import { ArkvoidClient } from "arkvoid";
import { NextRequest, NextResponse } from "next/server";

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "nextjs-chatbot",
  silent: true,
});

export async function POST(req: NextRequest) {
  const { message } = await req.json();
  const start = Date.now();

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "gpt-4o", messages: [{ role: "user", content: message }] }),
  });

  const data = await response.json();

  // Fire-and-forget: don't await
  void arkvoid.trace({
    action: "chat_api",
    riskLevel: "low",
    durationMs: Date.now() - start,
    metadata: { path: "/api/chat" },
  });

  return NextResponse.json({ answer: data.choices[0].message.content });
}
```

---

## Vercel AI SDK

```typescript
import { streamText } from "ai";
import { openai } from "@ai-sdk/openai";
import { ArkvoidClient } from "arkvoid";

const arkvoid = new ArkvoidClient({ apiKey: process.env.ARKVOID_API_KEY!, agent: "ai-sdk-bot" });

export async function generateAnswer(prompt: string) {
  const start = Date.now();
  const result = await streamText({
    model: openai("gpt-4o"),
    prompt,
    onFinish: ({ usage }) => {
      void arkvoid.trace({
        action: "stream_completion",
        riskLevel: "low",
        modelProvider: "openai",
        modelName: "gpt-4o",
        inputTokens: usage.promptTokens,
        outputTokens: usage.completionTokens,
        durationMs: Date.now() - start,
      });
    },
  });
  return result;
}
```

---

## AWS Lambda

```python
# lambda_function.py
import json
import os
from arkvoid import ArkvoidClient
import time

# Initialize outside handler for connection reuse
arkvoid = ArkvoidClient(
    api_key=os.environ["ARKVOID_API_KEY"],
    agent="lambda-agent",
    silent=True,  # Never block Lambda on SDK errors
)

def handler(event, context):
    start = time.time()
    # ... your AI logic ...
    result = {"answer": "42"}

    arkvoid.trace(
        action="lambda_invocation",
        risk_level="low",
        duration_ms=int((time.time() - start) * 1000),
        metadata={
            "function_name": context.function_name,
            "request_id": context.aws_request_id,
        },
    )
    return {"statusCode": 200, "body": json.dumps(result)}
```

---

## FastAPI

```python
from fastapi import FastAPI, Request
from arkvoid import ArkvoidClient
import time

app = FastAPI()
arkvoid = ArkvoidClient(api_key="ARK_...", agent="fastapi-agent")

@app.middleware("http")
async def trace_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    
    if request.url.path.startswith("/api/ai"):
        arkvoid.trace(
            action=f"http_{request.method.lower()}",
            risk_level="low",
            duration_ms=int((time.time() - start) * 1000),
            metadata={
                "path": str(request.url.path),
                "status_code": response.status_code,
            },
        )
    return response
```

---

## Cloudflare Workers

```typescript
import { ArkvoidClient } from "arkvoid";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const arkvoid = new ArkvoidClient({
      apiKey: env.ARKVOID_API_KEY,
      agent: "cf-worker",
      silent: true,
    });

    const start = Date.now();
    // ... AI logic ...
    const result = { answer: "42" };

    // Non-blocking trace
    void arkvoid.trace({
      action: "worker_request",
      riskLevel: "low",
      durationMs: Date.now() - start,
    });

    return Response.json(result);
  },
};
```
