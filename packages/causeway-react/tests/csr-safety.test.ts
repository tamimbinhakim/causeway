// @vitest-environment node
import { describe, expect, it } from "vitest";

describe("CSR safety", () => {
  it("loads `@causewayjs/react` without DOM globals", async () => {
    expect(typeof globalThis.window).toBe("undefined");
    expect(typeof globalThis.document).toBe("undefined");

    const mod = await import("../src/index.js");
    expect(typeof mod.CausewayProvider).toBe("function");
    expect(typeof mod.useQuery).toBe("function");
  });
});
