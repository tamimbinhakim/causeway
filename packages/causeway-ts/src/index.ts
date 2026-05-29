// `@causewayjs/ts` — the tiny zero-dep transport runtime generated Causeway
// clients import. Public app ergonomics live in route keys, not generated
// method trees.

export { createRouteKeyClient } from "./client.js";
export { parseSSE } from "./sse.js";
export { DEFAULT_FORWARDED_HEADERS, forwardHeaders } from "./ssr.js";
export { CausewayError, unwrapResult } from "./types.js";
export type { HeaderRecord, HeaderRecordValue, HeaderSource, HeadersLike } from "./ssr.js";
export type {
  CallOptions,
  CausewayClient,
  ClientConfig,
  DehydratedClient,
  DehydratedQuery,
  Err,
  HttpMethod,
  Ok,
  ParamDescriptor,
  ParamLocation,
  QueryState,
  Result,
  RouteDescriptor,
  RouteMeta,
} from "./types.js";
