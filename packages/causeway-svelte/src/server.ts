import { forwardHeaders, unwrapResult } from "causeway-ts";

import type { ArgsOf, DataOf, UnaryKeys } from "./types.js";

type Unary = (args?: unknown, opts?: { headers?: Record<string, string> }) => Promise<unknown>;

export interface SvelteRequestLike {
  request: Request;
}

/** Call a Causeway method from a SvelteKit server load with auth/locale headers forwarded. */
export async function loadQuery<TApi extends object, K extends UnaryKeys<TApi> & string>(
  api: TApi,
  method: K,
  args: ArgsOf<TApi[K]>,
  event: SvelteRequestLike,
  options: { forwardHeaders?: readonly string[] } = {},
): Promise<DataOf<TApi[K]>> {
  const headers = forwardHeaders(event.request, options.forwardHeaders);
  const fn = api[method] as unknown as Unary;
  const value = await fn(args as unknown, { headers });
  return unwrapResult(value) as DataOf<TApi[K]>;
}
