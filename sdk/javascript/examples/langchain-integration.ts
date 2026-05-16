/**
 * ARKVOID SDK – LangChain Integration Example
 *
 * Integrates ARKVOID with LangChain via a custom callback handler.
 * Automatically traces all LLM calls, chain runs, and tool invocations.
 *
 * npm install arkvoid @langchain/core @langchain/openai langchain
 */

import { ArkvoidClient } from "arkvoid";
import type { ToolCallRecord } from "arkvoid";
import { BaseCallbackHandler } from "@langchain/core/callbacks/base";
import type { Serialized } from "@langchain/core/load/serializable";
import type { LLMResult } from "@langchain/core/outputs";
import { ChatOpenAI } from "@langchain/openai";
import { AgentExecutor, createOpenAIToolsAgent } from "langchain/agents";
import { pull } from "langchain/hub";
import { TavilySearchResults } from "@langchain/community/tools/tavily_search";
import type { ChatPromptTemplate } from "@langchain/core/prompts";

// ─────────────────────────────────────────────
// ARKVOID LangChain Callback Handler
// ─────────────────────────────────────────────

export class ArkvoidLangChainHandler extends BaseCallbackHandler {
  name = "ArkvoidLangChainHandler";

  private client: ArkvoidClient;
  private agentSlug: string;
  private runStartTimes = new Map<string, number>();
  private pendingToolCalls = new Map<string, ToolCallRecord[]>();

  constructor(client: ArkvoidClient, agentSlug: string) {
    super();
    this.client = client;
    this.agentSlug = agentSlug;
  }

  // ── LLM Events ──────────────────────────────

  async handleLLMStart(
    llm: Serialized,
    _prompts: string[],
    runId: string
  ): Promise<void> {
    this.runStartTimes.set(runId, Date.now());
    this.pendingToolCalls.set(runId, []);
    console.log(`[ARKVOID] LLM started: ${llm.id?.join("/")} (${runId})`);
  }

  async handleLLMEnd(output: LLMResult, runId: string): Promise<void> {
    const startTime = this.runStartTimes.get(runId);
    const durationMs = startTime ? Date.now() - startTime : undefined;
    const toolCalls = this.pendingToolCalls.get(runId) ?? [];

    const generation = output.generations[0]?.[0];
    const modelName =
      (output.llmOutput?.model_name as string) ??
      (output.llmOutput?.modelName as string) ??
      "unknown";

    await this.client.trace({
      action: "llm_call",
      riskLevel: "low",
      agent: this.agentSlug,
      modelProvider: "openai",
      modelName,
      inputTokens: output.llmOutput?.tokenUsage?.promptTokens as number,
      outputTokens: output.llmOutput?.tokenUsage?.completionTokens as number,
      durationMs,
      ...(generation && { outputData: generation.text }),
      toolCalls,
      metadata: {
        source: "langchain",
        runId,
        generationCount: output.generations.length,
      },
      tags: ["langchain", "llm"],
    });

    this.runStartTimes.delete(runId);
    this.pendingToolCalls.delete(runId);
  }

  async handleLLMError(error: Error, runId: string): Promise<void> {
    const startTime = this.runStartTimes.get(runId);
    const durationMs = startTime ? Date.now() - startTime : undefined;

    await this.client.trace({
      action: "llm_error",
      riskLevel: "high",
      agent: this.agentSlug,
      durationMs,
      metadata: {
        source: "langchain",
        runId,
        error: error.message,
        success: false,
      },
      tags: ["langchain", "error"],
    });

    this.runStartTimes.delete(runId);
    this.pendingToolCalls.delete(runId);
  }

  // ── Tool Events ──────────────────────────────

  async handleToolStart(
    tool: Serialized,
    input: string,
    runId: string,
    parentRunId?: string
  ): Promise<void> {
    this.runStartTimes.set(runId, Date.now());
    console.log(
      `[ARKVOID] Tool started: ${tool.name ?? "unknown"} (${runId})`
    );

    // Register tool call under parent LLM run
    if (parentRunId && this.pendingToolCalls.has(parentRunId)) {
      const calls = this.pendingToolCalls.get(parentRunId)!;
      calls.push({
        toolName: (tool.name as string) ?? "unknown",
        callIndex: calls.length,
        input: { query: input },
        status: "success",
      });
    }
  }

  async handleToolEnd(
    output: string,
    runId: string,
    parentRunId?: string
  ): Promise<void> {
    const startTime = this.runStartTimes.get(runId);
    const durationMs = startTime ? Date.now() - startTime : undefined;

    // Update tool call record with output + latency
    if (parentRunId && this.pendingToolCalls.has(parentRunId)) {
      const calls = this.pendingToolCalls.get(parentRunId)!;
      const last = calls[calls.length - 1];
      if (last) {
        last.latencyMs = durationMs;
        last.output = { result: output.slice(0, 500) }; // truncate for preview
      }
    }

    this.runStartTimes.delete(runId);
  }

  async handleToolError(error: Error, runId: string): Promise<void> {
    await this.client.trace({
      action: "tool_error",
      riskLevel: "medium",
      agent: this.agentSlug,
      metadata: {
        source: "langchain",
        runId,
        error: error.message,
      },
      tags: ["langchain", "tool", "error"],
    });

    this.runStartTimes.delete(runId);
  }

  // ── Chain Events ─────────────────────────────

  async handleChainStart(
    _chain: Serialized,
    _inputs: Record<string, unknown>,
    runId: string
  ): Promise<void> {
    this.runStartTimes.set(runId, Date.now());
  }

  async handleChainEnd(
    _outputs: Record<string, unknown>,
    runId: string
  ): Promise<void> {
    this.runStartTimes.delete(runId);
  }
}

// ─────────────────────────────────────────────
// Usage: LangChain Agent with ARKVOID tracing
// ─────────────────────────────────────────────

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "research-agent",
});

const arkvoidHandler = new ArkvoidLangChainHandler(arkvoid, "research-agent");

const llm = new ChatOpenAI({
  model: "gpt-4o",
  temperature: 0,
  callbacks: [arkvoidHandler],
});

async function runResearchAgent(query: string) {
  const tools = [new TavilySearchResults({ maxResults: 3 })];

  const prompt = await pull<ChatPromptTemplate>(
    "hwchase17/openai-tools-agent"
  );

  const agent = await createOpenAIToolsAgent({ llm, tools, prompt });

  const executor = new AgentExecutor({
    agent,
    tools,
    callbacks: [arkvoidHandler],
    verbose: false,
  });

  console.log(`\nRunning research agent for: "${query}"`);

  const result = await executor.invoke({ input: query });

  return result.output;
}

// ─────────────────────────────────────────────
// Simple chain tracing (without agent)
// ─────────────────────────────────────────────

async function tracedChain(prompt: string) {
  const simpleLlm = new ChatOpenAI({
    model: "gpt-4o-mini",
    callbacks: [arkvoidHandler],
  });

  const result = await simpleLlm.invoke(prompt);
  return result.content;
}

// ─────────────────────────────────────────────
// Run
// ─────────────────────────────────────────────

(async () => {
  console.log("🔗 ARKVOID LangChain Integration Example\n");

  const answer = await tracedChain(
    "Explain the basics of reinforcement learning in 2 sentences."
  );
  console.log("LLM:", answer);
})();
