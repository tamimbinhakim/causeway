/* eslint-disable require-yield -- intentional in test fixtures */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { CausewayError } from "causeway-ts";

import { createReactClient } from "../src/index.js";
import type { ReactRouteMeta } from "../src/index.js";

type Result<T, E> = { ok: true; data: T } | { ok: false; error: E };

interface Issue {
  id: number;
  title: string;
}
interface IssueNotFound {
  kind: "IssueNotFound";
  issueId: number;
}

interface GeneratedApi {
  issues: {
    byId(args: { issueId: number }): Promise<Result<Issue, IssueNotFound>>;
    create(args: { data: { title: string } }): Promise<Result<Issue, IssueNotFound>>;
  };
  ping: {
    list(): Promise<{ ok: true; pong: true }>;
  };
  search: {
    list(args?: { q?: string; limit?: number }): Promise<Issue[]>;
  };
  events: {
    list(args: { topic: string }): AsyncIterable<{ kind: "tick"; n: number }>;
  };
}

const ROUTES: ReactRouteMeta[] = [
  {
    id: "getIssue",
    name: "getIssue",
    segments: ["issues"],
    verb: "byId",
    hasArgs: true,
  },
  { id: "rawPing", name: "rawPing", segments: ["ping"], verb: "list" },
  {
    id: "search",
    name: "search",
    segments: ["search"],
    verb: "list",
    hasArgs: true,
  },
  {
    id: "createIssue",
    name: "createIssue",
    segments: ["issues"],
    verb: "create",
    hasArgs: true,
  },
  {
    id: "events",
    name: "events",
    segments: ["events"],
    verb: "list",
    hasArgs: true,
    streams: true,
  },
];

function buildClient(api: PartialGeneratedApi) {
  return createReactClient<GeneratedApi>(api as GeneratedApi, ROUTES);
}

type PartialGeneratedApi = {
  issues?: {
    byId?: GeneratedApi["issues"]["byId"];
    create?: GeneratedApi["issues"]["create"];
  };
  ping?: {
    list?: GeneratedApi["ping"]["list"];
  };
  search?: {
    list?: GeneratedApi["search"]["list"];
  };
  events?: {
    list?: GeneratedApi["events"]["list"];
  };
};

