// `causeway-ts` — the tiny zero-dep runtime generated Causeway clients import.
// Static typing lives in the generated `.d.ts`; this file only does plumbing.

export { createLazyClient } from "./client.js";
export { parseSSE } from "./sse.js";
export { DEFAULT_FORWARDED_HEADERS, forwardHeaders } from "./ssr.js";
export { CausewayError, unwrapResult } from "./types.js";
export type { HeaderRecord, HeaderRecordValue, HeaderSource, HeadersLike } from "./ssr.js";
export type {
  CallOptions,
  Err,
  HttpMethod,
  LazyClientConfig,
  Ok,
  ParamDescriptor,
  ParamLocation,
  Result,
  RouteDescriptor,
  RouteMeta,
} from "./types.js";
