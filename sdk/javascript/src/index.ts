/**
 * ARKVOID SDK
 * AI Agent Monitoring & Governance
 *
 * @version 1.0.0
 * @author ARKVOID Inc.
 * @license MIT
 * @see https://arkvoid.cherazen.com
 *
 * @example
 * import { ArkvoidClient } from "arkvoid";
 *
 * const arkvoid = new ArkvoidClient({
 *   apiKey: process.env.ARKVOID_API_KEY!,
 *   agent: "my-agent",
 * });
 *
 * await arkvoid.trace({
 *   action: "document_analysis",
 *   riskLevel: "low",
 *   durationMs: 1200,
 * });
 */

// ─────────────────────────────────────────────
// Core Client
// ─────────────────────────────────────────────

export { ArkvoidClient } from "./client.js";

// ─────────────────────────────────────────────
// Types (re-exported for consumers)
// ─────────────────────────────────────────────

export type {
  ArkvoidClientOptions,
  TraceOptions,
  TraceResponse,
  TracePayload,
  VerifyOptions,
  VerifyResponse,
  WrapOptions,
  LogActionOptions,
  RiskLevel,
  TraceStatus,
  ActionType,
  Environment,
  ToolCallRecord,
  DataAccessRecord,
  HashResult,
  RetryConfig,
} from "./types.js";

// ─────────────────────────────────────────────
// Errors
// ─────────────────────────────────────────────

export {
  ArkvoidError,
  ArkvoidAuthError,
  ArkvoidNotFoundError,
  ArkvoidValidationError,
  ArkvoidRateLimitError,
  ArkvoidTimeoutError,
  ArkvoidNetworkError,
  ArkvoidServerError,
} from "./errors.js";

// ─────────────────────────────────────────────
// Hash Utilities
// ─────────────────────────────────────────────

export {
  sha256,
  hashValue,
  hashBuffer,
  hashApiKey,
  computeTraceIntegrityHash,
  constantTimeEqual,
  hashesEqual,
  stripHashPrefix,
  fnv1aHash,
} from "./hash.js";

// ─────────────────────────────────────────────
// Verification Utilities
// ─────────────────────────────────────────────

export {
  verifyTraceLocally,
  isValidHash,
  isValidTraceId,
} from "./verify.js";

// ─────────────────────────────────────────────
// Functional API (module-level singleton pattern)
// ─────────────────────────────────────────────

import { ArkvoidClient } from "./client.js";
import type { TraceOptions, TraceResponse, VerifyOptions, VerifyResponse } from "./types.js";

let _defaultClient: ArkvoidClient | null = null;

/**
 * Configure a module-level default client.
 * Enables the functional API (trace, verify, logAction).
 *
 * @example
 * import { configure, trace } from "arkvoid";
 *
 * configure({ apiKey: process.env.ARKVOID_API_KEY!, agent: "my-agent" });
 * await trace({ action: "document_search", riskLevel: "low" });
 */
export function configure(
  options: ConstructorParameters<typeof ArkvoidClient>[0]
): void {
  _defaultClient = new ArkvoidClient(options);
}

function getDefaultClient(): ArkvoidClient {
  if (!_defaultClient) {
    throw new Error(
      '[ARKVOID] No default client configured. Call configure({ apiKey: "ARK_..." }) first, ' +
        "or use new ArkvoidClient({ apiKey }) directly."
    );
  }
  return _defaultClient;
}

/**
 * Send an AI action trace using the module-level client.
 * Requires configure() to be called first.
 *
 * @example
 * await trace({ action: "chat_completion", riskLevel: "low", durationMs: 1200 });
 */
export async function trace(
  options: TraceOptions
): Promise<TraceResponse | null> {
  return getDefaultClient().trace(options);
}

/**
 * Verify a trace using the module-level client.
 *
 * @example
 * const result = await verify({ traceId: "ark_abc123" });
 */
export async function verify(options: VerifyOptions): Promise<VerifyResponse> {
  return getDefaultClient().verify(options);
}

/**
 * Execute a function and auto-trace it using the module-level client.
 *
 * @example
 * const result = await logAction(
 *   () => openai.chat.completions.create({ model: "gpt-4o", messages }),
 *   { action: "gpt4o_call", riskLevel: "low" }
 * );
 */
export async function logAction<T>(
  fn: () => T | Promise<T>,
  options: Omit<TraceOptions, "durationMs" | "inputData" | "outputData"> & {
    captureOutput?: boolean;
  }
): Promise<T> {
  return getDefaultClient().logAction(fn, options);
}

// ─────────────────────────────────────────────
// Version
// ─────────────────────────────────────────────

export { SDK_VERSION as VERSION } from "./http.js";