type Equal<A, B> =
  (<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2 ? true : false;
type Expect<T extends true> = T;

declare const typedApi: ReturnType<typeof buildClient>;
type ByIdQuery = ReturnType<typeof typedApi.issues.byId.useQuery>;
type PingQuery = ReturnType<typeof typedApi.ping.list.useQuery>;
type CreateMutation = ReturnType<typeof typedApi.issues.create.useMutation>;

type _ByIdQueryData = Expect<Equal<ByIdQuery["data"], Issue | undefined>>;
type _ByIdQueryError = Expect<Equal<ByIdQuery["error"], IssueNotFound | null>>;
type _PingQueryData = Expect<Equal<PingQuery["data"], { ok: true; pong: true } | undefined>>;
type _CreateMutationData = Expect<Equal<CreateMutation["data"], Issue | undefined>>;
type _CreateMutationError = Expect<Equal<CreateMutation["error"], IssueNotFound | null>>;

function typeAssertions() {
  typedApi.issues.byId.useQuery({ issueId: 1 });
  typedApi.ping.list.useQuery({ enabled: false });
  typedApi.search.list.useQuery({ q: "open", limit: 10 });
  typedApi.search.list.useQuery(undefined, { enabled: false });
  typedApi.search.list.queryOptions({ q: "open" }, { staleTime: 1000 });
  typedApi.issues.create.useMutation().mutate({ data: { title: "ok" } });
  typedApi.events.list.useSubscription(
    { topic: "builds" },
    {
      onEvent: (event) => {
        event.n.toFixed();
        // @ts-expect-error stream event payload is typed
        void event.missing;
      },
    },
  );

  // @ts-expect-error issueId must be a number
  typedApi.issues.byId.useQuery({ issueId: "1" });
  // @ts-expect-error required route args cannot be omitted
  typedApi.issues.byId.useQuery();
  // @ts-expect-error no-arg routes accept options, not route args
  typedApi.ping.list.queryKey({});
  // @ts-expect-error mutation variables are inferred from the generated route args
  typedApi.issues.create.useMutation().mutate({ data: { title: 1 } });
}

void typeAssertions;

function makeWrapper() {
  // retry: false so a single rejection lands on `.error` immediately.
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function renderHook<T>(hook: () => T, Wrapper: (p: { children: ReactNode }) => ReactNode) {
  const result: { current: T | null } = { current: null };
  function Probe() {
    result.current = hook();
    return null;
  }
  const utils = render(<Probe />, { wrapper: Wrapper });
  return { result, ...utils };
}

describe("useQuery", () => {
  it("builds reusable query options under the nested namespace", async () => {
    const getIssue = vi.fn(async () => ({ ok: true as const, data: { id: 2, title: "opts" } }));
    const api = buildClient({ issues: { byId: getIssue } });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    await client.prefetchQuery(api.issues.byId.queryOptions({ issueId: 2 }));
    expect(client.getQueryData(["getIssue", { issueId: 2 }])).toEqual({ id: 2, title: "opts" });
  });

  it("dispatches through the nested generated API leaf", async () => {
    const search = vi.fn(async () => [{ id: 1 }]);
    const api = createReactClient<{
      search: { list(args: { q: string }): Promise<{ id: number }[]> };
    }>({ search: { list: search } }, [
      {
        id: "search",
        name: "search",
        segments: ["search"],
        verb: "list",
        hasArgs: true,
      },
    ]);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    await client.prefetchQuery(api.search.list.queryOptions({ q: "term" }));
    expect(search).toHaveBeenCalledWith(
      { q: "term" },
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("queryKey echoes the operation name + args", () => {
    const api = buildClient({});
    expect(api.issues.byId.queryKey({ issueId: 3 })).toEqual(["getIssue", { issueId: 3 }]);
  });

  it("returns Result.ok data", async () => {
    const getIssue = vi.fn(async () => ({ ok: true as const, data: { id: 1, title: "hi" } }));
    const api = buildClient({ issues: { byId: getIssue } });

    const { result } = renderHook(() => api.issues.byId.useQuery({ issueId: 1 }), makeWrapper());

    await waitFor(() => expect(result.current?.isSuccess).toBe(true));
    expect(result.current?.data).toEqual({ id: 1, title: "hi" });
  });

  it("surfaces Result.error on .error", async () => {
    const err = { kind: "IssueNotFound" as const, issueId: 99 };
    const getIssue = vi.fn(async () => ({ ok: false as const, error: err }));
    const api = buildClient({ issues: { byId: getIssue } });

    const { result } = renderHook(() => api.issues.byId.useQuery({ issueId: 99 }), makeWrapper());

    await waitFor(() => expect(result.current?.isError).toBe(true));
    const thrown = result.current?.error as unknown;
    expect(thrown).toBeInstanceOf(CausewayError);
    expect(thrown).toMatchObject(err);
  });

  it("passes non-Result returns through untouched", async () => {
    // `{ ok: true, pong: true }` has no `data`/`error` keys — not an envelope.
    const rawPing = vi.fn(async () => ({ ok: true as const, pong: true as const }));
    const api = buildClient({ ping: { list: rawPing } });

    const { result } = renderHook(() => api.ping.list.useQuery(), makeWrapper());

    await waitFor(() => expect(result.current?.isSuccess).toBe(true));
    expect(result.current?.data).toEqual({ ok: true, pong: true });
  });

  it("forwards args and signal to the api method", async () => {
    const getIssue = vi.fn(async () => ({ ok: true as const, data: { id: 7, title: "x" } }));
    const api = buildClient({ issues: { byId: getIssue } });

    const { result } = renderHook(() => api.issues.byId.useQuery({ issueId: 7 }), makeWrapper());

    await waitFor(() => expect(result.current?.isSuccess).toBe(true));
    expect(getIssue).toHaveBeenCalledWith(
      { issueId: 7 },
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });
});

describe("useMutation", () => {
  it("returns Result.ok data on success", async () => {
    const createIssue = vi.fn(async () => ({ ok: true as const, data: { id: 5, title: "new" } }));
    const api = buildClient({ issues: { create: createIssue } });

    const { result } = renderHook(() => api.issues.create.useMutation(), makeWrapper());

    await act(async () => {
      await result.current!.mutateAsync({ data: { title: "new" } });
    });
    await waitFor(() => expect(result.current?.data).toEqual({ id: 5, title: "new" }));
  });

  it("rejects with Result.error and lands it on .error", async () => {
    const err = { kind: "IssueNotFound" as const, issueId: 1 };
    const createIssue = vi.fn(async () => ({ ok: false as const, error: err }));
    const api = buildClient({ issues: { create: createIssue } });

    const { result } = renderHook(() => api.issues.create.useMutation(), makeWrapper());

    await act(async () => {
      await expect(result.current!.mutateAsync({ data: { title: "x" } })).rejects.toMatchObject(
        err,
      );
    });
    await waitFor(() => {
      const thrown = result.current?.error as unknown;
      expect(thrown).toBeInstanceOf(CausewayError);
      expect(thrown).toMatchObject(err);
    });
  });
});

async function* twoTicks(): AsyncIterable<{ kind: "tick"; n: number }> {
  yield { kind: "tick", n: 1 };
  yield { kind: "tick", n: 2 };
}

async function* immediateThrow(): AsyncIterable<unknown> {
  throw new Error("boom");
}

describe("useSubscription", () => {
  it("delivers events and transitions to closed when the stream ends", async () => {
    const api = buildClient({ events: { list: () => twoTicks() } });

    const received: unknown[] = [];
    const { result } = renderHook(
      () =>
        api.events.list.useSubscription(
          { topic: "x" },
          { onEvent: (ev: unknown) => received.push(ev) },
        ),
      makeWrapper(),
    );

    await waitFor(() => expect(result.current?.status).toBe("closed"));
    expect(received).toEqual([
      { kind: "tick", n: 1 },
      { kind: "tick", n: 2 },
    ]);
  });

  it("aborts on unmount", async () => {
    let aborted = false;
    // Held open indefinitely; resolves only on abort so the hook tears it down.
    async function* events(_a: unknown, opts: { signal?: AbortSignal }): AsyncIterable<unknown> {
      opts.signal?.addEventListener("abort", () => {
        aborted = true;
      });
      await new Promise((resolve) => opts.signal?.addEventListener("abort", resolve));
    }
    const api = buildClient({ events: { list: events as GeneratedApi["events"]["list"] } });

    const { unmount, result } = renderHook(
      () => api.events.list.useSubscription({ topic: "y" }, { onEvent: () => {} }),
      makeWrapper(),
    );

    await waitFor(() => expect(result.current?.status).toBe("open"));
    unmount();
    await waitFor(() => expect(aborted).toBe(true));
  });

  it("stays idle when enabled is false", () => {
    const events = vi.fn();
    const api = buildClient({ events: { list: events as GeneratedApi["events"]["list"] } });

    const { result } = renderHook(
      () => api.events.list.useSubscription({ topic: "z" }, { enabled: false, onEvent: () => {} }),
      makeWrapper(),
    );

    expect(result.current?.status).toBe("idle");
    expect(events).not.toHaveBeenCalled();
  });

  it("transitions to error and surfaces the thrown value", async () => {
    const api = buildClient({
      events: { list: immediateThrow as unknown as GeneratedApi["events"]["list"] },
    });

    const { result } = renderHook(
      () => api.events.list.useSubscription({ topic: "q" }, { onEvent: () => {} }),
      makeWrapper(),
    );

    await waitFor(() => expect(result.current?.status).toBe("error"));
    expect(result.current?.error).toBeInstanceOf(Error);
  });
});
