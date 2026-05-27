// Generated-client surface against a fetch impl that mimics a real causeway
// server. Companion to `packages/causeway/tests/runtime/test_e2e_smoke.py`.

import { describe, expect, it } from "vitest";

import { createLazyClient } from "../src/index.js";
import type { RouteDescriptor, RouteMeta } from "../src/index.js";

type FetchImpl = typeof globalThis.fetch;

const ROUTES = [
  {
    method: "GET",
    path: "/me",
    name: "me",
    segments: ["me"],
    verb: "list",
    params: [{ name: "authorization", alias: "authorization", in: "header" }],
  },
  {
    method: "GET",
    path: "/posts/{post_id}",
    name: "getPost",
    segments: ["posts"],
    verb: "byId",
    params: [{ name: "postId", alias: "post_id", in: "path" }],
    result: true,
  },
  {
    method: "POST",
    path: "/posts",
    name: "createPost",
    segments: ["posts"],
    verb: "create",
    params: [{ name: "data", alias: "data", in: "body" }],
  },
  {
    method: "GET",
    path: "/posts",
    name: "listPosts",
    segments: ["posts"],
    verb: "list",
    params: [{ name: "tag", alias: "tag", in: "query" }],
  },
  {
    method: "POST",
    path: "/avatar",
    name: "uploadAvatar",
    segments: ["avatar"],
    verb: "create",
    params: [{ name: "file", alias: "file", in: "file" }],
  },
  {
    method: "POST",
    path: "/login",
    name: "login",
    segments: ["login"],
    verb: "create",
    params: [{ name: "form", alias: "form", in: "body" }],
    formBody: true,
  },
  {
    method: "POST",
    path: "/webhooks/stripe",
    name: "stripeWebhook",
    segments: ["webhooks", "stripe"],
    verb: "create",
    params: [{ name: "body", alias: "body", in: "body" }],
    binaryBody: true,
  },
  {
    method: "GET",
    path: "/exports/{id}.csv",
    name: "exportCsv",
    segments: ["exports", "csv"],
    verb: "byId",
    params: [{ name: "id", alias: "id", in: "path" }],
    binaryResponse: true,
  },
  {
    method: "GET",
    path: "/feed",
    name: "feed",
    segments: ["feed"],
    verb: "list",
    params: [{ name: "count", alias: "count", in: "query" }],
    streams: true,
  },
] as const satisfies ReadonlyArray<RouteDescriptor>;

function routeMeta(route: RouteDescriptor): RouteMeta {
  return {
    id: route.name,
    name: route.name,
    segments: route.segments,
    verb: route.verb,
    ...((route.params?.length ?? 0) > 0 ? { hasArgs: true } : {}),
    ...(route.streams ? { streams: true } : {}),
  };
}

const ROUTE_META: RouteMeta[] = ROUTES.map(routeMeta);

type Api = {
  me: {
    list: (a: {
      authorization: string;
    }) => Promise<{ id: number; email: string; createdAt: string }>;
  };
  posts: {
    byId: (a: {
      postId: number;
    }) => Promise<
      { ok: true; data: { id: number; authorId: number } } | { ok: false; error: { kind: string } }
    >;
    create: (a: { data: { title: string; bodyText: string } }) => Promise<{ id: number }>;
    list: (a?: { tag?: string[] }) => Promise<Array<{ id: number }>>;
  };
  avatar: {
    create: (a: { file: Blob }) => Promise<{ bytes: number }>;
  };
  login: {
    create: (a: {
      form: { email: string; password: string };
    }) => Promise<{ token: string; userId: number }>;
  };
  webhooks: {
    stripe: {
      create: (a: { body: Uint8Array }) => Promise<unknown>;
    };
  };
  exports: {
    csv: {
      byId: (a: { id: string }) => Promise<Blob>;
    };
  };
  feed: {
    list: (
      a: { count: number },
      opts?: { signal?: AbortSignal },
    ) => AsyncIterable<{ kind: "tick"; seq: number } | { kind: "done"; total: number }>;
  };
};

