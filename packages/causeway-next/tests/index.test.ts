import { isValidElement } from "react";
import { describe, expect, it, vi } from "vitest";

import { createClient } from "@causewayjs/client";
import type { CausewayClient, ClientConfig, RouteDescriptor, RouteMeta } from "@causewayjs/client";
import type { HydrateClientProps } from "../src/client.js";

import {
  createServerHydration,
  createServerClient,
  hydrate,
  prefetch,
  prefetchMany,
  prepareHydration,
  queryOptions,
} from "../src/index.js";

interface Customer {
  id: string;
}

interface Screening {
  screened: boolean;
}

declare module "@causewayjs/client" {
  interface Register {
    routeKey: "GET /customers/$id" | "POST /customers/$id/screen";
    queryRouteKey: "GET /customers/$id";
    mutationRouteKey: "POST /customers/$id/screen";
    routeInput: {
      "GET /customers/$id": { id: string };
      "POST /customers/$id/screen": { id: string };
    };
    routeData: {
      "GET /customers/$id": Customer;
      "POST /customers/$id/screen": Screening;
    };
    routeError: {
      "GET /customers/$id": Error;
      "POST /customers/$id/screen": Error;
    };
  }
}

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
  },
};

const routeMeta: RouteMeta[] = Object.entries(routes).map(([id, route]) => ({
  id,
  routeKey: route.routeKey,
  method: route.method,
  path: route.path,
  hasArgs: true,
}));

type GeneratedClientOptions = Omit<ClientConfig, "routeMeta" | "loadRoute">;

function createGeneratedClient(options: GeneratedClientOptions = {}): CausewayClient {
  return createClient({
    ...options,
    routeMeta,
    loadRoute: (id) => {
      const route = routes[id];
      if (route === undefined) throw new Error(id);
      return route;
    },
  });
}

function TestHydrateClient(_props: HydrateClientProps) {
  return null;
}

async function TypeProbe() {
  const client = createServerClient(createGeneratedClient, {
    baseUrl: "https://api.test",
    headers: new Headers(),
  });
  const customer = await prefetch(client, "GET /customers/$id", { id: "c_1" });
  customer.id.toUpperCase();

  const customerQuery = queryOptions("GET /customers/$id", { id: "c_1" });
  await prefetch(client, customerQuery);
  await prefetchMany(client, customerQuery, ["GET /customers/$id", { id: "c_1" }]);
  const hydration = createServerHydration(createGeneratedClient, {
    baseUrl: "https://api.test",
    headers: new Headers(),
    HydrateClient: TestHydrateClient,
  });
  const hydratedCustomer = await hydration.prefetch("GET /customers/$id", { id: "c_1" });
  hydratedCustomer.id.toUpperCase();
  hydration.hydrate(null);
  hydration.HydrateClient({ children: null });
  await prepareHydration(createGeneratedClient, {
    prefetch: [customerQuery],
  });
  hydrate(createGeneratedClient, { version: 1, queries: [] }, { baseUrl: "/api" });

  // @ts-expect-error input is inferred from the route key
  await prefetch(client, "GET /customers/$id", { customerId: "c_1" });
  // @ts-expect-error prefetch only accepts GET route keys
  await prefetch(client, "POST /customers/$id/screen", { id: "c_1" });
  // @ts-expect-error prefetchMany validates each tuple
  await prefetchMany(client, ["GET /customers/$id", { customerId: "c_1" }]);
  // @ts-expect-error queryOptions validates input
  queryOptions("GET /customers/$id", { customerId: "c_1" });
  await prepareHydration(createGeneratedClient, {
    prefetch: [
      queryOptions("GET /customers/$id", { id: "c_1" }),
      // @ts-expect-error prepareHydration validates tuple route keys
      ["POST /customers/$id/screen", { id: "c_1" }],
    ],
  });
}
void TypeProbe;

