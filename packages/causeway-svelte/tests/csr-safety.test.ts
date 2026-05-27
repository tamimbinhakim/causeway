import { describe, expect, it } from "vitest";

describe("CSR safety", () => {
  it("loads `@causewayjs/svelte` without DOM globals", async () => {
    expect(typeof globalThis.window).toBe("undefined");
    expect(typeof globalThis.document).toBe("undefined");

    const mod = await import("../src/index.js");
    expect(typeof mod.createCausewayStores).toBe("function");
  });

  it("loads `@causewayjs/svelte/server` without DOM globals", async () => {
    expect(typeof globalThis.window).toBe("undefined");
    expect(typeof globalThis.document).toBe("undefined");

    const mod = await import("../src/server.js");
    expect(typeof mod.loadQuery).toBe("function");
  });
});
