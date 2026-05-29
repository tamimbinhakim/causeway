// Generated-client transport against a fetch impl that mimics a real Causeway
// server. Companion to `packages/causeway/tests/runtime/test_e2e_smoke.py`.

import { describe, expect, it } from "vitest";

import { createRouteKeyClient } from "../src/index.js";
import type { CausewayClient, RouteDescriptor, RouteMeta } from "../src/index.js";

type FetchImpl = typeof globalThis.fetch;

const ROUTES: Record<string, RouteDescriptor> = {
  me: {
    method: "GET",
    path: "/me",
    routeKey: "GET /me",
    params: [{ name: "authorization", alias: "authorization", in: "header" }],
  },
  getPost: {
    method: "GET",
    path: "/posts/{post_id}",
    routeKey: "GET /posts/$post_id",
    params: [{ name: "postId", alias: "post_id", in: "path" }],
    result: true,
  },
  createPost: {
    method: "POST",
    path: "/posts",
    routeKey: "POST /posts",
    params: [{ name: "data", alias: "data", in: "body" }],
  },
  listPosts: {
    method: "GET",
    path: "/posts",
    routeKey: "GET /posts",
    params: [{ name: "tag", alias: "tag", in: "query" }],
  },
  uploadAvatar: {
    method: "POST",
    path: "/avatar",
    routeKey: "POST /avatar",
    params: [{ name: "file", alias: "file", in: "file" }],
  },
  login: {
    method: "POST",
    path: "/login",
    routeKey: "POST /login",
    params: [{ name: "form", alias: "form", in: "body" }],
    formBody: true,
  },
  stripeWebhook: {
    method: "POST",
    path: "/webhooks/stripe",
    routeKey: "POST /webhooks/stripe",
    params: [{ name: "body", alias: "body", in: "body" }],
    binaryBody: true,
  },
  exportCsv: {
    method: "GET",
    path: "/exports/{id}.csv",
    routeKey: "GET /exports/$id.csv",
    params: [{ name: "id", alias: "id", in: "path" }],
    binaryResponse: true,
  },
  feed: {
    method: "GET",
    path: "/feed",
    routeKey: "GET /feed",
    params: [{ name: "count", alias: "count", in: "query" }],
    streams: true,
  },
};

const ROUTE_META: RouteMeta[] = Object.entries(ROUTES).map(([id, route]) => ({
  id,
  routeKey: route.routeKey,
  method: route.method,
  path: route.path,
  ...((route.params?.length ?? 0) > 0 ? { hasArgs: true } : {}),
  ...(route.streams ? { streams: true } : {}),
}));

