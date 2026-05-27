import { describe, expect, it, vi } from "vitest";

import { createLazyClient } from "../src/client.js";
import type { RouteDescriptor, RouteMeta } from "../src/types.js";

const routes: RouteDescriptor[] = [
  {
    method: "GET",
    path: "/chat",
    name: "chat",
    segments: ["chat"],
    verb: "list",
    streams: true,
  },
];

const routeMeta: RouteMeta[] = routes.map((route) => ({
  id: route.name,
  name: route.name,
  segments: route.segments,
  verb: route.verb,
  ...((route.params?.length ?? 0) > 0 ? { hasArgs: true } : {}),
  ...(route.streams ? { streams: true } : {}),
}));

function createTestClient<TApi extends object = Record<string, unknown>>(config: {
  fetch?: typeof fetch;
}): TApi {
  return createLazyClient<TApi>({
    ...config,
    routeMeta,
    loadRoute: (id) => {
      const route = routes.find((item) => item.name === id);
      if (route === undefined) throw new Error(id);
      return route;
    },
  });
}

function sseStream(frames: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();

  return new ReadableStream({
    start(controller) {
      for (const f of frames) controller.enqueue(enc.encode(f));
      controller.close();
    },
  });
}

describe("streaming client", () => {
  it("yields parsed JSON frames as a typed AsyncIterable", async () => {
    const body = sseStream([
      'data: {"kind":"token","text":"hi"}\n\n',
      'data: {"kind":"token","text":"there"}\n\n',
      "event: done\ndata: {}\n\n",
    ]);

    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(body, {
          status: 200,
          headers: { "content-type": "text/event-stream" },
        }),
    );

    const api = createTestClient({ fetch: fetchMock }) as {
      chat: { list: () => AsyncIterable<{ kind: string; text?: string }> };
    };

    const got: unknown[] = [];
    for await (const ev of api.chat.list()) got.push(ev);

    expect(got).toEqual([
      { kind: "token", text: "hi" },
      { kind: "token", text: "there" },
    ]);
  });

  it("throws on event: error frames", async () => {
    const body = sseStream(['event: error\ndata: {"kind":"RateLimited","retry_after":5}\n\n']);

    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(body, {
          status: 200,
          headers: { "content-type": "text/event-stream" },
        }),
    );

    const api = createTestClient({ fetch: fetchMock }) as {
      chat: { list: () => AsyncIterable<unknown> };
    };

    const run = async () => {
      for await (const ev of api.chat.list()) {
        void ev;
      }
    };

    await expect(run()).rejects.toThrow(/stream error/);
  });

  it("resumes with Last-Event-Id after a mid-stream disconnect", async () => {
    // First connection: yields two events with ids 1 and 2, then drops.
    // Second connection: must see Last-Event-Id: 2 in the request, yields
    // event id 3 + done.
    const calls: { headers: Record<string, string> }[] = [];
    let attempt = 0;

    const fetchMock = vi.fn<typeof fetch>(async (_url, init?: RequestInit) => {
      const headers: Record<string, string> = {};
      const raw = (init?.headers ?? {}) as Record<string, string>;
      for (const k of Object.keys(raw)) headers[k.toLowerCase()] = raw[k]!;
      calls.push({ headers });
      attempt += 1;

      if (attempt === 1) {
        // Tell client retry=1ms so the test doesn't sit on a 1s default.
        const body = sseStream(['retry: 1\nid: 1\ndata: {"n":1}\n\n', 'id: 2\ndata: {"n":2}\n\n']);
        return new Response(body, {
          status: 200,
          headers: { "content-type": "text/event-stream" },
        });
      }
      const body = sseStream(['id: 3\ndata: {"n":3}\n\n', "event: done\ndata: {}\n\n"]);
      return new Response(body, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      });
    });

    const api = createTestClient({ fetch: fetchMock }) as {
      chat: { list: () => AsyncIterable<{ n: number }> };
    };
    const got: number[] = [];
    for await (const ev of api.chat.list()) got.push(ev.n);

    expect(got).toEqual([1, 2, 3]);
    expect(calls).toHaveLength(2);
    expect(calls[0]!.headers["last-event-id"]).toBeUndefined();
    expect(calls[1]!.headers["last-event-id"]).toBe("2");
  });
});
