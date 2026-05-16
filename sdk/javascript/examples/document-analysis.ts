/**
 * ARKVOID SDK – Document Analysis Pipeline Example
 *
 * Traces a multi-stage document processing pipeline:
 * 1. Ingestion
 * 2. Chunking
 * 3. Embedding
 * 4. LLM Analysis
 * 5. Result storage
 *
 * npm install arkvoid openai
 */

import { randomUUID } from "node:crypto";
import OpenAI from "openai";
import { ArkvoidClient } from "arkvoid";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "document-pipeline",
  environment: "production",
});

// ─────────────────────────────────────────────
// Pipeline Stages
// ─────────────────────────────────────────────

interface Document {
  id: string;
  filename: string;
  content: string;
  mimeType: string;
  sizeBytes: number;
  classification: "public" | "internal" | "confidential" | "restricted";
  containsPii: boolean;
}

interface AnalysisResult {
  summary: string;
  keyTopics: string[];
  sentiment: string;
  riskFlags: string[];
  confidence: number;
}

// Stage 1: Ingest & validate document
async function ingestDocument(
  rawContent: string,
  filename: string
): Promise<Document> {
  const doc: Document = {
    id: randomUUID(),
    filename,
    content: rawContent,
    mimeType: "text/plain",
    sizeBytes: Buffer.byteLength(rawContent, "utf8"),
    classification: "internal",
    containsPii: rawContent.toLowerCase().includes("ssn") ||
      rawContent.toLowerCase().includes("social security"),
  };

  await arkvoid.trace({
    action: "document_ingestion",
    riskLevel: doc.containsPii ? "medium" : "low",
    inputData: { filename, sizeBytes: doc.sizeBytes },
    metadata: {
      documentId: doc.id,
      filename: doc.filename,
      sizeBytes: doc.sizeBytes,
      mimeType: doc.mimeType,
      containsPii: doc.containsPii,
      classification: doc.classification,
    },
    dataAccess: [
      {
        dataSource: "upload_endpoint",
        dataClassification: doc.classification,
        containsPii: doc.containsPii,
        recordsAccessed: 1,
      },
    ],
    tags: ["pipeline", "ingestion"],
  });

  return doc;
}

// Stage 2: Chunk document
async function chunkDocument(
  doc: Document
): Promise<{ chunks: string[]; count: number }> {
  const CHUNK_SIZE = 1000;
  const chunks: string[] = [];

  for (let i = 0; i < doc.content.length; i += CHUNK_SIZE) {
    chunks.push(doc.content.slice(i, i + CHUNK_SIZE));
  }

  await arkvoid.trace({
    action: "document_chunking",
    riskLevel: "low",
    metadata: {
      documentId: doc.id,
      chunkCount: chunks.length,
      avgChunkSize: Math.round(doc.content.length / chunks.length),
    },
    tags: ["pipeline", "chunking"],
  });

  return { chunks, count: chunks.length };
}

// Stage 3: Generate embeddings
async function embedChunks(
  doc: Document,
  chunks: string[]
): Promise<{ embeddings: number[][]; model: string }> {
  const start = Date.now();
  const embeddingModel = "text-embedding-3-small";

  const response = await openai.embeddings.create({
    model: embeddingModel,
    input: chunks,
  });

  const embeddings = response.data.map((d) => d.embedding);
  const durationMs = Date.now() - start;

  await arkvoid.trace({
    action: "document_embedding",
    riskLevel: "low",
    modelProvider: "openai",
    modelName: embeddingModel,
    inputTokens: response.usage.prompt_tokens,
    durationMs,
    metadata: {
      documentId: doc.id,
      chunkCount: chunks.length,
      embeddingDimensions: embeddings[0]?.length ?? 1536,
    },
    tags: ["pipeline", "embedding"],
  });

  return { embeddings, model: embeddingModel };
}

