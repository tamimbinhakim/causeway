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

type QueryArgs<K extends string> = [RegisteredRouteInput<K>] extends [void]
  ? [input: void, request: Request, options?: ServerQueryOptions]
  : [input: RegisteredRouteInput<K>, request: Request, options?: ServerQueryOptions];

interface ServerQueryOptions {
  forwardHeaders?: readonly string[];
  call?: CallOptions;
}

/** Call a Causeway GET route from a SolidStart server function with request headers forwarded. */
export async function serverQuery<K extends RegisteredQueryRouteKey>(
  client: CausewayClient,
  routeKey: K,
  ...args: QueryArgs<K>
): Promise<RegisteredRouteData<K>>;
export async function serverQuery<TData = unknown>(
  client: CausewayClient,
  routeKey: UnregisteredRouteKey,
  input: RouteInputValue,
  request: Request,
  options?: ServerQueryOptions,
): Promise<TData>;
export async function serverQuery<TData = unknown>(
  client: CausewayClient,
  routeKey: string,
  input: RouteInputValue,
  request: Request,
  options: ServerQueryOptions = {},
): Promise<TData> {
  const headers = {
    ...forwardHeaders(request, options.forwardHeaders),
    ...options.call?.headers,
  };
  return await client.query<TData>(routeKey, input, { ...options.call, headers });
}
