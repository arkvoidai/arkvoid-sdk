/**
 * ARKVOID SDK – ArkvoidClient
 *
 * The primary interface for sending AI traces to ARKVOID.
 * Framework-agnostic, runtime-agnostic, zero external dependencies.
 */

import type {
  ArkvoidClientOptions,
  TraceOptions,
  TraceResponse,
  TracePayload,
  RawTraceResponse,
  VerifyOptions,
  VerifyResponse,
  WrapOptions,
  Environment,
} from "./types.js";
import {
  ArkvoidValidationError,
} from "./errors.js";
import { hashValue } from "./hash.js";
import { withRetry, DEFAULT_RETRY_CONFIG } from "./retry.js";
import { ArkvoidLogger } from "./logger.js";
import { HttpClient, SDK_VERSION } from "./http.js";
import { verifyTrace } from "./verify.js";

const DEFAULT_BASE_URL = "https://arkvoid.cherazen.com/api/v1";
const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_MAX_RETRIES = 3;

// ─────────────────────────────────────────────
// ArkvoidClient
// ─────────────────────────────────────────────

export class ArkvoidClient {
  private readonly apiKey: string;
  private readonly defaultAgent?: string;
  private readonly silent: boolean;
  private readonly environment: Environment;
  private readonly sdkVersion: string;
  private readonly http: HttpClient;
  private readonly logger: ArkvoidLogger;
  private readonly maxRetries: number;
  private readonly baseUrl: string;

  constructor(options: ArkvoidClientOptions) {
    const {
      apiKey,
      agent,
      silent = false,
      baseUrl = DEFAULT_BASE_URL,
      timeout = DEFAULT_TIMEOUT_MS,
      maxRetries = DEFAULT_MAX_RETRIES,
      environment = "production",
      sdkVersion = SDK_VERSION,
      debug = false,
    } = options;

    if (!apiKey) {
      throw new ArkvoidValidationError(
        "apiKey is required. Get yours at arkvoid.cherazen.com"
      );
    }
    if (!apiKey.startsWith("ARK_")) {
      throw new ArkvoidValidationError(
        'API key must start with "ARK_". Get yours at arkvoid.cherazen.com'
      );
    }

    this.apiKey = apiKey;
    this.defaultAgent = agent;
    this.silent = silent;
    this.environment = environment;
    this.sdkVersion = sdkVersion;
    this.maxRetries = maxRetries;
    this.baseUrl = baseUrl;
    this.logger = new ArkvoidLogger(debug, silent);
    this.http = new HttpClient(
      baseUrl,
      apiKey,
      timeout,
      this.logger,
      sdkVersion
    );
  }

  // ─────────────────────────────────────────────
  // trace()
  // ─────────────────────────────────────────────

  /**
   * Send an AI action trace to ARKVOID.
   *
   * @example
   * const result = await client.trace({
   *   action: "document_analysis",
   *   riskLevel: "low",
   *   agent: "my-agent",
   *   modelProvider: "openai",
   *   modelName: "gpt-4o",
   *   inputTokens: 1200,
   *   outputTokens: 340,
   *   durationMs: 1823,
   *   metadata: { userId: "u_abc" }
   * });
   */
  async trace(options: TraceOptions): Promise<TraceResponse | null> {
    const agentSlug = options.agent ?? this.defaultAgent;

    if (!agentSlug) {
      const msg =
        'Agent slug is required. Pass agent: "slug" or set it in ArkvoidClient({ agent: "slug" })';
      if (this.silent) {
        this.logger.warn(msg);
        return null;
      }
      throw new ArkvoidValidationError(msg);
    }

    let payload: TracePayload;
    try {
      payload = await this.buildPayload(agentSlug, options);
    } catch (error) {
      this.logger.warn("Failed to build trace payload:", error);
      if (this.silent) return null;
      throw error;
    }

    try {
      const { data } = await withRetry(
        () => this.http.post<RawTraceResponse>("/traces", payload),
        { maxRetries: this.maxRetries, ...DEFAULT_RETRY_CONFIG },
        (attempt, delay) => {
          this.logger.debugLog(
            `Retry attempt ${attempt} in ${Math.round(delay)}ms`
          );
        }
      );

      this.logger.debugLog(`Trace recorded: ${data.trace_id}`);

      return {
        traceId: data.trace_id,
        timestamp: data.timestamp,
        status: data.status,
        hash: data.hash,
      };
    } catch (error) {
      if (this.silent) {
        this.logger.warn("Failed to send trace:", (error as Error).message);
        return null;
      }
      throw error;
    }
  }

  // ─────────────────────────────────────────────
  // verify()
  // ─────────────────────────────────────────────

  /**
   * Verify that a trace exists and its integrity hash is valid.
   *
   * @example
   * const result = await client.verify({ traceId: "ark_abc123" });
   * console.log(result.valid); // true
   */
  async verify(options: VerifyOptions): Promise<VerifyResponse> {
    return verifyTrace(
      options.traceId,
      this.http,
      this.logger,
      options.expectedHash
    );
  }

  // ─────────────────────────────────────────────
  // logAction()
  // ─────────────────────────────────────────────

