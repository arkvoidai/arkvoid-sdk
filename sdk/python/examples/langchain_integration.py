"""
ARKVOID SDK – LangChain Integration Example (Python)

Custom BaseCallbackHandler that sends every LLM call,
chain run, and tool invocation to ARKVOID automatically.

pip install arkvoid langchain langchain-openai
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool
from langchain import hub

from arkvoid import ArkvoidClient, ToolCallRecord

# ─────────────────────────────────────────────
# ARKVOID LangChain Callback Handler
# ─────────────────────────────────────────────

class ArkvoidCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that sends all LLM + tool events to ARKVOID.

    Usage:
        handler = ArkvoidCallbackHandler(client=arkvoid, agent_slug="my-agent")
        llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])
    """

    def __init__(self, client: ArkvoidClient, agent_slug: str):
        super().__init__()
        self.client = client
        self.agent_slug = agent_slug
        self._run_start: Dict[str, float] = {}
        self._pending_tools: Dict[str, List[ToolCallRecord]] = {}

    # ── LLM events ─────────────────────────────

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        self._run_start[run_key] = time.time()
        self._pending_tools[run_key] = []

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        start = self._run_start.pop(run_key, None)
        duration_ms = int((time.time() - start) * 1000) if start else None
        tool_calls = self._pending_tools.pop(run_key, [])

        llm_output = response.llm_output or {}
        model_name = (
            llm_output.get("model_name")
            or llm_output.get("model")
            or "unknown"
        )
        usage = llm_output.get("token_usage", {})

        self.client.trace(
            action="llm_call",
            risk_level="low",
            agent=self.agent_slug,
            model_provider="openai",
            model_name=model_name,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            duration_ms=duration_ms,
            tool_calls=tool_calls or None,
            metadata={
                "source": "langchain",
                "run_id": run_key,
                "generation_count": len(response.generations),
            },
            tags=["langchain", "llm"],
        )

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        start = self._run_start.pop(run_key, None)
        self._pending_tools.pop(run_key, None)

        self.client.trace(
            action="llm_error",
            risk_level="high",
            agent=self.agent_slug,
            duration_ms=int((time.time() - start) * 1000) if start else None,
            metadata={
                "source": "langchain",
                "run_id": run_key,
                "error": str(error),
                "success": False,
            },
            tags=["langchain", "error"],
        )

    # ── Tool events ─────────────────────────────

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._run_start[str(run_id)] = time.time()
        tool_name = serialized.get("name", "unknown_tool")

        if parent_run_id:
            parent_key = str(parent_run_id)
            if parent_key in self._pending_tools:
                calls = self._pending_tools[parent_key]
                calls.append(
                    ToolCallRecord(
                        tool_name=tool_name,
                        call_index=len(calls),
                        input={"query": input_str},
                        status="success",
                    )
                )

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        start = self._run_start.pop(run_key, None)
        latency_ms = int((time.time() - start) * 1000) if start else None

        if parent_run_id:
            parent_key = str(parent_run_id)
            calls = self._pending_tools.get(parent_key, [])
            if calls:
                last = calls[-1]
                last.latency_ms = latency_ms
                last.output = {"result": output[:500]}

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        start = self._run_start.pop(run_key, None)

        self.client.trace(
            action="tool_error",
            risk_level="medium",
            agent=self.agent_slug,
            duration_ms=int((time.time() - start) * 1000) if start else None,
            metadata={"error": str(error), "run_id": run_key},
            tags=["langchain", "tool", "error"],
        )


# ─────────────────────────────────────────────
# Usage
# ─────────────────────────────────────────────

arkvoid = ArkvoidClient(
    api_key=os.environ["ARKVOID_API_KEY"],
    agent="research-agent",
)

handler = ArkvoidCallbackHandler(client=arkvoid, agent_slug="research-agent")

llm = ChatOpenAI(model="gpt-4o", temperature=0, callbacks=[handler])


# ── Simple chain ─────────────────────────────

def simple_chain(prompt: str) -> str:
    """LLM call with auto-tracing via callback."""
    result = llm.invoke(prompt)
    return result.content


# ── Agent with tools ─────────────────────────

@tool
def web_search(query: str) -> str:
    """Search the web for current information."""
    # Simulated — swap with real search API
    return f"[Simulated search results for: {query}]"


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"


async def run_agent(task: str) -> str:
    """Run a LangChain agent with full ARKVOID tracing."""
    tools = [web_search, calculator]
    prompt = hub.pull("hwchase17/openai-tools-agent")

    agent = create_openai_tools_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(agent=agent, tools=tools, callbacks=[handler])

    result = await executor.ainvoke({"input": task})
    return result["output"]


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    print("🔗 ARKVOID LangChain Integration (Python)\n")

    answer = simple_chain("What is the difference between RAG and fine-tuning?")
    print(f"Answer: {answer[:150]}...\n")

    result = asyncio.run(run_agent("Calculate 15% of 8500 and search for AI safety news"))
    print(f"Agent: {result[:200]}")