// Stage 4: LLM analysis
async function analyzeDocument(
  doc: Document
): Promise<AnalysisResult> {
  const start = Date.now();
  const model = "gpt-4o";

  const systemPrompt = `You are a document analyst. Analyze the document and return a JSON object with:
- summary (string): 2-3 sentence summary
- keyTopics (array of strings): top 5 topics
- sentiment (string): positive/neutral/negative
- riskFlags (array of strings): compliance or data risks
- confidence (number): 0-1 confidence score`;

  const completion = await openai.chat.completions.create({
    model,
    messages: [
      { role: "system", content: systemPrompt },
      {
        role: "user",
        content: `Analyze this document:\n\n${doc.content.slice(0, 8000)}`,
      },
    ],
    response_format: { type: "json_object" },
  });

  const durationMs = Date.now() - start;
  const raw = completion.choices[0]?.message.content ?? "{}";
  const result = JSON.parse(raw) as AnalysisResult;

  // Determine risk level based on analysis
  const hasRiskFlags = result.riskFlags.length > 0;
  const riskLevel = hasRiskFlags
    ? "medium"
    : doc.containsPii
      ? "medium"
      : "low";

  await arkvoid.trace({
    action: "document_analysis",
    riskLevel,
    riskScore: hasRiskFlags ? 45 : doc.containsPii ? 30 : 10,
    modelProvider: "openai",
    modelName: model,
    inputTokens: completion.usage?.prompt_tokens,
    outputTokens: completion.usage?.completion_tokens,
    durationMs,
    inputData: doc.content.slice(0, 500), // hash only first 500 chars
    outputData: result,
    metadata: {
      documentId: doc.id,
      filename: doc.filename,
      topicsFound: result.keyTopics,
      riskFlagsFound: result.riskFlags,
      sentiment: result.sentiment,
      confidence: result.confidence,
    },
    dataAccess: doc.containsPii
      ? [
          {
            dataSource: "document_store",
            dataClassification: "confidential",
            containsPii: true,
            recordsAccessed: 1,
          },
        ]
      : undefined,
    tags: ["pipeline", "analysis", ...(hasRiskFlags ? ["risk-flagged"] : [])],
  });

  return result;
}

// Stage 5: Store results
async function storeResults(
  doc: Document,
  analysis: AnalysisResult
): Promise<void> {
  // Simulate DB write
  await new Promise((r) => setTimeout(r, 50));

  await arkvoid.trace({
    action: "result_storage",
    riskLevel: "low",
    metadata: {
      documentId: doc.id,
      storedAt: new Date().toISOString(),
    },
    dataAccess: [
      {
        dataSource: "results_database",
        dataClassification: "internal",
        containsPii: false,
        recordsAccessed: 1,
      },
    ],
    tags: ["pipeline", "storage"],
  });
}

// ─────────────────────────────────────────────
// Full Pipeline
// ─────────────────────────────────────────────

async function runDocumentPipeline(rawContent: string, filename: string) {
  console.log(`\n📄 Processing: ${filename}`);

  const doc = await ingestDocument(rawContent, filename);
  console.log(`  ✅ Ingested (${doc.sizeBytes} bytes, PII: ${doc.containsPii})`);

  const { chunks } = await chunkDocument(doc);
  console.log(`  ✅ Chunked into ${chunks.length} pieces`);

  const { embeddings } = await embedChunks(doc, chunks);
  console.log(`  ✅ Embedded ${embeddings.length} chunks`);

  const analysis = await analyzeDocument(doc);
  console.log(`  ✅ Analyzed: ${analysis.summary.slice(0, 80)}...`);
  console.log(`     Topics: ${analysis.keyTopics.slice(0, 3).join(", ")}`);
  console.log(`     Risk flags: ${analysis.riskFlags.join(", ") || "none"}`);

  await storeResults(doc, analysis);
  console.log(`  ✅ Results stored`);

  return { doc, analysis };
}

// ─────────────────────────────────────────────
// Run
// ─────────────────────────────────────────────

const SAMPLE_DOC = `
QUARTERLY FINANCIAL REPORT – Q3 2025

Executive Summary:
Revenue increased by 23% year-over-year, reaching $4.2M for the quarter.
Operating expenses remain controlled at 68% of revenue. The company has
achieved profitability for the third consecutive quarter.

Key Metrics:
- MRR: $1.4M (up from $1.1M in Q2)
- Customer count: 847 (net +120)
- Churn rate: 2.1%
- NPS: 72

Risks:
- Increased competition in core market
- Regulatory uncertainty in EU market
- Dependency on single cloud provider

Team Size: 34 full-time employees across engineering, sales, and operations.
`;

(async () => {
  console.log("📊 ARKVOID Document Analysis Pipeline Example\n");

  await runDocumentPipeline(SAMPLE_DOC, "Q3-2025-financial-report.txt");

  console.log("\n🎉 Pipeline complete!");
})();
