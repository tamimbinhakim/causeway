import { describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";
import { CausewayError } from "@causewayjs/ts";

import { createCausewayStores } from "../src/index.js";

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
  rawPing(): Promise<{ pong: true }>;
  createIssue(args: { title: string }): Promise<Result<Issue, IssueNotFound>>;
  events(args: { topic: string }): AsyncIterable<{ kind: "tick"; n: number }>;
}

function wait(): Promise<void> {
  return new Promise((r) => setTimeout(r, 0));
}

async function* makeGen() {
  yield { kind: "tick" as const, n: 1 };
  yield { kind: "tick" as const, n: 2 };
}

describe("query store", () => {
  it("unwraps Result.ok onto .data", async () => {
    const getIssue = vi.fn(async () => ({ data: { id: 1, title: "hi" }, ok: true as const }));
    const stores = createCausewayStores({ getIssue } as unknown as TestApi);
    const store = stores.query("getIssue", { issueId: 1 });

    await wait();
    await wait();
    const val = get(store);
    expect(val.status).toBe("success");
    expect(val.data).toEqual({ id: 1, title: "hi" });
    expect(val.error).toBeUndefined();
  });

  it("passes Result.error through .error on rejection", async () => {
    const getIssue = vi.fn(async () => ({
      error: { issueId: 99, kind: "IssueNotFound" as const },
      ok: false as const,
    }));
    const stores = createCausewayStores({ getIssue } as unknown as TestApi);
    const store = stores.query("getIssue", { issueId: 99 });

    await wait();
    await wait();
    const val = get(store);
    expect(val.status).toBe("error");
    expect(val.error).toBeInstanceOf(CausewayError);
    expect(val.error).toMatchObject({ issueId: 99, kind: "IssueNotFound" });
  });

  it("does not fetch when enabled=false", () => {
    const getIssue = vi.fn(async () => ({ data: { id: 1, title: "x" }, ok: true as const }));
    const stores = createCausewayStores({ getIssue } as unknown as TestApi);
    stores.query("getIssue", { issueId: 1 }, { enabled: false });
    expect(getIssue).not.toHaveBeenCalled();
  });
});

describe("mutation store", () => {
  it("calls mutate and exposes data", async () => {
    const createIssue = vi.fn(async () => ({ data: { id: 5, title: "new" }, ok: true as const }));
    const stores = createCausewayStores({ createIssue } as unknown as TestApi);
    const store = stores.mutation("createIssue");

    const out = await get(store).mutate({ title: "new" });
    expect(out).toEqual({ id: 5, title: "new" });
    expect(get(store).status).toBe("success");
  });
});

describe("subscription store", () => {
  it("forwards stream events to onEvent and closes cleanly", async () => {
    const events = vi.fn(() => makeGen());
    const seen: number[] = [];
    const stores = createCausewayStores({ events } as unknown as TestApi);
    const store = stores.subscription("events", { topic: "x" }, (ev) => seen.push(ev.n));
    const unsub = store.subscribe(() => {});

    await wait();
    await wait();
    await wait();
    expect(seen).toEqual([1, 2]);
    expect(get(store).status).toBe("closed");
    unsub();
  });
});
