import { describe, expect, it } from "vitest";

import { DEFAULT_FORWARDED_HEADERS, forwardHeaders } from "../src/ssr.js";

describe("forwardHeaders", () => {
  it("forwards the default subset, lowercased", () => {
    const req = new Request("https://example.com/", {
      headers: {
        Cookie: "session=abc",
        Authorization: "Bearer xyz",
        "X-CSRF-Token": "csrf",
        "X-Request-Id": "req-1",
        "Content-Type": "application/json",
        "User-Agent": "test",
      },
    });

    const forwarded = forwardHeaders(req);

    expect(forwarded["cookie"]).toBe("session=abc");
    expect(forwarded["authorization"]).toBe("Bearer xyz");
    expect(forwarded["x-csrf-token"]).toBe("csrf");
    expect(forwarded["x-request-id"]).toBe("req-1");
    expect(forwarded["content-type"]).toBeUndefined();
    expect(forwarded["user-agent"]).toBeUndefined();
  });

  it("accepts a Headers instance directly", () => {
    const headers = new Headers({ cookie: "k=v" });
    expect(forwardHeaders(headers)["cookie"]).toBe("k=v");
  });

  it("accepts plain header records", () => {
    const forwarded = forwardHeaders({
      Cookie: "session=abc",
      AUTHORIZATION: "Bearer xyz",
      "X-Forwarded-For": ["10.0.0.1", "10.0.0.2"],
      "Content-Type": "application/json",
    });

    expect(forwarded["cookie"]).toBe("session=abc");
    expect(forwarded["authorization"]).toBe("Bearer xyz");
    expect(forwarded["x-forwarded-for"]).toBe("10.0.0.1, 10.0.0.2");
    expect(forwarded["content-type"]).toBeUndefined();
  });

  it("accepts request-like objects with plain header records", () => {
    const forwarded = forwardHeaders({
      headers: {
        Cookie: "session=abc",
        "X-Request-Id": "req-2",
      },
    });

    expect(forwarded["cookie"]).toBe("session=abc");
    expect(forwarded["x-request-id"]).toBe("req-2");
  });

  it("accepts read-only Headers-like values", () => {
    const headers = {
      get(name: string) {
        return name.toLowerCase() === "authorization" ? "Bearer readonly" : null;
      },
    };

    expect(forwardHeaders(headers)["authorization"]).toBe("Bearer readonly");
  });

  it("honors a custom name list", () => {
    const req = new Request("https://example.com/", {
      headers: { "X-Custom": "yes", Cookie: "session=abc" },
    });
    const out = forwardHeaders(req, ["x-custom"]);
    expect(out["x-custom"]).toBe("yes");
    expect(out["cookie"]).toBeUndefined();
  });

  it("omits absent headers", () => {
    const req = new Request("https://example.com/", { headers: { Cookie: "k=v" } });
    expect("authorization" in forwardHeaders(req)).toBe(false);
  });

  it("accepts nullish sources", () => {
    expect(forwardHeaders(null)).toEqual({});
    expect(forwardHeaders(undefined)).toEqual({});
  });

  it("reports unawaited async header sources clearly", () => {
    const source = Promise.resolve(new Headers({ cookie: "k=v" }));

    expect(() => forwardHeaders(source as unknown as Parameters<typeof forwardHeaders>[0])).toThrow(
      /await headers/,
    );
  });

  it("exports the default forwarded names", () => {
    expect(DEFAULT_FORWARDED_HEADERS).toContain("cookie");
    expect(DEFAULT_FORWARDED_HEADERS).toContain("authorization");
  });
});
