import { defineConfig } from "tsup";

export default defineConfig({
  entry: {
    index: "src/index.ts",
  },
  format: ["esm", "cjs"],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  treeshake: true,
  minify: false,
  target: "es2020",
  platform: "neutral",
  outDir: "dist",
  outExtension({ format }) {
    return {
      js: format === "cjs" ? ".cjs" : ".js",
    };
  },
  external: [],
  noExternal: [],
  esbuildOptions(options) {
    // Ensure consistent output
    options.conditions = ["import", "default"];
  },
  banner: {
    js: `/**
 * ARKVOID JavaScript SDK v1.0.0
 * https://arkvoid.cherazen.com
 * @license MIT
 */`,
  },
});
