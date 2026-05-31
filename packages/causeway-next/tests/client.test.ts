/**
 * @vitest-environment happy-dom
 */

import { act, createElement } from "react";
import type { ReactElement } from "react";
import { createRoot } from "react-dom/client";
import type { Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createClient } from "@causewayjs/client";
import type {
  CausewayClient,
  DehydratedClient,
  RouteDescriptor,
  RouteMeta,
} from "@causewayjs/client";
import { CausewayProvider, useCausewayClient, useQuery } from "@causewayjs/react";
import { createHydrateClient } from "../src/client.js";

const routes: Record<string, RouteDescriptor> = {
  getCustomer: {
    method: "GET",
    path: "/customers/{id}",
    routeKey: "GET /customers/$id",
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

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
});

describe("createHydrateClient", () => {
  it("hydrates the nearest provider client instead of creating an isolated boundary client", () => {
    const parentClient = createGeneratedClient();
    const factory = vi.fn(() => createGeneratedClient());
    const HydrateClient = createHydrateClient(factory);
    let seenClient: CausewayClient | null = null;

    function Probe() {
      seenClient = useCausewayClient();
      return null;
    }

    render(
      createElement(
        CausewayProvider,
        { client: parentClient },
        createElement(HydrateClient, { state: snapshot("c_1", "first", 1) }, createElement(Probe)),
      ),
    );

    expect(factory).not.toHaveBeenCalled();
    expect(seenClient).toBe(parentClient);
    expect(customerData(parentClient)).toEqual({ id: "first" });

    render(
      createElement(
        CausewayProvider,
        { client: parentClient },
        createElement(HydrateClient, { state: snapshot("c_1", "second", 2) }, createElement(Probe)),
      ),
    );

    expect(factory).not.toHaveBeenCalled();
    expect(seenClient).toBe(parentClient);
    expect(customerData(parentClient)).toEqual({ id: "second" });
  });

  it("hydrates the provider client before rendering boundary children", () => {
    const parentClient = createGeneratedClient();
    const factory = vi.fn(() => createGeneratedClient());
    const HydrateClient = createHydrateClient(factory);
    const seenDuringRender: Array<{ id: string } | undefined> = [];

    function Probe() {
      seenDuringRender.push(customerData(useCausewayClient()));
      return null;
    }

    render(
      createElement(
        CausewayProvider,
        { client: parentClient },
        createElement(HydrateClient, { state: snapshot("c_1", "first", 1) }, createElement(Probe)),
      ),
    );

    expect(factory).not.toHaveBeenCalled();
    expect(seenDuringRender[0]).toEqual({ id: "first" });
  });

  it("notifies already-mounted parent subscribers after a route snapshot arrives", () => {
    const parentClient = createGeneratedClient();
    const factory = vi.fn(() => createGeneratedClient());
    const HydrateClient = createHydrateClient(factory);

    function Probe() {
      const customer = useQuery("GET /customers/$id", { id: "c_1" }, { enabled: false });
      return createElement("span", null, customer.data?.id ?? "loading");
    }

    render(createElement(CausewayProvider, { client: parentClient }, createElement(Probe)));
    expect(container.textContent).toBe("loading");

    render(
      createElement(
        CausewayProvider,
        { client: parentClient },
        createElement(Probe),
        createElement(HydrateClient, { state: snapshot("c_1", "first", 1) }),
      ),
    );

    expect(factory).not.toHaveBeenCalled();
    expect(container.textContent).toBe("first");
  });

  it("keeps one fallback boundary client and hydrates it when snapshots change", () => {
    const factory = vi.fn(() => createGeneratedClient());
    const HydrateClient = createHydrateClient(factory);
    let seenClient: CausewayClient | null = null;

    function Probe() {
      seenClient = useCausewayClient();
      return null;
    }

    render(
      createElement(HydrateClient, { state: snapshot("c_1", "first", 1) }, createElement(Probe)),
    );

    const fallbackClient = seenClient;
    expect(factory).toHaveBeenCalledTimes(1);
    expect(customerData(fallbackClient)).toEqual({ id: "first" });

    render(
      createElement(HydrateClient, { state: snapshot("c_1", "second", 2) }, createElement(Probe)),
    );

    expect(factory).toHaveBeenCalledTimes(1);
    expect(seenClient).toBe(fallbackClient);
    expect(customerData(fallbackClient)).toEqual({ id: "second" });
  });
});

function render(element: ReactElement) {
  act(() => {
    root.render(element);
  });
}

function createGeneratedClient(): CausewayClient {
  return createClient({
    routeMeta,
    loadRoute: (id) => {
      const route = routes[id];
      if (route === undefined) throw new Error(id);
      return route;
    },
  });
}

function snapshot(inputId: string, dataId: string, updatedAt: number): DehydratedClient {
  return {
    version: 1,
    queries: [
      {
        routeKey: "GET /customers/$id",
        input: { id: inputId },
        scope: null,
        data: { id: dataId },
        updatedAt,
      },
    ],
  };
}

function customerData(client: CausewayClient | null): { id: string } | undefined {
  return client?.getData("GET /customers/$id", { id: "c_1" });
}
