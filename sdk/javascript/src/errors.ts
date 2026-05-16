/**
 * ARKVOID SDK – Custom Error Classes
 */

export class ArkvoidError extends Error {
  public readonly code: string;
  public readonly statusCode?: number;
  public readonly details?: unknown;

  constructor(
    message: string,
    code: string,
    statusCode?: number,
    details?: unknown
  ) {
    super(message);
    this.name = "ArkvoidError";
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;

    // Maintain proper prototype chain in transpiled environments
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ArkvoidAuthError extends ArkvoidError {
  constructor(message = "Invalid or revoked API key") {
    super(message, "AUTH_ERROR", 401);
    this.name = "ArkvoidAuthError";
  }
}

export class ArkvoidNotFoundError extends ArkvoidError {
  constructor(resource: string) {
    super(
      `${resource} not found. Make sure it's registered at arkvoid.cherazen.com`,
      "NOT_FOUND",
      404
    );
    this.name = "ArkvoidNotFoundError";
  }
}

export class ArkvoidValidationError extends ArkvoidError {
  constructor(message: string, details?: unknown) {
    super(message, "VALIDATION_ERROR", 400, details);
    this.name = "ArkvoidValidationError";
  }
}

export class ArkvoidRateLimitError extends ArkvoidError {
  public readonly retryAfterMs?: number;

  constructor(retryAfterMs?: number) {
    super(
      "Rate limit exceeded. Please slow down your requests.",
      "RATE_LIMIT",
      429
    );
    this.name = "ArkvoidRateLimitError";
    this.retryAfterMs = retryAfterMs;
  }
}

export class ArkvoidTimeoutError extends ArkvoidError {
  constructor(timeoutMs: number) {
    super(
      `Request timed out after ${timeoutMs}ms`,
      "TIMEOUT",
      408
    );
    this.name = "ArkvoidTimeoutError";
  }
}

export class ArkvoidNetworkError extends ArkvoidError {
  constructor(cause?: Error) {
    super(
      `Network error: ${cause?.message ?? "Unable to connect to ARKVOID"}`,
      "NETWORK_ERROR"
    );
    this.name = "ArkvoidNetworkError";
    if (cause) this.cause = cause;
  }
}

export class ArkvoidServerError extends ArkvoidError {
  constructor(statusCode: number, details?: unknown) {
    super(
      `ARKVOID server error (HTTP ${statusCode})`,
      "SERVER_ERROR",
      statusCode,
      details
    );
    this.name = "ArkvoidServerError";
  }
}

/**
 * Map HTTP status codes to specific error types
 */
export function createErrorFromResponse(
  statusCode: number,
  body: Record<string, unknown>
): ArkvoidError {
  const message = (body.error as string) || `HTTP ${statusCode}`;

  switch (statusCode) {
    case 401:
      return new ArkvoidAuthError(message);
    case 404:
      return new ArkvoidNotFoundError("Agent");
    case 400:
      return new ArkvoidValidationError(message, body.details);
    case 429: {
      const retryAfter = body.retry_after as number | undefined;
      return new ArkvoidRateLimitError(
        retryAfter ? retryAfter * 1000 : undefined
      );
    }
    default:
      return new ArkvoidServerError(statusCode, body);
  }
}

export function isRetryableError(error: unknown): boolean {
  if (error instanceof ArkvoidRateLimitError) return true;
  if (error instanceof ArkvoidTimeoutError) return true;
  if (error instanceof ArkvoidNetworkError) return true;
  if (error instanceof ArkvoidServerError) {
    return error.statusCode !== undefined && error.statusCode >= 500;
  }
  return false;
}
