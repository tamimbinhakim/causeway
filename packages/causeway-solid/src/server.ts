import { forwardHeaders, unwrapResult } from "@causewayjs/ts";

import type { ArgsOf, DataOf, UnaryKeys } from "./types.js";

type Unary = (args?: unknown, opts?: { headers?: Record<string, string> }) => Promise<unknown>;

/** Call a Causeway method from a SolidStart server function with auth/locale headers forwarded. */
export async function serverQuery<TApi extends object, K extends UnaryKeys<TApi> & string>(
  api: TApi,
  method: K,
  args: ArgsOf<TApi[K]>,
  request: Request,
  options: { forwardHeaders?: readonly string[] } = {},
): Promise<DataOf<TApi[K]>> {
  const headers = forwardHeaders(request, options.forwardHeaders);
  const fn = api[method] as unknown as Unary;
  const value = await fn(args as unknown, { headers });
  return unwrapResult(value) as DataOf<TApi[K]>;
}
