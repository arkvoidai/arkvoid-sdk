"""
ARKVOID SDK – Custom Async AI Agent (Python)

Demonstrates tracing a multi-step agent with:
- AsyncArkvoidClient
- Session grouping
- Parent/child trace chains
- Tool call recording
- Risk escalation on failure

pip install arkvoid openai aiohttp
"""

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from arkvoid import AsyncArkvoidClient, ToolCallRecord

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_result",
            "description": "Persist a result to the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
        },
    },
]


# ─────────────────────────────────────────────
# Simulated tool execution
# ─────────────────────────────────────────────

async def execute_tool(name: str, args: Dict[str, str]) -> Dict[str, Any]:
    await asyncio.sleep(0.1)  # simulate latency
    if name == "web_search":
        return {"results": [f"Result about: {args.get('query', '')}"], "count": 3}
    elif name == "calculate":
        try:
            return {"result": eval(args.get("expression", "0"), {"__builtins__": {}}, {})}
        except Exception as e:
            return {"error": str(e)}
    elif name == "save_result":
        return {"saved": True, "key": args.get("key"), "timestamp": time.time()}
    return {"error": "Unknown tool"}


# ─────────────────────────────────────────────
# Agent loop
# ─────────────────────────────────────────────

async def run_agent(
    task: str,
    user_id: str,
    arkvoid: AsyncArkvoidClient,
    max_iterations: int = 6,
) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    model = "gpt-4o"

    print(f"\n🤖 Session: {session_id}")
    print(f"📋 Task: {task}\n")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "You are a capable research assistant. Use tools to answer thoroughly."},
        {"role": "user", "content": task},
    ]

    parent_trace_id: Optional[str] = None
    iteration = 0
    final_answer: Optional[str] = None

    for iteration in range(1, max_iterations + 1):
        iter_start = time.time()
        tool_calls_this_iter: List[ToolCallRecord] = []

        print(f"  → Iteration {iteration}")

        response = await openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_unset=True))

        # Agent finished
        if not message.tool_calls:
            final_answer = message.content or ""
            trace = await arkvoid.trace(
                action="agent_final_answer",
                risk_level="low",
                session_id=session_id,
                parent_trace_id=parent_trace_id,
                model_provider="openai",
                model_name=model,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                duration_ms=int((time.time() - iter_start) * 1000),
                output_data=final_answer,
                metadata={"user_id": user_id, "iteration": iteration},
                tags=["agent", "final"],
            )
            print(f"  ✅ Done → trace: {trace.trace_id if trace else '–'}")
            break

        # Execute tool calls
        for tc in message.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)
            tool_start = time.time()

            risk_level = "medium" if tool_name == "save_result" else "low"
            result = await execute_tool(tool_name, tool_args)
            tool_latency = int((time.time() - tool_start) * 1000)

            tool_calls_this_iter.append(
                ToolCallRecord(
                    tool_name=tool_name,
                    call_index=len(tool_calls_this_iter),
                    input=tool_args,
                    output=result,
                    latency_ms=tool_latency,
                    status="error" if "error" in result else "success",
                )
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

            print(f"     🔧 {tool_name} → {str(result)[:60]}")

        # Trace this iteration
        trace = await arkvoid.trace(
            action=f"agent_iteration_{iteration}",
            risk_level="low",
            session_id=session_id,
            parent_trace_id=parent_trace_id,
            model_provider="openai",
            model_name=model,
            input_tokens=response.usage.prompt_tokens if response.usage else None,
            output_tokens=response.usage.completion_tokens if response.usage else None,
            duration_ms=int((time.time() - iter_start) * 1000),
            tool_calls=tool_calls_this_iter,
            metadata={
                "user_id": user_id,
                "iteration": iteration,
                "tool_count": len(tool_calls_this_iter),
            },
            tags=["agent", "iteration"],
        )

        if not parent_trace_id and trace:
            parent_trace_id = trace.trace_id

    return {
        "session_id": session_id,
        "final_answer": final_answer,
        "iterations": iteration,
        "parent_trace_id": parent_trace_id,
    }


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

async def main():
    print("🤖 ARKVOID Custom Async Agent (Python)\n")

    async with AsyncArkvoidClient(
        api_key=os.environ["ARKVOID_API_KEY"],
        agent="research-agent",
        debug=True,
    ) as arkvoid:
        result = await run_agent(
            task="What is 25% of 12,400? Also find recent news about AI regulation.",
            user_id="user_demo_001",
            arkvoid=arkvoid,
        )

    print(f"\n────────────────────────────────────")
    print(f"Session:    {result['session_id']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Root trace: {result['parent_trace_id']}")
    if result["final_answer"]:
        print(f"Answer:     {result['final_answer'][:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