  /**
   * Execute a function and automatically trace it.
   * Captures duration, success/failure, and optionally input/output hashes.
   *
   * @example
   * const result = await client.logAction(
   *   () => openai.chat.completions.create({ ... }),
   *   {
   *     action: "chat_completion",
   *     agent: "support-bot",
   *     riskLevel: "low",
   *   }
   * );
   */
  async logAction<T>(
    fn: () => T | Promise<T>,
    options: Omit<TraceOptions, "durationMs" | "inputData" | "outputData"> & {
      captureOutput?: boolean;
    }
  ): Promise<T> {
    const start = Date.now();
    let result: T;
    let error: Error | undefined;

    try {
      result = await fn();
    } catch (e) {
      error = e as Error;
      const durationMs = Date.now() - start;

      // Trace the failure (fire-and-forget in silent mode)
      void this.trace({
        ...options,
        durationMs,
        riskLevel: options.riskLevel ?? "high",
        metadata: {
          ...options.metadata,
          success: false,
          error: error.message,
          errorType: error.name,
        },
      });

      throw e;
    }

    const durationMs = Date.now() - start;

    void this.trace({
      ...options,
      durationMs,
      ...(options.captureOutput && { outputData: result }),
      metadata: {
        ...options.metadata,
        success: true,
      },
    });

    return result!;
  }

  // ─────────────────────────────────────────────
  // wrap()
  // ─────────────────────────────────────────────

  /**
   * Wrap an async function so every call is automatically traced.
   *
   * @example
   * const tracedSearch = client.wrap(searchDocuments, {
   *   action: "document_search",
   *   agent: "research-bot",
   *   riskLevel: "low",
   * });
   *
   * // Use like the original:
   * const results = await tracedSearch("quantum computing");
   */
  wrap<TArgs extends unknown[], TReturn>(
    fn: (...args: TArgs) => Promise<TReturn>,
    options: WrapOptions = {}
  ): (...args: TArgs) => Promise<TReturn> {
    const client = this;
    const action = options.action ?? fn.name ?? "wrapped_function";

    return async function (this: unknown, ...args: TArgs): Promise<TReturn> {
      const start = Date.now();
      let result: TReturn;
      let traceError: Error | undefined;

      try {
        result = await fn.apply(this, args);
      } catch (e) {
        traceError = e as Error;
        const durationMs = Date.now() - start;

        void client.trace({
          action,
          riskLevel: "high",
          agent: options.agent,
          durationMs,
          metadata: {
            ...options.metadata,
            success: false,
            error: traceError.message,
            function: fn.name,
          },
        });

        throw e;
      }

      void client.trace({
        action,
        riskLevel: options.riskLevel ?? "low",
        agent: options.agent,
        durationMs: Date.now() - start,
        metadata: {
          ...options.metadata,
          success: true,
          function: fn.name,
        },
      });

      return result!;
    };
  }

  // ─────────────────────────────────────────────
  // Internal: buildPayload()
  // ─────────────────────────────────────────────

  private async buildPayload(
    agentSlug: string,
    options: TraceOptions
  ): Promise<TracePayload> {
    const {
      action,
      riskLevel = "low",
      riskScore,
      inputData,
      outputData,
      inputHash: precomputedInputHash,
      outputHash: precomputedOutputHash,
      durationMs,
      metadata,
      toolCalls,
      dataAccess,
      modelProvider,
      modelName,
      inputTokens,
      outputTokens,
      actionType = "inference",
      tags,
      sessionId,
      parentTraceId,
      requiredHumanApproval,
    } = options;

    // Compute hashes for raw input/output
    const inputHash =
      precomputedInputHash ??
      (inputData !== undefined
        ? (await hashValue(inputData)).prefixed
        : undefined);

    const outputHash =
      precomputedOutputHash ??
      (outputData !== undefined
        ? (await hashValue(outputData)).prefixed
        : undefined);

    const payload: TracePayload = {
      agent_slug: agentSlug,
      action,
      risk_level: riskLevel,
      action_type: actionType,
      environment: this.environment,
      sdk_version: this.sdkVersion,
    };

    // Optional fields
    if (riskScore !== undefined) {
      payload.risk_score = Math.max(0, Math.min(100, riskScore));
    }
    if (inputHash) payload.input_hash = inputHash;
    if (outputHash) payload.output_hash = outputHash;
    if (durationMs !== undefined) payload.duration_ms = durationMs;
    if (metadata) payload.metadata = metadata;
    if (toolCalls?.length) payload.tool_calls = toolCalls;
    if (dataAccess?.length) payload.data_access = dataAccess;
    if (modelProvider) payload.model_provider = modelProvider;
    if (modelName) payload.model_name = modelName;
    if (inputTokens !== undefined) payload.input_tokens = inputTokens;
    if (outputTokens !== undefined) payload.output_tokens = outputTokens;
    if (tags?.length) payload.tags = tags;
    if (sessionId) payload.session_id = sessionId;
    if (parentTraceId) payload.parent_trace_id = parentTraceId;
    if (requiredHumanApproval !== undefined)
      payload.required_human_approval = requiredHumanApproval;

    return payload;
  }

  // ─────────────────────────────────────────────
  // Getters
  // ─────────────────────────────────────────────

  get baseURL(): string {
    return this.baseUrl;
  }

  get version(): string {
    return this.sdkVersion;
  }
}
