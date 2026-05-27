import { defineConfig } from "tsup";

export default defineConfig({
  clean: true,
  dts: true,
  entry: ["src/index.ts", "src/server.ts"],
  external: ["solid-js", "@causewayjs/ts"],
  format: ["esm", "cjs"],
  minify: false,
  sourcemap: true,
  splitting: false,
  target: "es2022",
  treeshake: true,
});