describe("@causewayjs/next hydration helpers", () => {
  it("creates a server client from the generated client factory", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(
      async (_url, init) =>
        new Response(JSON.stringify({ id: readAuth(init) }), {
          headers: { "content-type": "application/json" },
        }),
    );
    const client = createServerClient(createGeneratedClient, {
      baseUrl: "https://api.test",
      fetch,
      headers: new Headers({ authorization: "Bearer user" }),
    });

    await prefetch(client, "GET /customers/$id", { id: "c_1" });

    expect(fetch).toHaveBeenCalledWith(
      "https://api.test/customers/c_1",
      expect.objectContaining({
        headers: expect.objectContaining({ authorization: "Bearer user" }),
        method: "GET",
      }),
    );
  });

  it("prefetches many routes and returns the same client", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(
      async (url) =>
        new Response(JSON.stringify({ id: String(url).split("/").pop() }), {
          headers: { "content-type": "application/json" },
        }),
    );
    const client = createGeneratedClient({ baseUrl: "https://api.test", fetch });

    const returned = await prefetchMany(
      client,
      queryOptions("GET /customers/$id", { id: "c_1" }),
      ["GET /customers/$id", { id: "c_1" }],
      ["GET /customers/$id", { id: "c_2" }],
    );

    expect(returned).toBe(client);
    expect(client.getData("GET /customers/$id", { id: "c_1" })).toEqual({ id: "c_1" });
    expect(client.getData("GET /customers/$id", { id: "c_2" })).toEqual({ id: "c_2" });
  });

  it("creates a React Query-style server hydration scope", async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(
      async (url) =>
        new Response(JSON.stringify({ id: String(url).split("/").pop() }), {
          headers: { "content-type": "application/json" },
        }),
    );
    const causeway = createServerHydration(createGeneratedClient, {
      baseUrl: "https://api.test",
      fetch,
      HydrateClient: TestHydrateClient,
    });

    const customer = await causeway.prefetch("GET /customers/$id", { id: "c_1" });
    const element = causeway.hydrate("child");
    const boundary = causeway.HydrateClient({ children: "child" });

    expect(customer).toEqual({ id: "c_1" });
    expect(causeway.client.getData("GET /customers/$id", { id: "c_1" })).toEqual({ id: "c_1" });
    expect(causeway.dehydrate().queries).toHaveLength(1);
    expect(causeway.snapshot()).toEqual(causeway.dehydrate());
    expect(isValidElement(element)).toBe(true);
    expect(element.type).toBe(TestHydrateClient);
    expect((element.props as HydrateClientProps).state?.queries).toHaveLength(1);
    expect((element.props as HydrateClientProps).children).toBe("child");
    expect((boundary.props as HydrateClientProps).state?.queries).toHaveLength(1);
  });

  it("warns in dev when a server hydration scope prefetched but never rendered its boundary", async () => {
    vi.useFakeTimers();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const fetch = vi.fn<typeof globalThis.fetch>(
      async (url) =>
        new Response(JSON.stringify({ id: String(url).split("/").pop() }), {
          headers: { "content-type": "application/json" },
        }),
    );
    const causeway = createServerHydration(createGeneratedClient, {
      baseUrl: "https://api.test",
      fetch,
      HydrateClient: TestHydrateClient,
    });

    await causeway.prefetch("GET /customers/$id", { id: "c_1" });
    vi.runAllTimers();

    expect(warn).toHaveBeenCalledWith(expect.stringContaining("HydrateClient"));
    warn.mockRestore();
    vi.useRealTimers();
  });

  it("prepares a hydration snapshot and hydrates a browser client from a factory", async () => {
    const serverFetch = vi.fn<typeof globalThis.fetch>(
      async (url) =>
        new Response(JSON.stringify({ id: String(url).split("/").pop() }), {
          headers: { "content-type": "application/json" },
        }),
    );

    const { client: serverClient, snapshot } = await prepareHydration(createGeneratedClient, {
      baseUrl: "https://api.test",
      fetch: serverFetch,
      prefetch: [queryOptions("GET /customers/$id", { id: "c_1" })],
    });

    expect(serverClient.getData("GET /customers/$id", { id: "c_1" })).toEqual({ id: "c_1" });
    expect(snapshot.queries).toHaveLength(1);

    const browserFetch = vi.fn<typeof globalThis.fetch>();
    const browserClient = hydrate(createGeneratedClient, snapshot, {
      baseUrl: "/api",
      fetch: browserFetch,
    });

    expect(browserClient.getData("GET /customers/$id", { id: "c_1" })).toEqual({ id: "c_1" });
    expect(browserFetch).not.toHaveBeenCalled();
  });
});

function readAuth(init: RequestInit | undefined): string | undefined {
  const headers = init?.headers;
  if (headers == null || Array.isArray(headers) || headers instanceof Headers) return undefined;
  return (headers as Record<string, string>).authorization;
}