function makeServer(): { fetch: FetchImpl; calls: Request[] } {
  const calls: Request[] = [];
  const handlers: Array<[string, (req: Request) => Promise<Response> | Response]> = [
    ["GET /me", () => json({ id: 1, email: "a@x.com", created_at: "2025-01-01" })],
    ["GET /posts/42", () => json({ ok: true, data: { id: 42, author_id: 7 } })],
    ["GET /posts/404", () => json({ ok: false, error: { kind: "PostNotFound", post_id: 404 } })],
    [
      "POST /posts",
      async (req) => {
        const body = await req.json();
        if (!hasPostBody(body)) {
          return new Response("bad body", { status: 400 });
        }
        return json({ id: 1 });
      },
    ],
    [
      "GET /posts",
      (req) => {
        const url = new URL(req.url);
        const tags = url.searchParams.getAll("tag");
        return json(tags.map((t, i) => ({ id: i + 1, tag: t })));
      },
    ],
    [
      "POST /avatar",
      async (req) => {
        const form = await req.formData();
        const file = form.get("file") as File | null;
        if (!file) return new Response("missing file", { status: 400 });
        const bytes = await file.arrayBuffer();
        return json({ bytes: bytes.byteLength });
      },
    ],
    [
      "POST /login",
      async (req) => {
        const ct = req.headers.get("content-type") ?? "";
        if (!ct.includes("application/x-www-form-urlencoded")) {
          return new Response(`bad ct: ${ct}`, { status: 400 });
        }
        const text = await req.text();
        return json({ token: "tok-1", user_id: 1, echoed: text });
      },
    ],
    [
      "POST /webhooks/stripe",
      async (req) => {
        const ct = req.headers.get("content-type");
        if (ct !== "application/octet-stream") {
          return new Response(`bad ct: ${ct}`, { status: 400 });
        }
        const bytes = await req.arrayBuffer();
        return json({ bytes: bytes.byteLength });
      },
    ],
    [
      "GET /exports/abc.csv",
      () =>
        new Response("a,b,c\n1,2,3\n", {
          status: 200,
          headers: { "content-type": "text/csv" },
        }),
    ],
    [
      "GET /feed",
      (req) => {
        const url = new URL(req.url);
        const count = Number(url.searchParams.get("count") ?? "0");
        const frames: string[] = [];
        for (let i = 0; i < count; i++) {
          frames.push(`id: ${i}\ndata: {"kind":"tick","seq":${i}}\n\n`);
        }
        frames.push(`event: done\ndata: {"total":${count}}\n\n`);
        return new Response(frames.join(""), {
          status: 200,
          headers: { "content-type": "text/event-stream" },
        });
      },
    ],
  ];

  const fetchImpl: FetchImpl = async (input, init) => {
    const req = new Request(input, init);
    calls.push(req);
    const url = new URL(req.url);
    const key = `${req.method} ${url.pathname}`;
    const handler = handlers.find(([k]) => k === key);
    if (!handler) return new Response(`no route: ${key}`, { status: 404 });
    return handler[1](req);
  };

  return { fetch: fetchImpl, calls };
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

function hasPostBody(value: unknown): boolean {
  if (value === null || typeof value !== "object") return false;
  return (
    "title" in value && value.title === "hi" && "body_text" in value && value.body_text === "world"
  );
}

function createClient(fetch: FetchImpl): CausewayClient {
  return createRouteKeyClient({
    routeMeta: ROUTE_META,
    loadRoute: (id) => {
      const route = ROUTES[id];
      if (route === undefined) throw new Error(id);
      return route;
    },
    fetch,
    baseUrl: "http://test",
  });
}

describe("e2e integration — route-key client against a causeway-shaped mock server", () => {
  it("unary GET with header param + snake→camel response translation", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const me = await api.query("GET /me", { authorization: "Bearer tok" });
    expect(me).toEqual({ id: 1, email: "a@x.com", createdAt: "2025-01-01" });

    expect(server.calls[0]!.headers.get("authorization")).toBe("Bearer tok");
  });

  it("path-param GET unwraps a Result.ok branch", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const post = await api.query("GET /posts/$post_id", { postId: 42 });
    expect(post).toEqual({ id: 42, authorId: 7 });
  });

  it("path-param GET throws a typed Result.error branch", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    await expect(api.query("GET /posts/$post_id", { postId: 404 })).rejects.toMatchObject({
      kind: "PostNotFound",
      postId: 404,
    });
  });

  it("POST body with camel→snake translation", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const r = await api.mutate("POST /posts", { data: { title: "hi", bodyText: "world" } });
    expect(r).toEqual({ id: 1 });
    const req = server.calls[0]!;
    expect(req.headers.get("content-type")).toContain("application/json");
  });

  it("repeated query param expands to `?tag=a&tag=b`", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const r = await api.query("GET /posts", { tag: ["red", "blue"] });
    expect(r).toEqual([
      { id: 1, tag: "red" },
      { id: 2, tag: "blue" },
    ]);
    const url = new URL(server.calls[0]!.url);
    expect(url.searchParams.getAll("tag")).toEqual(["red", "blue"]);
  });

  it("multipart file upload uses FormData and lets fetch pick the boundary", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const blob = new Blob([new Uint8Array([1, 2, 3, 4, 5])]);
    const r = await api.mutate("POST /avatar", { file: blob });
    expect(r).toEqual({ bytes: 5 });
    expect(server.calls[0]!.headers.get("content-type")).toMatch(
      /^multipart\/form-data; boundary=/,
    );
  });

  it("formBody routes encode as application/x-www-form-urlencoded with snake_case keys", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const r = await api.mutate<{ token: string; userId: number }>("POST /login", {
      form: { email: "a@x.com", password: "hunter2" },
    });
    expect(r.token).toBe("tok-1");
    expect(r.userId).toBe(1);
  });

  it("binaryBody routes pass raw bytes through unmodified", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const payload = new Uint8Array([222, 173, 190, 239]);
    const r = await api.mutate<{ bytes: number }>("POST /webhooks/stripe", { body: payload });
    expect(r.bytes).toBe(4);
  });

  it("binaryResponse routes hand back a Blob", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const blob = await api.query<Blob>("GET /exports/$id.csv", { id: "abc" });
    expect(blob).toBeInstanceOf(Blob);
    const text = await blob.text();
    expect(text).toContain("a,b,c");
  });

  it("streaming route parses SSE frames into AsyncIterable<T>", async () => {
    const server = makeServer();
    const api = createClient(server.fetch);

    const seen: unknown[] = [];
    for await (const ev of api.stream("GET /feed", { count: 3 })) {
      seen.push(ev);
    }
    expect(seen).toEqual([
      { kind: "tick", seq: 0 },
      { kind: "tick", seq: 1 },
      { kind: "tick", seq: 2 },
    ]);
  });

  it("streaming route can be cancelled mid-flight", async () => {
    const calls: Request[] = [];
    const slowFetch: FetchImpl = async (input, init) => {
      const req = new Request(input, init);
      calls.push(req);
      const encoder = new TextEncoder();
      const stream = new ReadableStream<Uint8Array>({
        async start(controller) {
          for (let i = 0; i < 100; i++) {
            if (req.signal?.aborted) {
              controller.close();
              return;
            }
            controller.enqueue(encoder.encode(`data: {"kind":"tick","seq":${i}}\n\n`));
            await new Promise((r) => setTimeout(r, 5));
          }
          controller.close();
        },
      });
      return new Response(stream, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      });
    };

    const api = createClient(slowFetch);
    const ac = new AbortController();
    const seen: unknown[] = [];
    for await (const ev of api.stream("GET /feed", { count: 100 }, { signal: ac.signal })) {
      seen.push(ev);
      if (seen.length >= 3) ac.abort();
    }
    expect(seen.length).toBeGreaterThanOrEqual(3);
    expect(seen.length).toBeLessThan(100);
    expect(calls[0]!.signal?.aborted).toBe(true);
  });
});
