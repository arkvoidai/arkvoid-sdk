"""
ARKVOID SDK – Document Analysis Pipeline (Python)

Multi-stage document processing with full ARKVOID tracing:
1. Ingestion & classification
2. Chunking
3. Embedding (OpenAI)
4. LLM analysis
5. Risk flagging
6. Result storage

pip install arkvoid openai
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import OpenAI

from arkvoid import ArkvoidClient, DataAccessRecord, ToolCallRecord, trace

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

arkvoid = ArkvoidClient(
    api_key=os.environ["ARKVOID_API_KEY"],
    agent="document-pipeline",
    environment="production",
    debug=False,
)


# ─────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────

@dataclass
class Document:
    id: str
    filename: str
    content: str
    mime_type: str = "text/plain"
    size_bytes: int = 0
    classification: str = "internal"
    contains_pii: bool = False


@dataclass
class AnalysisResult:
    summary: str = ""
    key_topics: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    risk_flags: List[str] = field(default_factory=list)
    confidence: float = 0.0


# ─────────────────────────────────────────────
# Stage 1: Ingest
# ─────────────────────────────────────────────

def ingest_document(raw_content: str, filename: str) -> Document:
    lower = raw_content.lower()
    contains_pii = any(kw in lower for kw in ("ssn", "social security", "credit card", "passport"))

    doc = Document(
        id=str(uuid.uuid4()),
        filename=filename,
        content=raw_content,
        size_bytes=len(raw_content.encode("utf-8")),
        contains_pii=contains_pii,
        classification="confidential" if contains_pii else "internal",
    )

    arkvoid.trace(
        action="document_ingestion",
        risk_level="medium" if contains_pii else "low",
        input_data={"filename": filename, "size_bytes": doc.size_bytes},
        metadata={
            "document_id": doc.id,
            "filename": doc.filename,
            "size_bytes": doc.size_bytes,
            "contains_pii": doc.contains_pii,
            "classification": doc.classification,
        },
        data_access=[
            DataAccessRecord(
                data_source="upload_endpoint",
                data_classification="confidential" if contains_pii else "internal",
                contains_pii=contains_pii,
                records_accessed=1,
            )
        ],
        tags=["pipeline", "ingestion"],
    )

    return doc


# ─────────────────────────────────────────────
# Stage 2: Chunk
# ─────────────────────────────────────────────

def chunk_document(doc: Document, chunk_size: int = 1000) -> List[str]:
    chunks = [
        doc.content[i: i + chunk_size]
        for i in range(0, len(doc.content), chunk_size)
    ]

    arkvoid.trace(
        action="document_chunking",
        risk_level="low",
        metadata={
            "document_id": doc.id,
            "chunk_count": len(chunks),
            "chunk_size": chunk_size,
            "avg_chunk_size": len(doc.content) // max(len(chunks), 1),
        },
        tags=["pipeline", "chunking"],
    )

    return chunks


# ─────────────────────────────────────────────
# Stage 3: Embed
# ─────────────────────────────────────────────

def embed_chunks(doc: Document, chunks: List[str]) -> Dict[str, Any]:
    model = "text-embedding-3-small"
    start = time.time()

    response = openai_client.embeddings.create(model=model, input=chunks)
    duration_ms = int((time.time() - start) * 1000)

    embeddings = [d.embedding for d in response.data]

    arkvoid.trace(
        action="document_embedding",
        risk_level="low",
        model_provider="openai",
        model_name=model,
        input_tokens=response.usage.prompt_tokens,
        duration_ms=duration_ms,
        metadata={
            "document_id": doc.id,
            "chunk_count": len(chunks),
            "embedding_dimensions": len(embeddings[0]) if embeddings else 0,
        },
        tags=["pipeline", "embedding"],
    )

    return {"embeddings": embeddings, "model": model}


# ─────────────────────────────────────────────
# Stage 4: LLM Analysis
# ─────────────────────────────────────────────

def analyze_document(doc: Document) -> AnalysisResult:
    model = "gpt-4o"
    start = time.time()

    system_prompt = (
        "You are a document analyst. Return a JSON object with exactly these keys: "
        "summary (string), key_topics (list of strings), sentiment (string: "
        "positive/neutral/negative), risk_flags (list of strings), confidence (float 0-1)."
    )

    completion = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze:\n\n{doc.content[:8000]}"},
        ],
        response_format={"type": "json_object"},
    )
    duration_ms = int((time.time() - start) * 1000)

    raw = completion.choices[0].message.content or "{}"
    parsed = json.loads(raw)

    result = AnalysisResult(
        summary=parsed.get("summary", ""),
        key_topics=parsed.get("key_topics", []),
        sentiment=parsed.get("sentiment", "neutral"),
        risk_flags=parsed.get("risk_flags", []),
        confidence=float(parsed.get("confidence", 0.0)),
    )

    has_flags = bool(result.risk_flags)
    risk_level = "high" if has_flags and doc.contains_pii else "medium" if has_flags else "low"
    risk_score = 65 if has_flags else (30 if doc.contains_pii else 10)

    arkvoid.trace(
        action="document_analysis",
        risk_level=risk_level,
        risk_score=risk_score,
        model_provider="openai",
        model_name=model,
        input_tokens=completion.usage.prompt_tokens if completion.usage else None,
        output_tokens=completion.usage.completion_tokens if completion.usage else None,
        duration_ms=duration_ms,
        input_data=doc.content[:300],   # hash of first 300 chars
        output_data=result.__dict__,
        metadata={
            "document_id": doc.id,
            "filename": doc.filename,
            "topics": result.key_topics[:5],
            "risk_flags": result.risk_flags,
            "sentiment": result.sentiment,
            "confidence": result.confidence,
        },
        data_access=[
            DataAccessRecord(
                data_source="document_store",
                data_classification="confidential" if doc.contains_pii else "internal",
                contains_pii=doc.contains_pii,
                records_accessed=1,
            )
        ] if doc.contains_pii else None,
        tags=["pipeline", "analysis"] + (["risk-flagged"] if has_flags else []),
    )

    return result


# ─────────────────────────────────────────────
# Stage 5: Store
# ─────────────────────────────────────────────

@trace(
    agent="document-pipeline",
    action="result_storage",
    risk_level="low",
    tags=["pipeline", "storage"],
)
def store_results(doc: Document, analysis: AnalysisResult) -> bool:
    # Simulate DB write
    time.sleep(0.05)
    return True


# ─────────────────────────────────────────────
# Full pipeline
# ─────────────────────────────────────────────

def run_pipeline(raw_content: str, filename: str) -> Dict[str, Any]:
    print(f"\n📄 Processing: {filename}")

    doc = ingest_document(raw_content, filename)
    print(f"  ✅ Ingested ({doc.size_bytes} bytes, PII: {doc.contains_pii})")

    chunks = chunk_document(doc)
    print(f"  ✅ Chunked into {len(chunks)} piece(s)")

    embed_result = embed_chunks(doc, chunks)
    print(f"  ✅ Embedded ({embed_result['model']}, {len(embed_result['embeddings'])} vecs)")

    analysis = analyze_document(doc)
    print(f"  ✅ Analyzed: {analysis.summary[:80]}...")
    print(f"     Topics:     {', '.join(analysis.key_topics[:3])}")
    print(f"     Risk flags: {', '.join(analysis.risk_flags) or 'none'}")

    store_results(doc, analysis)
    print(f"  ✅ Stored")

    return {"document": doc.__dict__, "analysis": analysis.__dict__}


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

SAMPLE = """
QUARTERLY FINANCIAL REPORT – Q3 2025

Revenue grew 23% YoY to $4.2M. Operating expenses held at 68% of revenue.
Third consecutive profitable quarter.

Key Metrics:
- MRR: $1.4M  |  Customer count: 847  |  Churn: 2.1%  |  NPS: 72

Risks: EU regulatory uncertainty, single-vendor cloud dependency.
Team: 34 full-time employees across engineering, sales, operations.
"""

if __name__ == "__main__":
    print("📊 ARKVOID Document Analysis Pipeline (Python)\n")
    result = run_pipeline(SAMPLE, "Q3-2025-financial-report.txt")
    print("\n🎉 Pipeline complete — all stages traced to ARKVOID!")
