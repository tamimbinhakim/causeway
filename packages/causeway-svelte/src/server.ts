import { forwardHeaders } from "@causewayjs/client";
import type {
  CallOptions,
  CausewayClient,
  RegisteredQueryRouteKey,
  RegisteredRouteData,
  RegisteredRouteInput,
  RouteInputValue,
  UnregisteredRouteKey,
} from "@causewayjs/client";

export interface SvelteRequestLike {
  request: Request;
}

type QueryArgs<K extends string> = [RegisteredRouteInput<K>] extends [void]
  ? [input: void, event: SvelteRequestLike, options?: LoadQueryOptions]
  : [input: RegisteredRouteInput<K>, event: SvelteRequestLike, options?: LoadQueryOptions];

interface LoadQueryOptions {
  forwardHeaders?: readonly string[];
  call?: CallOptions;
}

/** Call a Causeway GET route from a SvelteKit server load with request headers forwarded. */
export async function loadQuery<K extends RegisteredQueryRouteKey>(
  client: CausewayClient,
  routeKey: K,
  ...args: QueryArgs<K>
): Promise<RegisteredRouteData<K>>;
export async function loadQuery<TData = unknown>(
  client: CausewayClient,
  routeKey: UnregisteredRouteKey,
  input: RouteInputValue,
  event: SvelteRequestLike,
  options?: LoadQueryOptions,
): Promise<TData>;
export async function loadQuery<TData = unknown>(
  client: CausewayClient,
  routeKey: string,
  input: RouteInputValue,
  event: SvelteRequestLike,
  options: LoadQueryOptions = {},
): Promise<TData> {
  const headers = {
    ...forwardHeaders(event.request, options.forwardHeaders),
    ...options.call?.headers,
  };
  return await client.query<TData>(routeKey, input, { ...options.call, headers });
}
