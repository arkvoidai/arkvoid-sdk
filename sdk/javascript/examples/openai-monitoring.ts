/**
 * ARKVOID SDK â€“ OpenAI API Monitoring Example
 *
 * Every OpenAI call is automatically traced to ARKVOID,
 * including model, tokens, latency, and hashed prompt/response.
 *
 * npm install arkvoid openai
 */

import OpenAI from "openai";
import { ArkvoidClient } from "arkvoid";

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Setup
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

const arkvoid = new ArkvoidClient({
  apiKey: process.env.ARKVOID_API_KEY!,
  agent: "gpt4-support-bot",
  environment: "production",
  debug: false,
});

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Example 1: Manual tracing of a chat completion
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function trackedChatCompletion(userMessage: string) {
  const model = "gpt-4o";
  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: "You are a helpful assistant." },
    { role: "user", content: userMessage },
  ];

  const start = Date.now();

  const completion = await openai.chat.completions.create({ model, messages });

  const durationMs = Date.now() - start;
  const choice = completion.choices[0]?.message.content ?? "";

  // Send trace to ARKVOID
  const trace = await arkvoid.trace({
    action: "chat_completion",
    riskLevel: "low",
    modelProvider: "openai",
    modelName: model,
    inputTokens: completion.usage?.prompt_tokens,
    outputTokens: completion.usage?.completion_tokens,
    durationMs,
    // Hashed â€” not stored raw
    inputData: messages,
    outputData: choice,
    metadata: {
      promptId: "support-v1",
      userId: "user_demo",
      finishReason: completion.choices[0]?.finish_reason,
    },
    tags: ["chat", "support"],
  });

  console.log(`âœ… Trace recorded: ${trace?.traceId}`);
  return choice;
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Example 2: Automatic wrapping with client.wrap()
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function analyzeDocument(text: string): Promise<string> {
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content: "Analyze the following document and extract key insights.",
      },
      { role: "user", content: text },
    ],
  });
  return completion.choices[0]?.message.content ?? "";
}

// Every call to tracedAnalyze() is automatically logged
const tracedAnalyze = arkvoid.wrap(analyzeDocument, {
  action: "document_analysis",
  riskLevel: "low",
  metadata: { pipeline: "research-v2" },
});

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Example 3: logAction() â€“ run + trace in one call
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function runWithAutoTrace(prompt: string) {
  const result = await arkvoid.logAction(
    () =>
      openai.chat.completions.create({
        model: "gpt-4o",
        messages: [{ role: "user", content: prompt }],
      }),
    {
      action: "user_query",
      riskLevel: "low",
      modelProvider: "openai",
      modelName: "gpt-4o",
      metadata: { source: "api" },
    }
  );

  return result.choices[0]?.message.content;
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Example 4: High-risk action with risk score
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async function executeHighRiskQuery(prompt: string, userId: string) {
  const start = Date.now();

  const result = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      {
        role: "system",
        content: "You have access to sensitive financial data. Be careful.",
      },
      { role: "user", content: prompt },
    ],
  });

  await arkvoid.trace({
    action: "financial_analysis",
    riskLevel: "high",
    riskScore: 75,
    requiredHumanApproval: true,
    modelProvider: "openai",
    modelName: "gpt-4o",
    durationMs: Date.now() - start,
    inputData: prompt,
    metadata: {
      userId,
      dataClassification: "confidential",
      requiresReview: true,
    },
    dataAccess: [
      {
        dataSource: "financial_records_db",
        dataClassification: "confidential",
        containsPii: true,
        recordsAccessed: 1,
      },
    ],
    tags: ["financial", "high-risk", "requires-approval"],
  });

  return result.choices[0]?.message.content;
}

// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Run
// â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

(async () => {
  console.log("ðŸ“¡ ARKVOID OpenAI Monitoring Example\n");

  const answer = await trackedChatCompletion("What is quantum computing?");
  console.log("Response:", answer?.slice(0, 100) + "...\n");

  const analysis = await tracedAnalyze(
    "Photosynthesis is the process by which plants convert light to energy..."
  );
  console.log("Analysis:", analysis?.slice(0, 100) + "...\n");
})();
      
