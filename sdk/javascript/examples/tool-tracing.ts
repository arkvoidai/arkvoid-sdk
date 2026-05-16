/**
 * ARKVOID SDK – Tool Execution Tracing Example
 *
 * Demonstrates fine-grained tool call tracing for:
 * - Web search
 * - Code execution
 * - Database queries
 * - External API calls
 * - File operations
 *
 * npm install arkvoid
 */

import { ArkvoidClient } from "arkvoid";
import type { ToolCallRecord, RiskLevel } from "arkvoid";

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "tool-agent",
  environment: "production",
});

// ─────────────────────────────────────────────
// Tool Registry
// ─────────────────────────────────────────────

interface ToolResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  latencyMs: number;
}

// Traced tool executor factory
function createTracedTool<TInput extends Record<string, unknown>, TOutput>(
  config: {
    name: string;
    riskLevel: RiskLevel;
    externalSystem?: string;
    execute: (input: TInput) => Promise<TOutput>;
    agentSlug?: string;
  }
) {
  return async (input: TInput): Promise<ToolResult<TOutput>> => {
    const start = Date.now();
    let result: TOutput | undefined;
    let error: string | undefined;

    try {
      result = await config.execute(input);
    } catch (e) {
      error = (e as Error).message;
    }

    const latencyMs = Date.now() - start;

    // Trace each tool call
    await arkvoid.trace({
      action: `tool_call.${config.name}`,
      riskLevel: error ? "high" : config.riskLevel,
      actionType: "tool_call",
      agent: config.agentSlug,
      toolCalls: [
        {
          toolName: config.name,
          callIndex: 0,
          input,
          output: result ? { result } : { error },
          externalSystem: config.externalSystem,
          latencyMs,
          status: error ? "error" : "success",
        },
      ],
      durationMs: latencyMs,
      metadata: {
        success: !error,
        ...(error && { error }),
      },
      tags: ["tool", config.name, error ? "error" : "success"],
    });

    return { success: !error, data: result, error, latencyMs };
  };
}

// ─────────────────────────────────────────────
// Tool Implementations (simulated)
// ─────────────────────────────────────────────

// 1. Web Search
const webSearch = createTracedTool({
  name: "web_search",
  riskLevel: "low",
  externalSystem: "search_api",
  execute: async ({ query }: { query: string }) => {
    await sleep(200 + Math.random() * 300);
    return {
      results: [
        { title: `Result 1 for "${query}"`, url: "https://example.com/1", snippet: "..." },
        { title: `Result 2 for "${query}"`, url: "https://example.com/2", snippet: "..." },
      ],
      totalResults: 1240000,
    };
  },
});

// 2. Code Execution (sandboxed)
const executeCode = createTracedTool({
  name: "code_execution",
  riskLevel: "high",
  externalSystem: "code_sandbox",
  execute: async ({
    code,
    language,
  }: {
    code: string;
    language: string;
  }) => {
    await sleep(500 + Math.random() * 1000);
    // Simulated execution
    if (code.includes("rm -rf") || code.includes("delete")) {
      throw new Error("Dangerous operation detected");
    }
    return {
      stdout: `[Executed ${language} code]\nOutput: 42`,
      stderr: "",
      exitCode: 0,
      executionTime: 0.34,
    };
  },
});

// 3. Database Query
const queryDatabase = createTracedTool({
  name: "database_query",
  riskLevel: "medium",
  externalSystem: "postgres_prod",
  execute: async ({ sql, params }: { sql: string; params: unknown[] }) => {
    await sleep(50 + Math.random() * 200);

    // Detect potential SQL injection pattern
    if (sql.toLowerCase().includes("drop table") || sql.toLowerCase().includes("--")) {
      throw new Error("Suspicious SQL pattern detected");
    }

    return {
      rows: [{ id: 1, name: "Alice" }, { id: 2, name: "Bob" }],
      rowCount: 2,
      duration: 45,
    };
  },
});

// 4. External API Call
const callExternalApi = createTracedTool({
  name: "external_api",
  riskLevel: "medium",
  externalSystem: "payment_gateway",
  execute: async ({
    endpoint,
    payload,
  }: {
    endpoint: string;
    payload: Record<string, unknown>;
  }) => {
    await sleep(100 + Math.random() * 400);
    return {
      statusCode: 200,
      response: { success: true, transactionId: "txn_abc123" },
    };
  },
});

