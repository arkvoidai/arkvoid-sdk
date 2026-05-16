"""
ARKVOID SDK â€“ OpenAI API Monitoring Example (Python)

Every OpenAI call is traced to ARKVOID with model, tokens,
latency, and cryptographically hashed inputs/outputs.

pip install arkvoid openai
"""

import os
import time
from typing import Optional

from openai import OpenAI

from arkvoid import ArkvoidClient, trace, ToolCallRecord

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Setup
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

arkvoid = ArkvoidClient(
    api_key=os.environ["ARKVOID_API_KEY"],
    agent="gpt4-support-bot",
    environment="production",
)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Example 1: Manual trace around OpenAI call
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def tracked_chat_completion(user_message: str) -> Optional[str]:
    model = "gpt-4o"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": user_message},
    ]

    start = time.time()
    completion = openai_client.chat.completions.create(model=model, messages=messages)
    duration_ms = int((time.time() - start) * 1000)

    content = completion.choices[0].message.content or ""

    result = arkvoid.trace(
        action="chat_completion",
        risk_level="low",
        model_provider="openai",
        model_name=model,
        input_tokens=completion.usage.prompt_tokens if completion.usage else None,
        output_tokens=completion.usage.completion_tokens if completion.usage else None,
        duration_ms=duration_ms,
        input_data=messages,       # SHA-256 hashed, not stored raw
        output_data=content,       # SHA-256 hashed, not stored raw
        metadata={
            "prompt_id": "support-v1",
            "user_id": "user_demo",
            "finish_reason": completion.choices[0].finish_reason,
        },
        tags=["chat", "support"],
    )

    print(f"âœ… Trace: {result.trace_id if result else 'failed'}")
    return content


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Example 2: @trace decorator (zero-boilerplate)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@trace(
    agent="gpt4-support-bot",
    action="document_analysis",
    risk_level="low",
    model_provider="openai",
    model_name="gpt-4o-mini",
    tags=["analysis"],
)
def analyze_document(text: str) -> str:
    """Analyze a document â€” traced automatically with zero extra code."""
    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Extract key insights from the document."},
            {"role": "user", "content": text},
        ],
    )
    return completion.choices[0].message.content or ""


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Example 3: log_action() â€“ run + trace in one call
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_with_auto_trace(prompt: str) -> Optional[str]:
    result = arkvoid.log_action(
        lambda: openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        ),
        action="user_query",
        risk_level="low",
        model_provider="openai",
        model_name="gpt-4o",
        metadata={"source": "api"},
    )
    return result.choices[0].message.content if result else None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Example 4: High-risk action with data access
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def financial_analysis(prompt: str, user_id: str) -> Optional[str]:
    from arkvoid import DataAccessRecord

    start = time.time()
    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You have access to sensitive financial data."},
            {"role": "user", "content": prompt},
        ],
    )
    duration_ms = int((time.time() - start) * 1000)

    arkvoid.trace(
        action="financial_analysis",
        risk_level="high",
        risk_score=72,
        required_human_approval=True,
        model_provider="openai",
        model_name="gpt-4o",
        duration_ms=duration_ms,
        input_data=prompt,
        metadata={
            "user_id": user_id,
            "data_classification": "confidential",
        },
        data_access=[
            DataAccessRecord(
                data_source="financial_records_db",
                data_classification="confidential",
                contains_pii=True,
                records_accessed=1,
            )
        ],
        tags=["financial", "high-risk"],
    )

    return completion.choices[0].message.content


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Example 5: Tool-calling trace
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def run_with_tools(user_query: str) -> str:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        }
    ]

    start = time.time()
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": user_query}],
        tools=tools,
    )
    duration_ms = int((time.time() - start) * 1000)

    tool_calls_recorded: list[ToolCallRecord] = []
    for tc in (response.choices[0].message.tool_calls or []):
        tool_calls_recorded.append(
            ToolCallRecord(
                tool_name=tc.function.name,
                call_index=len(tool_calls_recorded),
                input={"raw_args": tc.function.arguments},
                status="success",
            )
        )

    arkvoid.trace(
        action="tool_assisted_query",
        risk_level="low",
        model_provider="openai",
        model_name="gpt-4o",
        input_tokens=response.usage.prompt_tokens if response.usage else None,
        output_tokens=response.usage.completion_tokens if response.usage else None,
        duration_ms=duration_ms,
        tool_calls=tool_calls_recorded,
        metadata={"tool_count": len(tool_calls_recorded)},
        tags=["tool-calling"],
    )

    return response.choices[0].message.content or ""


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Run
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

if __name__ == "__main__":
    print("ðŸ“¡ ARKVOID OpenAI Monitoring Example (Python)\n")

    answer = tracked_chat_completion("What is quantum computing?")
    print(f"Answer: {(answer or '')[:100]}...\n")

    analysis = analyze_document(
        "Photosynthesis converts sunlight to chemical energy in plants..."
    )
    print(f"Analysis: {analysis[:100]}...\n")

    print("âœ… All traces sent to ARKVOID!")
                       
