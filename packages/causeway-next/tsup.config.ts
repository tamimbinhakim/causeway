import { defineConfig, type Options } from "tsup";

const shared: Options = {
  format: ["esm", "cjs"],
  dts: true,
  splitting: false,
  sourcemap: true,
  treeshake: true,
  minify: false,
  target: "es2022",
  external: ["@causewayjs/client", "@causewayjs/react", "react"],
};

export default defineConfig([
  {
    ...shared,
    entry: ["src/index.ts"],
    clean: true,
  },
  {
    ...shared,
    entry: ["src/client.ts"],
    clean: false,
  },
]);
