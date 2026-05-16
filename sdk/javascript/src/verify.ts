/**
 * ARKVOID SDK – Trace Verification
 *
 * Verify that a trace's cryptographic hash is authentic.
 * Supports both online verification (via API) and offline
 * local verification when you have the raw trace data.
 */

import type {
  VerifyOptions,
  VerifyResponse,
  RawTraceResponse,
} from "./types.js";
import { computeTraceIntegrityHash, hashesEqual } from "./hash.js";
import type { HttpClient } from "./http.js";
import { withRetry } from "./retry.js";
import type { ArkvoidLogger } from "./logger.js";

// ─────────────────────────────────────────────
// Online Verification (API round-trip)
// ─────────────────────────────────────────────

export async function verifyTrace(
  traceId: string,
  http: HttpClient,
  logger: ArkvoidLogger,
  expectedHash?: string
): Promise<VerifyResponse> {
  logger.debugLog(`Verifying trace: ${traceId}`);

  const { data } = await withRetry(() =>
    http.get<RawTraceResponse>(`/traces/${traceId}`)
  );

  const valid = data.status !== "failed";
  const matchesExpected = expectedHash
    ? hashesEqual(data.hash, expectedHash)
    : undefined;

  return {
    traceId: data.trace_id,
    valid,
    status: data.status,
    hash: data.hash,
    timestamp: data.timestamp,
    ...(matchesExpected !== undefined && { matchesExpected }),
  };
}

// ─────────────────────────────────────────────
// Offline / Local Verification
// ─────────────────────────────────────────────

export interface LocalVerifyInput {
  agentId: string;
  action: string;
  timestamp: string;
  hash: string;
}

/**
 * Verify a trace locally without an API call.
 *
 * Uses the same formula as the Arkvoid backend:
 * SHA-256(agentId + action + timestamp)
 *
 * @returns true if the computed hash matches the stored hash.
 */
export async function verifyTraceLocally(
  input: LocalVerifyInput
): Promise<boolean> {
  const computed = await computeTraceIntegrityHash(
    input.agentId,
    input.action,
    input.timestamp
  );
  return hashesEqual(computed, input.hash);
}

// ─────────────────────────────────────────────
// Hash Format Validation
// ─────────────────────────────────────────────

/**
 * Check if a string is a valid Arkvoid hash (sha256:<64 hex chars>).
 */
export function isValidHash(hash: string): boolean {
  if (!hash.startsWith("sha256:")) return false;
  const hex = hash.slice(7);
  return /^[0-9a-f]{64}$/.test(hex);
}

/**
 * Check if a string is a valid Arkvoid trace ID (ark_<32 hex chars>).
 */
export function isValidTraceId(traceId: string): boolean {
  return /^ark_[0-9a-f]{32}$/.test(traceId);
}
