import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["components/**/*.test.tsx", "lib/**/*.test.ts", "lib/**/*.test.tsx"],
    exclude: ["tests/e2e/**", "node_modules/**"]
  },
  esbuild: {
    jsx: "automatic"
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname)
    }
  }
});
