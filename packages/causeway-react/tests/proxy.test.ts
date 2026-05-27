import { describe, expect, it } from "vitest";
import { buildNamespaceTree, computeNamespace } from "../src/proxy.js";

describe("computeNamespace", () => {
  it("uses generated namespace metadata directly", () => {
    expect(
      computeNamespace({
        id: "getCustomer",
        name: "getCustomer",
        segments: ["customers"],
        verb: "byId",
        hasArgs: true,
      }),
    ).toEqual({
      segments: ["customers"],
      verb: "byId",
      operationName: "getCustomer",
      hasArgs: true,
    });
  });
});

describe("buildNamespaceTree", () => {
  it("builds nested namespaces from generated descriptors", () => {
    const tree = buildNamespaceTree([
      {
        id: "listCustomers",
        name: "listCustomers",
        segments: ["customers"],
        verb: "list",
      },
      {
        id: "placeHold",
        name: "placeHold",
        segments: ["customers", "holds"],
        verb: "place",
        hasArgs: true,
      },
    ]);

    const customers = tree.children.get("customers");
    expect(customers?.leaves.get("list")?.operationName).toBe("listCustomers");
    expect(customers?.children.get("holds")?.leaves.get("place")?.hasArgs).toBe(true);
  });

  it("rejects duplicate generated namespace leaves", () => {
    expect(() =>
      buildNamespaceTree([
        {
          id: "listCustomers",
          name: "listCustomers",
          segments: ["customers"],
          verb: "list",
        },
        {
          id: "allCustomers",
          name: "allCustomers",
          segments: ["customers"],
          verb: "list",
        },
      ]),
    ).toThrow(/duplicate generated namespace leaf customers\.list/);
  });
});
