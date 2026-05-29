import { describe, expect, it, vi } from "vitest";

import { createRouteKeyClient } from "../src/client.js";
import type { RouteDescriptor, RouteMeta } from "../src/types.js";

const routes: Record<string, RouteDescriptor> = {
  getCustomer: {
    method: "GET",
    path: "/customers/{id}",
    routeKey: "GET /customers/$id",
    params: [{ name: "id", alias: "id", in: "path" }],
  },
  screenCustomer: {
    method: "POST",
    path: "/customers/{id}/screen",
    routeKey: "POST /customers/$id/screen",
    params: [{ name: "id", alias: "id", in: "path" }],
    refreshes: ["GET /customers/$id"],
  },
};

const routeMeta: RouteMeta[] = Object.entries(routes).map(([id, route]) => ({
  id,
  routeKey: route.routeKey,
  method: route.method,
  path: route.path,
  refreshes: route.refreshes,
  hasArgs: true,
}));

function makeClient(fetch: typeof globalThis.fetch) {
  return createRouteKeyClient({
    baseUrl: "https://api.test",
    fetch,
    routeMeta,
    loadRoute: (id) => {
      const route = routes[id];
      if (route === undefined) throw new Error(id);
      return route;
    },
  });
}

describe("createRouteKeyClient", () => {
  it("dedupes in-flight queries by route key and canonical input", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ id: "c_1" }), {
          headers: { "content-type": "application/json" },
        }),
    );
    const client = makeClient(fetchMock);

    const [a, b] = await Promise.all([
      client.query("GET /customers/$id", { id: "c_1" }),
      client.query("GET /customers/$id", { id: "c_1" }),
    ]);

    expect(a).toEqual({ id: "c_1" });
    expect(b).toEqual({ id: "c_1" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("passes abort signals through to fetch", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn<typeof fetch>(async (_url, init) => {
      expect(init?.signal).toBe(controller.signal);
      return new Response(JSON.stringify({ id: "c_1" }), {
        headers: { "content-type": "application/json" },
      });
    });
    const client = makeClient(fetchMock);

    await client.query("GET /customers/$id", { id: "c_1" }, { signal: controller.signal });
  });

  it("runs declared refreshes after a successful mutation", async () => {
    const fetchMock = vi.fn<typeof fetch>(async (url, init) => {
      if (init?.method === "POST") {
        return new Response(JSON.stringify({ screened: true }), {
          headers: { "content-type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ id: String(url).split("/").pop(), screened: true }), {
        headers: { "content-type": "application/json" },
      });
    });
    const client = makeClient(fetchMock);

    await client.mutate("POST /customers/$id/screen", { id: "c_1" });

    expect(fetchMock.mock.calls.map(([url, init]) => [url, init?.method])).toEqual([
      ["https://api.test/customers/c_1/screen", "POST"],
      ["https://api.test/customers/c_1", "GET"],
    ]);
    expect(client.getData("GET /customers/$id", { id: "c_1" })).toEqual({
      id: "c_1",
      screened: true,
    });
  });

  it("does not refresh after a failed mutation", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response("boom", { status: 500 }));
    const client = makeClient(fetchMock);

    await expect(client.mutate("POST /customers/$id/screen", { id: "c_1" })).rejects.toMatchObject({
      kind: "HttpError",
      status: 500,
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("dehydrates and hydrates cached query data", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ id: "c_1" }), {
          headers: { "content-type": "application/json" },
        }),
    );
    const client = makeClient(fetchMock);
    await client.query("GET /customers/$id", { id: "c_1" });

    const next = makeClient(fetchMock);
    next.hydrate(client.dehydrate());

    expect(next.getData("GET /customers/$id", { id: "c_1" })).toEqual({ id: "c_1" });
  });
});
