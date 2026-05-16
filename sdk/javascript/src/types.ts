/**
 * ARKVOID SDK – Core TypeScript Types
 * https://arkvoid.cherazen.com
 */

// ─────────────────────────────────────────────
// Risk & Status
// ─────────────────────────────────────────────

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type TraceStatus = "verified" | "failed" | "pending_approval";
export type ActionType = "inference" | "tool_call" | "approval" | "data_access" | "custom";
export type Environment = "production" | "staging" | "development" | "test";

// ─────────────────────────────────────────────
// Client Configuration
// ─────────────────────────────────────────────

export interface ArkvoidClientOptions {
  /** Your ARKVOID API key. Must start with ARK_. */
  apiKey: string;
  /** Default agent slug to use when not specified per trace. */
  agent?: string;
  /** Suppress all errors and warnings. Useful for fire-and-forget. Default: false */
  silent?: boolean;
  /** Base URL override. Default: https://arkvoid.cherazen.com/api/v1 */
  baseUrl?: string;
  /** Timeout in milliseconds. Default: 10000 */
  timeout?: number;
  /** Max retry attempts on transient failures. Default: 3 */
  maxRetries?: number;
  /** Environment tag attached to all traces. Default: "production" */
  environment?: Environment;
  /** SDK version string appended to User-Agent. */
  sdkVersion?: string;
  /** Enable verbose debug logging. Default: false */
  debug?: boolean;
}

// ─────────────────────────────────────────────
// Trace Payload (what you send)
// ─────────────────────────────────────────────

export interface TraceOptions {
  /** What the agent did. e.g. "document_analysis", "user_query" */
  action: string;
  /** Risk classification. Default: "low" */
  riskLevel?: RiskLevel;
  /** Agent slug override (uses client default if not set). */
  agent?: string;
  /** Numeric risk score 0–100. Auto-calculated if omitted. */
  riskScore?: number;
  /** Raw input to be SHA-256 hashed before sending. NOT stored raw. */
  inputData?: unknown;
  /** Raw output to be SHA-256 hashed before sending. NOT stored raw. */
  outputData?: unknown;
  /** Duration of the action in milliseconds. */
  durationMs?: number;
  /** Extra structured metadata (model, tokens, user_id, etc.) */
  metadata?: Record<string, unknown>;
  /** Tool calls made during this trace. */
  toolCalls?: ToolCallRecord[];
  /** Data sources accessed during this trace. */
  dataAccess?: DataAccessRecord[];
  /** Model provider. e.g. "openai", "anthropic", "mistral" */
  modelProvider?: string;
  /** Model name. e.g. "gpt-4o", "claude-3-5-sonnet-20241022" */
  modelName?: string;
  /** Input token count. */
  inputTokens?: number;
  /** Output token count. */
  outputTokens?: number;
  /** Action type classification. Default: "inference" */
  actionType?: ActionType;
  /** Tags for filtering/grouping traces. */
  tags?: string[];
  /** Session ID to group related traces. */
  sessionId?: string;
  /** Parent trace ID for nested/child traces. */
  parentTraceId?: string;
  /** Whether this action required human approval. */
  requiredHumanApproval?: boolean;
  /** Pre-computed input hash (bypasses auto-hashing). */
  inputHash?: string;
  /** Pre-computed output hash (bypasses auto-hashing). */
  outputHash?: string;
}

// ─────────────────────────────────────────────
// Tool Call Record
// ─────────────────────────────────────────────

export interface ToolCallRecord {
  /** Tool name. e.g. "web_search", "calculator", "send_email" */
  toolName: string;
  /** Index/order of this tool call in the trace. */
  callIndex?: number;
  /** Tool input (will be stored as preview, not hashed). */
  input?: Record<string, unknown>;
  /** Tool output (will be stored as preview). */
  output?: Record<string, unknown>;
  /** External system this tool interacted with. */
  externalSystem?: string;
  /** Tool call latency in ms. */
  latencyMs?: number;
  /** Execution status. */
  status?: "success" | "error" | "timeout";
}

// ─────────────────────────────────────────────
// Data Access Record
// ─────────────────────────────────────────────

export interface DataAccessRecord {
  /** Data source name. e.g. "user_database", "s3://my-bucket" */
  dataSource: string;
  /** Data classification level. */
  dataClassification?: "public" | "internal" | "confidential" | "restricted";
  /** Whether PII was accessed. */
  containsPii?: boolean;
  /** Number of records accessed. */
  recordsAccessed?: number;
}

// ─────────────────────────────────────────────
// Trace Response (what you get back)
// ─────────────────────────────────────────────

export interface TraceResponse {
  /** Unique trace ID. Format: ark_<hex> */
  traceId: string;
  /** ISO 8601 timestamp of when the trace was recorded. */
  timestamp: string;
  /** Verification status. */
  status: TraceStatus;
  /** SHA-256 hash of the trace for integrity verification. Format: sha256:<hex> */
  hash: string;
}

// Raw API response shape (snake_case from server)
export interface RawTraceResponse {
  trace_id: string;
  timestamp: string;
  status: TraceStatus;
  hash: string;
}

// ─────────────────────────────────────────────
// Verify Options & Response
// ─────────────────────────────────────────────

export interface VerifyOptions {
  /** The trace ID to verify. */
  traceId: string;
  /** Expected hash to compare against. */
  expectedHash?: string;
}

export interface VerifyResponse {
  traceId: string;
  valid: boolean;
  status: TraceStatus;
  hash: string;
  timestamp: string;
  matchesExpected?: boolean;
}

// ─────────────────────────────────────────────
// logAction Options
// ─────────────────────────────────────────────

export interface LogActionOptions extends TraceOptions {
  /** Function to wrap and trace. */
  fn: (...args: unknown[]) => unknown | Promise<unknown>;
  /** Arguments to pass to the function. */
  args?: unknown[];
}

// ─────────────────────────────────────────────
// Wrap Options (for client.wrap())
// ─────────────────────────────────────────────

export interface WrapOptions {
  /** Override the action name. Defaults to fn.name */
  action?: string;
  /** Risk level for this wrapped function. */
  riskLevel?: RiskLevel;
  /** Agent slug override. */
  agent?: string;
  /** Extra metadata to merge. */
  metadata?: Record<string, unknown>;
}

// ─────────────────────────────────────────────
// Retry Config
// ─────────────────────────────────────────────

export interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
  retryableStatusCodes: number[];
}

// ─────────────────────────────────────────────
// Hash Utilities
// ─────────────────────────────────────────────

export interface HashResult {
  /** The SHA-256 hash in hex. */
  hex: string;
  /** The SHA-256 hash with prefix. */
  prefixed: string;
}

// ─────────────────────────────────────────────
// Internal Request Payload (snake_case → server)
// ─────────────────────────────────────────────

export interface TracePayload {
  agent_slug: string;
  action: string;
  risk_level: RiskLevel;
  risk_score?: number;
  input_hash?: string;
  output_hash?: string;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
  model_provider?: string;
  model_name?: string;
  input_tokens?: number;
  output_tokens?: number;
  action_type?: ActionType;
  tags?: string[];
  session_id?: string;
  parent_trace_id?: string;
  required_human_approval?: boolean;
  tool_calls?: ToolCallRecord[];
  data_access?: DataAccessRecord[];
  environment?: Environment;
  sdk_version?: string;
}
