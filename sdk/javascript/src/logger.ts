/**
 * ARKVOID SDK – Internal Debug Logger
 */

const PREFIX = "[ARKVOID]";

export type LogLevel = "debug" | "info" | "warn" | "error";

export class ArkvoidLogger {
  private debug: boolean;
  private silent: boolean;

  constructor(debug = false, silent = false) {
    this.debug = debug;
    this.silent = silent;
  }

  log(level: LogLevel, ...args: unknown[]): void {
    if (this.silent && level !== "error") return;

    switch (level) {
      case "debug":
        if (!this.debug) return;
        console.debug(PREFIX, ...args);
        break;
      case "info":
        console.info(PREFIX, ...args);
        break;
      case "warn":
        console.warn(PREFIX, ...args);
        break;
      case "error":
        if (!this.silent) console.error(PREFIX, ...args);
        break;
    }
  }

  debugLog(...args: unknown[]): void {
    this.log("debug", ...args);
  }

  info(...args: unknown[]): void {
    this.log("info", ...args);
  }

  warn(...args: unknown[]): void {
    this.log("warn", ...args);
  }

  error(...args: unknown[]): void {
    this.log("error", ...args);
  }
}