function makeServer(): { fetch: FetchImpl; calls: Request[] } {
  const calls: Request[] = [];
  const handlers: Array<[string, (req: Request) => Promise<Response> | Response]> = [
    ["GET /me", () => json({ id: 1, email: "a@x.com", created_at: "2025-01-01" })],
    ["GET /posts/42", () => json({ ok: true, data: { id: 42, author_id: 7 } })],
    ["GET /posts/404", () => json({ ok: false, error: { kind: "PostNotFound", post_id: 404 } })],
    [
      "POST /posts",
      async (req) => {
        const body = (await req.json()) as { title: string; body_text: string };
        if (body.title !== "hi" || body.body_text !== "world") {
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

function createApi(fetch: FetchImpl): Api {
  return createLazyClient<Api>({
    routeMeta: ROUTE_META,
    loadRoute: (id) => {
      const route = ROUTES.find((item) => item.name === id);
      if (route === undefined) throw new Error(id);
      return route;
    },
    fetch,
    baseUrl: "http://test",
  });
}

describe("e2e integration — generated-client surface against a causeway-shaped mock server", () => {
  it("unary GET with header param + snake→camel response translation", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const me = await api.me.list({ authorization: "Bearer tok" });
    expect(me).toEqual({ id: 1, email: "a@x.com", createdAt: "2025-01-01" });

    expect(server.calls[0]!.headers.get("authorization")).toBe("Bearer tok");
  });

  it("path-param GET with Result envelope (ok branch)", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const r = await api.posts.byId({ postId: 42 });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.data).toEqual({ id: 42, authorId: 7 });
  });

  it("path-param GET with Result envelope (err branch — typed)", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const r = await api.posts.byId({ postId: 404 });
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect((r.error as { kind: string }).kind).toBe("PostNotFound");
      expect((r.error as unknown as { postId: number }).postId).toBe(404);
    }
  });

  it("POST body with camel→snake translation", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const r = await api.posts.create({ data: { title: "hi", bodyText: "world" } });
    expect(r).toEqual({ id: 1 });
    const req = server.calls[0]!;
    expect(req.headers.get("content-type")).toContain("application/json");
  });

  it("repeated query param expands to `?tag=a&tag=b`", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const r = await api.posts.list({ tag: ["red", "blue"] });
    expect(r).toEqual([
      { id: 1, tag: "red" },
      { id: 2, tag: "blue" },
    ]);
    const url = new URL(server.calls[0]!.url);
    expect(url.searchParams.getAll("tag")).toEqual(["red", "blue"]);
  });

  it("multipart file upload uses FormData and lets fetch pick the boundary", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const blob = new Blob([new Uint8Array([1, 2, 3, 4, 5])]);
    const r = await api.avatar.create({ file: blob });
    expect(r).toEqual({ bytes: 5 });
    expect(server.calls[0]!.headers.get("content-type")).toMatch(
      /^multipart\/form-data; boundary=/,
    );
  });

  it("formBody routes encode as application/x-www-form-urlencoded with snake_case keys", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const r = await api.login.create({ form: { email: "a@x.com", password: "hunter2" } });
    expect(r.token).toBe("tok-1");
    expect(r.userId).toBe(1);
  });

  it("binaryBody routes pass raw bytes through unmodified", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const payload = new Uint8Array([222, 173, 190, 239]);
    const r = (await api.webhooks.stripe.create({ body: payload })) as { bytes: number };
    expect(r.bytes).toBe(4);
  });

  it("binaryResponse routes hand back a Blob", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const blob = await api.exports.csv.byId({ id: "abc" });
    expect(blob).toBeInstanceOf(Blob);
    const text = await blob.text();
    expect(text).toContain("a,b,c");
  });

  it("streaming route parses SSE frames into AsyncIterable<T>", async () => {
    const server = makeServer();
    const api = createApi(server.fetch);

    const seen: unknown[] = [];
    for await (const ev of api.feed.list({ count: 3 })) {
      seen.push(ev);
    }
    expect(seen).toEqual([
      { kind: "tick", seq: 0 },
      { kind: "tick", seq: 1 },
      { kind: "tick", seq: 2 },
    ]);
  });

  it("streaming route can be cancelled mid-flight", async () => {
    // Build a server that emits frames slowly, give it a controller, abort.
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

    const api = createApi(slowFetch);
    const ac = new AbortController();
    const seen: unknown[] = [];
    for await (const ev of api.feed.list({ count: 100 }, { signal: ac.signal })) {
      seen.push(ev);
      if (seen.length >= 3) ac.abort();
    }
    expect(seen.length).toBeGreaterThanOrEqual(3);
    expect(seen.length).toBeLessThan(100);
    expect(calls[0]!.signal?.aborted).toBe(true);
  });
});
