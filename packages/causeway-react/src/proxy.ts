import type { RouteMeta } from "@causewayjs/ts";

/** Namespace-tree builder for the React client. */

export type ReactRouteMeta = RouteMeta;

export interface NamespaceEntry {
  /** Literal generated namespace segments. */
  segments: readonly string[];
  /** Generated leaf verb (`list` / `byId` / `create` / `release` / ...). */
  verb: string;
  /** Stable operation key used for query keys. */
  operationName: string;
  /** Whether the generated API method expects an args object before options. */
  hasArgs: boolean;
}

export interface TreeNode {
  children: Map<string, TreeNode>;
  /** verb -> entry */
  leaves: Map<string, NamespaceEntry>;
}

export function computeNamespace(route: ReactRouteMeta): NamespaceEntry {
  return {
    segments: route.segments,
    verb: route.verb,
    operationName: route.name,
    hasArgs: route.hasArgs === true,
  };
}

export function buildNamespaceTree(routes: readonly ReactRouteMeta[]): TreeNode {
  const root: TreeNode = { children: new Map(), leaves: new Map() };
  for (const route of routes) {
    const entry = computeNamespace(route);
    let cursor = root;
    for (const seg of entry.segments) {
      let next = cursor.children.get(seg);
      if (next === undefined) {
        next = { children: new Map(), leaves: new Map() };
        cursor.children.set(seg, next);
      }
      cursor = next;
    }
    if (cursor.leaves.has(entry.verb)) {
      throw new Error(
        `Causeway React: duplicate generated namespace leaf ${[...entry.segments, entry.verb].join(
          ".",
        )}`,
      );
    }
    cursor.leaves.set(entry.verb, entry);
  }
  return root;
}
