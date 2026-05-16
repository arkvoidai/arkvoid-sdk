/**
 * ARKVOID SDK – Custom AI Agent Tracing Example
 *
 * Demonstrates tracing a multi-step AI agent with:
 * - Session-level grouping
 * - Parent/child trace relationships
 * - Tool call tracking
 * - State delta recording
 * - Risk escalation
 *
 * npm install arkvoid openai
 */

import { randomUUID } from "node:crypto";
import OpenAI from "openai";
import { ArkvoidClient } from "arkvoid";
import type { ToolCallRecord, RiskLevel } from "arkvoid";

// ─────────────────────────────────────────────
// Setup
// ─────────────────────────────────────────────

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "research-agent",
  environment: "production",
  debug: true,
});

// ─────────────────────────────────────────────
// Tool Definitions
// ─────────────────────────────────────────────

const TOOLS: OpenAI.Chat.ChatCompletionTool[] = [
  {
    type: "function",
    function: {
      name: "web_search",
      description: "Search the web for current information",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
        },
        required: ["query"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "calculate",
      description: "Perform mathematical calculations",
      parameters: {
        type: "object",
        properties: {
          expression: {
            type: "string",
            description: "Mathematical expression to evaluate",
          },
        },
        required: ["expression"],
      },
    },
  },
  {
    type: "function",
    function: {
      name: "save_result",
      description: "Save a result to the database",
      parameters: {
        type: "object",
        properties: {
          key: { type: "string" },
          value: { type: "string" },
        },
        required: ["key", "value"],
      },
    },
  },
];

// ─────────────────────────────────────────────
// Simulated Tool Execution
// ─────────────────────────────────────────────

async function executeTool(
  name: string,
  args: Record<string, string>
): Promise<{ result: string; latencyMs: number }> {
  const start = Date.now();

  // Simulate tool execution
  await new Promise((r) => setTimeout(r, Math.random() * 300 + 100));

  let result: string;
  switch (name) {
    case "web_search":
      result = `Search results for "${args.query}": [Simulated results about ${args.query}]`;
      break;
    case "calculate":
      result = String(eval(args.expression ?? "0")); // demo only!
      break;
    case "save_result":
      result = `Saved: ${args.key} = ${args.value}`;
      break;
    default:
      result = "Unknown tool";
  }

  return { result, latencyMs: Date.now() - start };
}

// ─────────────────────────────────────────────
// Agent Loop with Full Tracing
// ─────────────────────────────────────────────

interface AgentRunOptions {
  task: string;
  userId: string;
  maxIterations?: number;
}

async function runAgent({ task, userId, maxIterations = 5 }: AgentRunOptions) {
  const sessionId = randomUUID();
  const model = "gpt-4o";

  console.log(`\n🤖 Agent session: ${sessionId}`);
  console.log(`📋 Task: ${task}\n`);

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    {
      role: "system",
      content:
        "You are a research assistant. Use tools to answer questions thoroughly.",
    },
    { role: "user", content: task },
  ];

  let iteration = 0;
  let parentTraceId: string | undefined;
  let finalAnswer: string | undefined;

  while (iteration < maxIterations) {
    iteration++;
    const iterStart = Date.now();
    const toolCallsThisIter: ToolCallRecord[] = [];

    console.log(`\n→ Iteration ${iteration}`);

    const response = await openai.chat.completions.create({
      model,
      messages,
      tools: TOOLS,
    });

    const message = response.choices[0]?.message;
    if (!message) break;

    messages.push(message);

    // No more tool calls → agent is done
    if (!message.tool_calls?.length) {
      finalAnswer = message.content ?? "";

      // Trace final answer
      const traceResult = await arkvoid.trace({
        action: "agent_final_answer",
        riskLevel: "low",
        sessionId,
        parentTraceId,
        modelProvider: "openai",
        modelName: model,
        inputTokens: response.usage?.prompt_tokens,
        outputTokens: response.usage?.completion_tokens,
        durationMs: Date.now() - iterStart,
        outputData: finalAnswer,
        metadata: {
          userId,
          iteration,
          taskSummary: task.slice(0, 100),
        },
        tags: ["agent", "final-answer"],
      });

      console.log(`✅ Final trace: ${traceResult?.traceId}`);
      break;
    }

    // Execute tool calls
    for (const toolCall of message.tool_calls) {
      const toolName = toolCall.function.name;
      const toolArgs = JSON.parse(toolCall.function.arguments) as Record<
        string,
        string
      >;

      const riskLevel: RiskLevel =
        toolName === "save_result"
          ? "medium"
          : toolName === "web_search"
            ? "low"
            : "low";

      const { result, latencyMs } = await executeTool(toolName, toolArgs);

      toolCallsThisIter.push({
        toolName,
        callIndex: toolCallsThisIter.length,
        input: toolArgs,
        output: { result },
        latencyMs,
        status: "success",
      });

      console.log(`  🔧 ${toolName}(${JSON.stringify(toolArgs)}) → ${result.slice(0, 60)}`);

      messages.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: result,
      });
    }

    // Trace this iteration
    const traceResult = await arkvoid.trace({
      action: `agent_iteration_${iteration}`,
      riskLevel: "low",
      sessionId,
      parentTraceId,
      modelProvider: "openai",
      modelName: model,
      inputTokens: response.usage?.prompt_tokens,
      outputTokens: response.usage?.completion_tokens,
      durationMs: Date.now() - iterStart,
      toolCalls: toolCallsThisIter,
      metadata: {
        userId,
        iteration,
        toolCount: toolCallsThisIter.length,
        tools: toolCallsThisIter.map((t) => t.toolName),
      },
      tags: ["agent", "iteration"],
    });

    if (!parentTraceId && traceResult?.traceId) {
      parentTraceId = traceResult.traceId;
    }
  }

  return { sessionId, finalAnswer, iterations: iteration };
}

// ─────────────────────────────────────────────
// Run
// ─────────────────────────────────────────────

(async () => {
  console.log("🤖 ARKVOID Custom Agent Tracing Example\n");

  const { sessionId, finalAnswer, iterations } = await runAgent({
    task: "What is 15% of 2847, and search for recent AI governance news?",
    userId: "user_demo_001",
  });

  console.log(`\n─────────────────────────────`);
  console.log(`Session: ${sessionId}`);
  console.log(`Iterations: ${iterations}`);
  console.log(`Answer: ${finalAnswer?.slice(0, 200)}...`);
})();
