"""
ARKVOID SDK – Tool Execution Tracing (Python)

Demonstrates granular tool tracing using:
- @trace_tool decorator
- ToolCallRecord batching
- Risk-level escalation on tool errors
- Multi-tool workflow aggregation

pip install arkvoid
"""

import os
import random
import time
from typing import Any, Dict, List, Optional

from arkvoid import ArkvoidClient, ToolCallRecord, DataAccessRecord, trace_tool

# ─────────────────────────────────────────────
# Client
# ─────────────────────────────────────────────

arkvoid = ArkvoidClient(
    api_key=os.environ["ARKVOID_API_KEY"],
    agent="tool-agent",
    environment="production",
)


# ─────────────────────────────────────────────
# Tools via @trace_tool decorator
# ─────────────────────────────────────────────

@trace_tool(agent="tool-agent", tool_name="web_search", external_system="serpapi", risk_level="low")
def web_search(query: str) -> Dict[str, Any]:
    """Search the web. Auto-traced via @trace_tool."""
    time.sleep(random.uniform(0.1, 0.4))
    return {
        "results": [
            {"title": f"Result 1 for '{query}'", "url": "https://example.com/1"},
            {"title": f"Result 2 for '{query}'", "url": "https://example.com/2"},
        ],
        "total": 1_240_000,
    }


@trace_tool(agent="tool-agent", tool_name="calculator", risk_level="low")
def calculator(expression: str) -> Dict[str, Any]:
    """Safe math evaluation. Auto-traced via @trace_tool."""
    time.sleep(0.02)
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return {"result": result, "expression": expression}
    except Exception as e:
        raise ValueError(f"Cannot evaluate: {expression} → {e}") from e


@trace_tool(agent="tool-agent", tool_name="database_query", external_system="postgres_prod", risk_level="medium")
def database_query(sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Query the database. Auto-traced via @trace_tool."""
    time.sleep(random.uniform(0.05, 0.2))
    if any(kw in sql.lower() for kw in ("drop", "delete", "truncate", "--")):
        raise PermissionError("Destructive SQL blocked by governance policy")
    return {
        "rows": [{"id": 1, "value": "alpha"}, {"id": 2, "value": "beta"}],
        "row_count": 2,
        "query_time_ms": 48,
    }


@trace_tool(agent="tool-agent", tool_name="send_email", external_system="sendgrid", risk_level="medium")
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Send email via external service. Auto-traced."""
    time.sleep(0.15)
    return {"message_id": f"msg_{int(time.time())}", "status": "sent", "to": to}


@trace_tool(agent="tool-agent", tool_name="file_read", external_system="s3", risk_level="medium")
def read_file(path: str) -> Dict[str, Any]:
    """Read a file from S3. Auto-traced."""
    time.sleep(0.1)
    if "restricted" in path:
        raise PermissionError(f"Access denied: {path} is classified as restricted")
    return {"path": path, "content": f"[Contents of {path}]", "size_bytes": 4096}


# ─────────────────────────────────────────────
# Manual batch tracing (multiple tools → 1 trace)
# ─────────────────────────────────────────────

def run_research_workflow(topic: str) -> Dict[str, Any]:
    """Execute a multi-tool research workflow and record as a single trace."""
    tool_calls_recorded: List[ToolCallRecord] = []
    workflow_start = time.time()

    print(f"\n🔍 Research workflow: '{topic}'")

    # Tool 1: web search
    t = time.time()
    search1 = web_search(f"{topic} overview")
    tool_calls_recorded.append(ToolCallRecord(
        tool_name="web_search", call_index=0,
        input={"query": f"{topic} overview"},
        output={"result_count": len(search1.get("results", []))},
        latency_ms=int((time.time() - t) * 1000), status="success",
    ))

    # Tool 2: second search
    t = time.time()
    search2 = web_search(f"{topic} best practices 2025")
    tool_calls_recorded.append(ToolCallRecord(
        tool_name="web_search", call_index=1,
        input={"query": f"{topic} best practices 2025"},
        output={"result_count": len(search2.get("results", []))},
        latency_ms=int((time.time() - t) * 1000), status="success",
    ))

    # Tool 3: DB lookup
    t = time.time()
    db_result = database_query("SELECT * FROM knowledge_base WHERE topic = %s LIMIT 5", [topic])
    tool_calls_recorded.append(ToolCallRecord(
        tool_name="database_query", call_index=2,
        input={"table": "knowledge_base", "topic": topic},
        output={"row_count": db_result.get("row_count", 0)},
        external_system="postgres_prod",
        latency_ms=int((time.time() - t) * 1000), status="success",
    ))

    # Single aggregated trace for the whole workflow
    trace_result = arkvoid.trace(
        action="research_workflow",
        risk_level="low",
        duration_ms=int((time.time() - workflow_start) * 1000),
        tool_calls=tool_calls_recorded,
        metadata={
            "topic": topic,
            "tools_used": list({tc.tool_name for tc in tool_calls_recorded}),
            "total_tool_calls": len(tool_calls_recorded),
        },
        tags=["research", "multi-tool"],
    )

    print(f"  ✅ Workflow trace: {trace_result.trace_id if trace_result else '–'}")
    return {"search": search1, "db": db_result}


# ─────────────────────────────────────────────
# High-risk blocked operation
# ─────────────────────────────────────────────

def run_risky_operation():
    print("\n⚠️  Attempting risky DB operation...")
    start = time.time()
    try:
        database_query("DROP TABLE users --")
    except PermissionError as e:
        # Log the block as a critical trace
        arkvoid.trace(
            action="dangerous_query_blocked",
            risk_level="critical",
            risk_score=98,
            duration_ms=int((time.time() - start) * 1000),
            metadata={
                "reason": str(e),
                "blocked_by": "arkvoid_governance",
            },
            tags=["security", "blocked", "sql-injection"],
        )
        print(f"  🚫 Blocked & traced: {e}")


# ─────────────────────────────────────────────
# Parallel tool execution
# ─────────────────────────────────────────────

def run_parallel_tools():
    import threading

    print("\n⚡ Parallel tool execution...")
    results: Dict[str, Any] = {}

    def run_search(q: str):
        results[f"search_{q[:10]}"] = web_search(q)

    threads = [
        threading.Thread(target=run_search, args=(f"AI governance topic {i}",))
        for i in range(3)
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]

    arkvoid.trace(
        action="parallel_search",
        risk_level="low",
        metadata={"parallel_count": 3, "results_count": len(results)},
        tags=["parallel", "search"],
    )
    print(f"  ✅ {len(results)} parallel searches traced")


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🔧 ARKVOID Tool Execution Tracing (Python)\n")

    # Multi-tool workflow
    run_research_workflow("AI agent governance")

    # High-risk block
    run_risky_operation()

    # Parallel tools
    run_parallel_tools()

    # Single tool with data access
    print("\n📨 Sending email...")
    result = send_email(
        to="analyst@company.com",
        subject="Research Report Ready",
        body="Your AI governance report has been generated.",
    )
    print(f"  ✅ Email sent: {result.get('message_id')}")

    print("\n🎉 All tool traces sent to ARKVOID!")
