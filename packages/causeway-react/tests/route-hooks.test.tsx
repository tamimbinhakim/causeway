import { act, render, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { createClient } from "@causewayjs/client";

import { CausewayProvider, queryOptions, useMutation, useQuery } from "../src/index.js";
import type { RouteDescriptor, RouteMeta } from "@causewayjs/client";

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

function makeWrapper(fetch: typeof globalThis.fetch, feedback = {}) {
  const client = createClient({
    fetch,
    routeMeta,
    loadRoute: (id) => {
      const route = routes[id];
      if (route === undefined) throw new Error(id);
      return route;
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <CausewayProvider client={client} feedback={feedback}>
        {children}
      </CausewayProvider>
    );
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

describe("route-key React hooks", () => {
  function TypeProbe() {
    const customer = useQuery("GET /customers/$id", { id: "c_1" });
    customer.data?.id.toUpperCase();

    const customerOptions = queryOptions("GET /customers/$id", { id: "c_1" });
    const customerFromOptions = useQuery(customerOptions);
    customerFromOptions.data?.id.toUpperCase();

    const screen = useMutation("POST /customers/$id/screen");
    void screen({ id: "c_1" }).then((data) => data.screened.valueOf());

    // @ts-expect-error input is inferred from the route key
    useQuery("GET /customers/$id", { customerId: "c_1" });
    // @ts-expect-error query hooks only accept GET route keys
    useQuery("POST /customers/$id/screen", { id: "c_1" });
    // @ts-expect-error queryOptions validates input
    queryOptions("GET /customers/$id", { customerId: "c_1" });
    // @ts-expect-error mutation input is inferred from the route key
    void screen({ customerId: "c_1" });
    // @ts-expect-error mutation hooks only accept non-GET route keys
    useMutation("GET /customers/$id");

    return null;
  }
  void TypeProbe;

  it("loads query data through the owned client", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ id: "c_1" }), {
          headers: { "content-type": "application/json" },
        }),
    );

    const { result } = renderHook(
      () => useQuery(queryOptions("GET /customers/$id", { id: "c_1" })),
      makeWrapper(fetchMock),
    );

    await waitFor(() => expect(result.current?.pending).toBe(false));
    expect(result.current?.data).toEqual({ id: "c_1" });
  });

  it("emits app-owned mutation feedback", async () => {
    const feedback = {
      loading: vi.fn(),
      success: vi.fn(),
      error: vi.fn(),
    };
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ screened: true }), {
          headers: { "content-type": "application/json" },
        }),
    );

    const { result } = renderHook(
      () =>
        useMutation("POST /customers/$id/screen", {
          feedback: { loading: "Screening customer...", success: "Customer screened" },
        }),
      makeWrapper(fetchMock, feedback),
    );

    await act(async () => {
      await result.current!({ id: "c_1" });
    });

    expect(result.current?.data).toEqual({ screened: true });
    expect(feedback.loading).toHaveBeenCalledWith("Screening customer...", expect.any(String));
    expect(feedback.success).toHaveBeenCalledWith("Customer screened", expect.any(String));
    expect(feedback.error).not.toHaveBeenCalled();
  });
});
