import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@causewayjs/client": fileURLToPath(
        new URL("../causeway-client/src/index.ts", import.meta.url),
      ),
      "@causewayjs/ts": fileURLToPath(new URL("../causeway-ts/src/index.ts", import.meta.url)),
    },
  },
  test: {
    coverage: {
      include: ["src/**/*.ts"],
      provider: "v8",
      reporter: ["text", "lcov"],
    },
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
