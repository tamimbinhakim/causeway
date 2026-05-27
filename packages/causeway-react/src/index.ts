export {
  createReactClient,
  type ReactClient,
  type UseCausewaySubscriptionOptions,
  type UseCausewaySubscriptionResult,
} from "./hooks.js";

export {
  buildNamespaceTree,
  computeNamespace,
  type NamespaceEntry,
  type ReactRouteMeta,
  type TreeNode,
} from "./proxy.js";

export type { SubscriptionStatus } from "./types.js";
