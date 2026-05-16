/**
 * ARKVOID SDK – Retry Logic with Exponential Backoff + Jitter
 */

import type { RetryConfig } from "./types.js";
import {
  ArkvoidRateLimitError,
  isRetryableError,
} from "./errors.js";

export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 500,
  maxDelayMs: 10_000,
  retryableStatusCodes: [429, 500, 502, 503, 504],
};

/**
 * Execute an async function with exponential backoff + full jitter retry.
 *
 * - Does NOT retry on 4xx (except 429).
 * - Does NOT retry on auth errors (401).
 * - Respects Retry-After header from rate limit errors.
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {},
  onRetry?: (attempt: number, delay: number, error: unknown) => void
): Promise<T> {
  const {
    maxRetries,
    baseDelayMs,
    maxDelayMs,
  } = { ...DEFAULT_RETRY_CONFIG, ...config };

  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // Don't retry non-retryable errors
      if (!isRetryableError(error)) {
        throw error;
      }

      // Don't retry after the last attempt
      if (attempt === maxRetries) {
        break;
      }

      let delayMs: number;

      // Respect Retry-After for rate limit errors
      if (error instanceof ArkvoidRateLimitError && error.retryAfterMs) {
        delayMs = error.retryAfterMs;
      } else {
        // Exponential backoff: baseDelay * 2^attempt + jitter
        const exponential = baseDelayMs * Math.pow(2, attempt);
        const jitter = Math.random() * baseDelayMs;
        delayMs = Math.min(exponential + jitter, maxDelayMs);
      }

      onRetry?.(attempt + 1, delayMs, error);

      await sleep(delayMs);
    }
  }

  throw lastError;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate delay for a given attempt (for display/testing).
 */
export function calculateDelay(
  attempt: number,
  config: Partial<RetryConfig> = {}
): number {
  const { baseDelayMs = 500, maxDelayMs = 10_000 } = config;
  const exponential = baseDelayMs * Math.pow(2, attempt);
  return Math.min(exponential, maxDelayMs);
}
