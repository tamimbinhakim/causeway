// @vitest-environment node
import { describe, expect, it } from "vitest";

describe("CSR safety", () => {
  it("loads `causeway-react` without DOM globals", async () => {
    expect(typeof globalThis.window).toBe("undefined");
    expect(typeof globalThis.document).toBe("undefined");

    const mod = await import("../src/index.js");
    expect(typeof mod.createReactClient).toBe("function");
  });

  it("loads `causeway-react/server` without DOM globals", async () => {
    expect(typeof globalThis.window).toBe("undefined");
    expect(typeof globalThis.document).toBe("undefined");

    const mod = await import("../src/server.js");
    expect(typeof mod.prefetchQuery).toBe("function");
    expect(typeof mod.prefetchQueries).toBe("function");
  });
});
