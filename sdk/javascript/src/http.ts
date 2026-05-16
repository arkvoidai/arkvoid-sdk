/**
 * ARKVOID SDK – Fetch-Based HTTP Client
 *
 * - Works in Node.js 18+, browsers, Edge runtimes, Deno
 * - Timeout via AbortSignal.timeout()
 * - Automatic JSON parsing
 * - Typed error mapping
 */

import {
  ArkvoidNetworkError,
  ArkvoidTimeoutError,
  createErrorFromResponse,
} from "./errors.js";
import { ArkvoidLogger } from "./logger.js";

export const SDK_VERSION = "1.0.0";

export interface HttpRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  headers?: Record<string, string>;
  body?: unknown;
  timeoutMs?: number;
  signal?: AbortSignal;
}

export interface HttpResponse<T = unknown> {
  data: T;
  status: number;
  headers: Headers;
}

export class HttpClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;
  private timeoutMs: number;
  private logger: ArkvoidLogger;

  constructor(
    baseUrl: string,
    apiKey: string,
    timeoutMs: number,
    logger: ArkvoidLogger,
    sdkVersion = SDK_VERSION
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.timeoutMs = timeoutMs;
    this.logger = logger;
    this.defaultHeaders = {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      Accept: "application/json",
      "User-Agent": `arkvoid-js/${sdkVersion}`,
      "X-Arkvoid-SDK": `javascript/${sdkVersion}`,
    };
  }

  async request<T>(
    path: string,
    options: HttpRequestOptions = {}
  ): Promise<HttpResponse<T>> {
    const url = `${this.baseUrl}${path}`;
    const method = options.method ?? "POST";

    const headers = {
      ...this.defaultHeaders,
      ...options.headers,
    };

    // Timeout via AbortSignal
    let timeoutSignal: AbortSignal | undefined;
    let timeoutController: AbortController | undefined;

    if (options.timeoutMs !== undefined || this.timeoutMs > 0) {
      const ms = options.timeoutMs ?? this.timeoutMs;

      // Use AbortSignal.timeout() if available (Node 17.3+, browsers 2023+)
      if (typeof AbortSignal.timeout === "function") {
        timeoutSignal = AbortSignal.timeout(ms);
      } else {
        timeoutController = new AbortController();
        setTimeout(() => timeoutController!.abort(), ms);
        timeoutSignal = timeoutController.signal;
      }
    }

    // Merge external signal if provided
    const signal = mergeSignals(
      [options.signal, timeoutSignal].filter(Boolean) as AbortSignal[]
    );

    const fetchInit: RequestInit = {
      method,
      headers,
      signal,
    };

    if (options.body !== undefined) {
      fetchInit.body = JSON.stringify(options.body);
    }

    this.logger.debugLog(`→ ${method} ${url}`);
    const start = Date.now();

    let response: Response;
    try {
      response = await fetch(url, fetchInit);
    } catch (cause) {
      const err = cause as Error;

      // Distinguish timeout from network error
      if (err.name === "AbortError" || err.name === "TimeoutError") {
        throw new ArkvoidTimeoutError(this.timeoutMs);
      }

      throw new ArkvoidNetworkError(err);
    }

    const latency = Date.now() - start;
    this.logger.debugLog(
      `← ${response.status} ${url} (${latency}ms)`
    );

    const contentType = response.headers.get("content-type") ?? "";
    let data: unknown;

    if (contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorBody =
        typeof data === "object" && data !== null
          ? (data as Record<string, unknown>)
          : { error: String(data) };

      throw createErrorFromResponse(response.status, errorBody);
    }

    return {
      data: data as T,
      status: response.status,
      headers: response.headers,
    };
  }

  async post<T>(
    path: string,
    body: unknown,
    options: Omit<HttpRequestOptions, "method" | "body"> = {}
  ): Promise<HttpResponse<T>> {
    return this.request<T>(path, { ...options, method: "POST", body });
  }

  async get<T>(
    path: string,
    options: Omit<HttpRequestOptions, "method" | "body"> = {}
  ): Promise<HttpResponse<T>> {
    return this.request<T>(path, { ...options, method: "GET" });
  }
}

/**
 * Merge multiple AbortSignals into one.
 * Aborts as soon as any source signal aborts.
 */
function mergeSignals(signals: AbortSignal[]): AbortSignal | undefined {
  if (signals.length === 0) return undefined;
  if (signals.length === 1) return signals[0];

  // AbortSignal.any() is available in Node 20+, Chrome 116+
  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any(signals);
  }

  const controller = new AbortController();
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      break;
    }
    signal.addEventListener("abort", () => controller.abort(signal.reason), {
      once: true,
    });
  }
  return controller.signal;
}