// 5. File Operations
const fileOperation = createTracedTool({
  name: "file_operation",
  riskLevel: "medium",
  externalSystem: "s3_bucket",
  execute: async ({
    operation,
    path,
  }: {
    operation: "read" | "write" | "delete";
    path: string;
  }) => {
    await sleep(80 + Math.random() * 150);

    if (operation === "delete" && path.includes("production")) {
      throw new Error("Cannot delete production files without approval");
    }

    return {
      operation,
      path,
      success: true,
      sizeBytes: operation === "read" ? 4096 : undefined,
    };
  },
});

// ─────────────────────────────────────────────
// Multi-Tool Agent Trace (batch)
// ─────────────────────────────────────────────

async function runResearchWorkflow(topic: string) {
  const toolCalls: ToolCallRecord[] = [];
  const start = Date.now();

  console.log(`\n🔎 Researching: "${topic}"`);

  // Execute multiple tools
  const search1 = await webSearch({ query: `${topic} latest research` });
  const search2 = await webSearch({ query: `${topic} best practices` });
  const dbResult = await queryDatabase({
    sql: "SELECT * FROM knowledge_base WHERE topic = $1 LIMIT 10",
    params: [topic],
  });

  // Aggregate tool calls for a single "research" trace
  if (search1.data) {
    toolCalls.push({
      toolName: "web_search",
      callIndex: 0,
      input: { query: `${topic} latest research` },
      output: { resultCount: (search1.data as { results: unknown[] }).results.length },
      status: "success",
      latencyMs: search1.latencyMs,
    });
  }

  if (search2.data) {
    toolCalls.push({
      toolName: "web_search",
      callIndex: 1,
      input: { query: `${topic} best practices` },
      output: { resultCount: (search2.data as { results: unknown[] }).results.length },
      status: "success",
      latencyMs: search2.latencyMs,
    });
  }

  if (dbResult.data) {
    toolCalls.push({
      toolName: "database_query",
      callIndex: 2,
      input: { table: "knowledge_base", topic },
      output: { rowCount: (dbResult.data as { rowCount: number }).rowCount },
      externalSystem: "postgres_prod",
      status: "success",
      latencyMs: dbResult.latencyMs,
    });
  }

  // Single aggregated trace for the full workflow
  const trace = await arkvoid.trace({
    action: "research_workflow",
    riskLevel: "low",
    durationMs: Date.now() - start,
    toolCalls,
    metadata: {
      topic,
      toolsUsed: toolCalls.map((t) => t.toolName),
      dataSourcesQueried: 3,
    },
    tags: ["research", "multi-tool"],
  });

  console.log(`✅ Research workflow traced: ${trace?.traceId}`);
}

// ─────────────────────────────────────────────
// High-Risk Tool Interception
// ─────────────────────────────────────────────

async function runHighRiskOperation() {
  console.log("\n⚠️  Running high-risk code execution...");

  const result = await executeCode({
    code: "print('Hello, World!')",
    language: "python",
  });

  if (!result.success) {
    // Trace the failure with critical risk
    await arkvoid.trace({
      action: "code_execution_blocked",
      riskLevel: "critical",
      riskScore: 95,
      metadata: {
        reason: result.error,
        blocked: true,
      },
      tags: ["code-exec", "blocked", "security"],
    });
    console.log(`🚫 Blocked: ${result.error}`);
  } else {
    console.log(`✅ Executed safely (${result.latencyMs}ms)`);
  }
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─────────────────────────────────────────────
// Run
// ─────────────────────────────────────────────

(async () => {
  console.log("🔧 ARKVOID Tool Execution Tracing Example\n");

  await runResearchWorkflow("AI agent governance");
  await runHighRiskOperation();

  // Single tool traces
  const apiResult = await callExternalApi({
    endpoint: "/payments/charge",
    payload: { amount: 2999, currency: "usd" },
  });
  console.log(`\n💳 API call: ${apiResult.success ? "success" : apiResult.error}`);

  console.log("\n🎉 All tool traces sent to ARKVOID!");
})();
