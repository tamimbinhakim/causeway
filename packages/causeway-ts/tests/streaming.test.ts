import { describe, expect, it, vi } from "vitest";

import { createRouteKeyClient } from "../src/client.js";
import type { CausewayClient, RouteDescriptor, RouteMeta } from "../src/types.js";

const routes: Record<string, RouteDescriptor> = {
  chat: {
    method: "GET",
    path: "/chat",
    routeKey: "GET /chat",
    streams: true,
  },
};

const routeMeta: RouteMeta[] = [
  {
    id: "chat",
    routeKey: "GET /chat",
    method: "GET",
    path: "/chat",
    streams: true,
  },
];

function createTestClient(config: { fetch?: typeof fetch }): CausewayClient {
  return createRouteKeyClient({
    ...config,
    routeMeta,
    loadRoute: (id) => {
      const route = routes[id];
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

    const client = createTestClient({ fetch: fetchMock });
    const got: unknown[] = [];
    for await (const ev of client.stream("GET /chat")) got.push(ev);

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

    const client = createTestClient({ fetch: fetchMock });
    const run = async () => {
      for await (const ev of client.stream("GET /chat")) {
        void ev;
      }
    };

    await expect(run()).rejects.toThrow(/stream error/);
  });

  it("resumes with Last-Event-Id after a mid-stream disconnect", async () => {
    const calls: { headers: Record<string, string> }[] = [];
    let attempt = 0;

    const fetchMock = vi.fn<typeof fetch>(async (_url, init?: RequestInit) => {
      const headers: Record<string, string> = {};
      const raw = (init?.headers ?? {}) as Record<string, string>;
      for (const k of Object.keys(raw)) headers[k.toLowerCase()] = raw[k]!;
      calls.push({ headers });
      attempt += 1;

      if (attempt === 1) {
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

    const client = createTestClient({ fetch: fetchMock });
    const got: number[] = [];
    for await (const ev of client.stream<{ n: number }>("GET /chat")) got.push(ev.n);

    expect(got).toEqual([1, 2, 3]);
    expect(calls).toHaveLength(2);
    expect(calls[0]!.headers["last-event-id"]).toBeUndefined();
    expect(calls[1]!.headers["last-event-id"]).toBe("2");
  });
});
