import { createRoot } from "solid-js";
import { describe, expect, it, vi } from "vitest";

import { CausewayError } from "@causewayjs/ts";

import { createCausewayResources } from "../src/index.js";

type Result<T, E> = { ok: true; data: T } | { ok: false; error: E };
interface Issue {
  id: number;
  title: string;
}
interface IssueNotFound {
  kind: "IssueNotFound";
  issueId: number;
}
interface TestApi {
  getIssue(args: { issueId: number }): Promise<Result<Issue, IssueNotFound>>;
  createIssue(args: { title: string }): Promise<Result<Issue, IssueNotFound>>;
}

function wait(): Promise<void> {
  return new Promise((r) => setTimeout(r, 0));
}

describe("query resource", () => {
  it("unwraps Result.ok onto resource data", async () => {
    const getIssue = vi.fn(async () => ({ data: { id: 1, title: "hi" }, ok: true as const }));
    await createRoot(async (dispose) => {
      const resources = createCausewayResources({ getIssue } as unknown as TestApi);
      const [data, { refetch }] = resources.query("getIssue", () => ({ issueId: 1 }));
      // Resource fires asynchronously; await a microtask cycle
      await wait();
      await wait();
      await refetch();
      expect(data()).toEqual({ id: 1, title: "hi" });
      dispose();
    });
  });

  it("surfaces Result.error via the error signal", async () => {
    const getIssue = vi.fn(async () => ({
      error: { issueId: 99, kind: "IssueNotFound" as const },
      ok: false as const,
    }));
    await createRoot(async (dispose) => {
      const resources = createCausewayResources({ getIssue } as unknown as TestApi);
      const r = resources.query("getIssue", () => ({ issueId: 99 }));
      const [, { refetch }] = r;
      // Refetch throws but the error signal captures the typed shape on a real Error.
      try {
        await refetch();
      } catch {
        // Expected
      }
      expect(r.error()).toBeInstanceOf(CausewayError);
      expect(r.error()).toMatchObject({ issueId: 99, kind: "IssueNotFound" });
      dispose();
    });
  });
});

describe("mutation resource", () => {
  it("calls mutate and tracks state", async () => {
    const createIssue = vi.fn(async () => ({
      data: { id: 7, title: "new" },
      ok: true as const,
    }));
    await createRoot(async (dispose) => {
      const resources = createCausewayResources({ createIssue } as unknown as TestApi);
      const m = resources.mutation("createIssue");
      const result = await m.mutate({ title: "new" });
      expect(result).toEqual({ id: 7, title: "new" });
      expect(m.data()).toEqual({ id: 7, title: "new" });
      expect(m.loading()).toBe(false);
      dispose();
    });
  });
});
