/**
 * ARKVOID SDK – Cryptographic Hash Utilities
 *
 * Uses the native Web Crypto API, which is available in:
 * - Node.js 18+
 * - All modern browsers
 * - Edge runtimes (Vercel Edge, Cloudflare Workers, Deno)
 *
 * Zero external dependencies.
 */

import type { HashResult } from "./types.js";

// ─────────────────────────────────────────────
// Core SHA-256
// ─────────────────────────────────────────────

/**
 * Compute SHA-256 hash of a string.
 * Returns hex-encoded digest.
 */
export async function sha256(input: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(input);

  // Use native crypto (Node.js 18+ and browsers)
  const hashBuffer = await getCrypto().subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Hash any JSON-serialisable value (objects, arrays, strings, numbers, etc.).
 * Keys are sorted for determinism.
 */
export async function hashValue(value: unknown): Promise<HashResult> {
  const serialised =
    typeof value === "string"
      ? value
      : JSON.stringify(value, sortedReplacer);

  const hex = await sha256(serialised);
  return {
    hex,
    prefixed: `sha256:${hex}`,
  };
}

/**
 * Hash a raw binary buffer.
 */
export async function hashBuffer(buffer: ArrayBuffer): Promise<string> {
  const hashBuffer = await getCrypto().subtle.digest("SHA-256", buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ─────────────────────────────────────────────
// Trace Integrity Hash
// ─────────────────────────────────────────────

/**
 * Compute the canonical integrity hash of a trace, matching
 * the server-side formula: SHA-256(agentId + action + timestamp).
 *
 * Used for local verification of traces without network round-trips.
 */
export async function computeTraceIntegrityHash(
  agentId: string,
  action: string,
  timestamp: string
): Promise<string> {
  const raw = agentId + action + timestamp;
  const hex = await sha256(raw);
  return `sha256:${hex}`;
}

// ─────────────────────────────────────────────
// API Key Hash (for local comparison)
// ─────────────────────────────────────────────

/**
 * Compute SHA-256 hash of an API key (same formula the server uses).
 * Useful for debugging key mismatches.
 */
export async function hashApiKey(apiKey: string): Promise<string> {
  return sha256(apiKey);
}

// ─────────────────────────────────────────────
// Sync fallback for non-async contexts
// ─────────────────────────────────────────────

/**
 * Synchronous hash using a simple FNV-1a 64-bit approximation.
 * NOT cryptographic. Use only for non-security deduplication.
 */
export function fnv1aHash(input: string): string {
  let hash = 0x811c9dc5n;
  const FNV_PRIME = 0x01000193n;
  const MOD = BigInt("0xFFFFFFFF");
  for (let i = 0; i < input.length; i++) {
    hash ^= BigInt(input.charCodeAt(i));
    hash = (hash * FNV_PRIME) & MOD;
  }
  return hash.toString(16).padStart(8, "0");
}

// ─────────────────────────────────────────────
// Comparison
// ─────────────────────────────────────────────

/**
 * Constant-time string comparison to avoid timing attacks.
 */
export function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

/**
 * Strip sha256: prefix from a hash string.
 */
export function stripHashPrefix(hash: string): string {
  return hash.startsWith("sha256:") ? hash.slice(7) : hash;
}

/**
 * Compare two hashes (with or without sha256: prefix) in constant time.
 */
export function hashesEqual(a: string, b: string): boolean {
  return constantTimeEqual(stripHashPrefix(a), stripHashPrefix(b));
}

// ─────────────────────────────────────────────
// Internals
// ─────────────────────────────────────────────

function getCrypto(): Crypto {
  if (typeof globalThis.crypto !== "undefined") {
    return globalThis.crypto;
  }
  // Node.js <19 fallback
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require("crypto").webcrypto as Crypto;
  } catch {
    throw new Error(
      "[ARKVOID] No Web Crypto API available. Use Node.js 18+ or a modern runtime."
    );
  }
}

function sortedReplacer(_key: string, value: unknown): unknown {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).sort(([a], [b]) =>
        a.localeCompare(b)
      )
    );
  }
  return value;
}
