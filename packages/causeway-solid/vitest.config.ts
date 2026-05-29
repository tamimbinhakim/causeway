import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
import solid from "vite-plugin-solid";

export default defineConfig({
  plugins: [solid()],
  resolve: {
    alias: {
      "@causewayjs/client": fileURLToPath(
        new URL("../causeway-client/src/index.ts", import.meta.url),
      ),
      "@causewayjs/ts": fileURLToPath(new URL("../causeway-ts/src/index.ts", import.meta.url)),
    },
    conditions: ["development", "browser"],
  },
  test: {
    coverage: {
      include: ["src/**/*.ts"],
      provider: "v8",
      reporter: ["text", "lcov"],
    },
    environment: "happy-dom",
    include: ["tests/**/*.test.ts"],
    server: { deps: { inline: [/solid-js/] } },
  },
});
