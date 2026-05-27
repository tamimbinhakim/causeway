/**
 * React hooks for Causeway clients.
 *
 * Single public entry: {@link createReactClient}. Pass the generated
 * `createApi(...)` result and the generated `routeMeta` array; get back a
 * tRPC-style nested namespace:
 *
 * ```ts
 * const api = createReactClient(apiClient, routeMeta);
 *
 * api.customers.list.useQuery({ limit: 50 });
 * api.customers.byId.useQuery({ id });
 * api.customers.create.useMutation();
 * api.customers.holds.list.useQuery({ id });
 * api.notifications.stream.useSubscription(args, { onEvent });
 * ```
 *
 * Naming is generated once by Causeway and carried through `routeMeta`; React
 * uses that generated namespace directly.
 */

import {
  mutationOptions,
  queryOptions,
  useMutation,
  useQuery,
  useSuspenseQuery,
} from "@tanstack/react-query";
import type {
  UseMutationResult,
  UseMutationOptions,
  UseQueryOptions,
  UseQueryResult,
  UseSuspenseQueryOptions,
  UseSuspenseQueryResult,
} from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { buildNamespaceTree } from "./proxy.js";
import type { NamespaceEntry, ReactRouteMeta, TreeNode } from "./proxy.js";
import type { StreamItemOf, SubscriptionStatus } from "./types.js";
import { unwrapResult } from "causeway-ts";
import type { CallOptions, Err } from "causeway-ts";

function makeQueryKey(method: string, args?: unknown): readonly unknown[] {
  return args === undefined ? [method] : [method, args];
}

type Unary = (args?: unknown, opts?: { signal?: AbortSignal }) => Promise<unknown>;
type Stream = (args?: unknown, opts?: { signal?: AbortSignal }) => AsyncIterable<unknown>;
// Generated route functions have concrete argument tuples. Keep this broad so
// conditional types preserve those tuples instead of collapsing optional args.
type AnyRouteFn = (...args: never[]) => unknown;
type QueryKey = readonly unknown[];

type AwaitedReturn<F> = F extends (...args: never[]) => infer R ? Awaited<R> : never;
type ResultData<T> = T extends { ok: true; data: infer D } ? D : never;
type UnwrappedData<F> = [ResultData<AwaitedReturn<F>>] extends [never]
  ? AwaitedReturn<F>
  : ResultData<AwaitedReturn<F>>;
type RouteError<F> = [Err<AwaitedReturn<F>>] extends [never] ? Error : Err<AwaitedReturn<F>>;
type ParamsOf<F> = F extends (...args: infer P) => unknown ? P : never;
type FirstParam<F> = ParamsOf<F> extends [] ? never : ParamsOf<F>[0];
type HasArgs<F> =
  ParamsOf<F> extends []
    ? false
    : Exclude<FirstParam<F>, undefined> extends CallOptions
      ? false
      : true;
type ArgsOf<F> = HasArgs<F> extends true ? FirstParam<F> : never;
type MutationVars<F> = HasArgs<F> extends true ? NonNullable<ArgsOf<F>> : void;
type QueryOptionInput<F> = Omit<
  UseQueryOptions<UnwrappedData<F>, RouteError<F>, UnwrappedData<F>, QueryKey>,
  "queryFn" | "queryKey"
> & {
  queryKey?: QueryKey;
};
type SuspenseQueryOptionInput<F> = Omit<
  UseSuspenseQueryOptions<UnwrappedData<F>, RouteError<F>, UnwrappedData<F>, QueryKey>,
  "queryFn" | "queryKey"
> & {
  queryKey?: QueryKey;
};
type MutationOptionInput<F> = Omit<
  UseMutationOptions<UnwrappedData<F>, RouteError<F>, MutationVars<F>>,
  "mutationFn"
>;

type WithOptionalArgs<F, TOptions, TResult> =
  HasArgs<F> extends true
    ? undefined extends ArgsOf<F>
      ? (args?: ArgsOf<F>, options?: TOptions) => TResult
      : (args: ArgsOf<F>, options?: TOptions) => TResult
    : (options?: TOptions) => TResult;

function splitArgs(
  hasArgs: boolean,
  first: unknown,
  second: unknown,
): { args: unknown; options: unknown } {
  return hasArgs ? { args: first, options: second } : { args: undefined, options: first };
}

export type ReactLeaf<F> = {
  queryKey: HasArgs<F> extends true
    ? undefined extends ArgsOf<F>
      ? (args?: ArgsOf<F>) => QueryKey
      : (args: ArgsOf<F>) => QueryKey
    : () => QueryKey;
  queryOptions: WithOptionalArgs<
    F,
    QueryOptionInput<F>,
    UseQueryOptions<UnwrappedData<F>, RouteError<F>, UnwrappedData<F>, QueryKey>
  >;
  useQuery: WithOptionalArgs<
    F,
    QueryOptionInput<F>,
    UseQueryResult<UnwrappedData<F>, RouteError<F>>
  >;
  suspenseQueryOptions: WithOptionalArgs<
    F,
    SuspenseQueryOptionInput<F>,
    UseSuspenseQueryOptions<UnwrappedData<F>, RouteError<F>, UnwrappedData<F>, QueryKey>
  >;
  useSuspenseQuery: WithOptionalArgs<
    F,
    SuspenseQueryOptionInput<F>,
    UseSuspenseQueryResult<UnwrappedData<F>, RouteError<F>>
  >;
  mutationOptions: (
    options?: MutationOptionInput<F>,
  ) => Omit<UseMutationOptions<UnwrappedData<F>, RouteError<F>, MutationVars<F>>, "mutationKey">;
  useMutation: (
    options?: MutationOptionInput<F>,
  ) => UseMutationResult<UnwrappedData<F>, RouteError<F>, MutationVars<F>>;
  useSubscription: F extends (...args: never[]) => AsyncIterable<infer TEvent>
    ? WithOptionalArgs<F, UseCausewaySubscriptionOptions<TEvent>, UseCausewaySubscriptionResult>
    : never;
};

export interface UseCausewaySubscriptionOptions<TEvent> {
  enabled?: boolean;
  onEvent: (event: TEvent) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: unknown) => void;
}

export interface UseCausewaySubscriptionResult {
  status: SubscriptionStatus;
  error: unknown;
}

export type ReactClient<TApi extends object> = {
  [K in keyof TApi]: TApi[K] extends AnyRouteFn
    ? ReactLeaf<TApi[K]>
    : TApi[K] extends object
      ? ReactClient<TApi[K]>
      : never;
};

export function createReactClient<TApi extends object>(
  api: TApi,
  routes: readonly ReactRouteMeta[],
): ReactClient<TApi> {
  // ---- internal helpers (closure-scoped; not exported) ---------------------

  function makeQueryOptions(
    entry: NamespaceEntry,
    args?: unknown,
    options?: Partial<UseQueryOptions<unknown, unknown, unknown, QueryKey>>,
  ) {
    const method = entry.operationName;
    return queryOptions({
      queryKey: options?.queryKey ?? makeQueryKey(method, args),
      ...options,
      queryFn: async ({ signal }) => {
        const fn = resolveRouteFn(entry) as Unary;
        return dataOrThrow(await fn(args, { signal }));
      },
    });
  }

  function makeUseQuery(
    entry: NamespaceEntry,
    args?: unknown,
    options?: Partial<UseQueryOptions<unknown, unknown, unknown, QueryKey>>,
  ) {
    return useQuery(makeQueryOptions(entry, args, options));
  }

  function makeSuspenseQueryOptions(
    entry: NamespaceEntry,
    args?: unknown,
    options?: Partial<UseSuspenseQueryOptions<unknown, unknown, unknown, QueryKey>>,
  ) {
    return makeQueryOptions(
      entry,
      args,
      options as Partial<UseQueryOptions<unknown, unknown, unknown, QueryKey>>,
    );
  }

  function makeUseSuspenseQuery(
    entry: NamespaceEntry,
    args?: unknown,
    options?: Partial<UseSuspenseQueryOptions<unknown, unknown, unknown, QueryKey>>,
  ) {
    return useSuspenseQuery(
      makeSuspenseQueryOptions(entry, args, options) as UseSuspenseQueryOptions<
        unknown,
        unknown,
        unknown,
        QueryKey
      >,
    );
  }

  function makeMutationOptions(
    entry: NamespaceEntry,
    options?: Partial<UseMutationOptions<unknown, unknown, unknown>>,
  ) {
    return mutationOptions({
      ...options,
      mutationFn: async (vars: unknown) => {
        const fn = resolveRouteFn(entry) as Unary;
        return dataOrThrow(await fn(vars));
      },
    });
  }

  function makeUseMutation(
    entry: NamespaceEntry,
    options?: Partial<UseMutationOptions<unknown, unknown, unknown>>,
  ) {
    return useMutation(makeMutationOptions(entry, options));
  }

  function makeUseSubscription<TEvent>(
    entry: NamespaceEntry,
    args: unknown,
    options: UseCausewaySubscriptionOptions<TEvent>,
  ): UseCausewaySubscriptionResult {
    const { enabled = true, onEvent, onOpen, onClose, onError } = options;
    const [status, setStatus] = useState<SubscriptionStatus>("idle");
    const [errorState, setError] = useState<unknown>(null);

    const cb = useRef({ onEvent, onOpen, onClose, onError });
    cb.current = { onEvent, onOpen, onClose, onError };
    const argsKey = useMemo(() => stableKey(args), [args]);

    useEffect(() => {
      if (!enabled) {
        setStatus("idle");
        return;
      }
      const controller = new AbortController();
      setStatus("connecting");
      setError(null);

      void (async () => {
        try {
          const fn = resolveRouteFn(entry) as Stream;
          const iter = fn(args, { signal: controller.signal });
          setStatus("open");
          cb.current.onOpen?.();
          for await (const ev of iter) {
            if (controller.signal.aborted) break;
            cb.current.onEvent(ev as TEvent);
          }
          if (controller.signal.aborted) return;
          setStatus("closed");
          cb.current.onClose?.();
        } catch (error) {
          if (controller.signal.aborted) return;
          setError(error);
          setStatus("error");
          cb.current.onError?.(error);
        }
      })();

      return () => controller.abort();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [enabled, entry, argsKey]);

    return { status, error: errorState };
  }

  // ---- proxy assembly ------------------------------------------------------

  const tree = buildNamespaceTree(routes);
  return makeNodeProxy(tree) as ReactClient<TApi>;

  function makeNodeProxy(node: TreeNode): unknown {
    return new Proxy(
      {},
      {
        get(_t, prop: string) {
          const leaf = node.leaves.get(prop);
          if (leaf !== undefined) return makeLeaf(leaf);
          const child = node.children.get(prop);
          if (child !== undefined) return makeNodeProxy(child);
          return undefined;
        },
        ownKeys() {
          return [...node.children.keys(), ...node.leaves.keys()];
        },
        getOwnPropertyDescriptor() {
          return { enumerable: true, configurable: true };
        },
      },
    );
  }

  function makeLeaf(entry: NamespaceEntry) {
    const name = entry.operationName;
    return {
      queryKey: (args?: unknown) => makeQueryKey(name, args),
      queryOptions: (first?: unknown, second?: unknown) => {
        const { args, options } = splitArgs(entry.hasArgs, first, second);
        return makeQueryOptions(
          entry,
          args,
          options as Partial<UseQueryOptions<unknown, unknown, unknown, QueryKey>>,
        );
      },
      useQuery: (first?: unknown, second?: unknown) => {
        const { args, options } = splitArgs(entry.hasArgs, first, second);
        return makeUseQuery(
          entry,
          args,
          options as Partial<UseQueryOptions<unknown, unknown, unknown, QueryKey>>,
        );
      },
      suspenseQueryOptions: (first?: unknown, second?: unknown) => {
        const { args, options } = splitArgs(entry.hasArgs, first, second);
        return makeSuspenseQueryOptions(
          entry,
          args,
          options as Partial<UseSuspenseQueryOptions<unknown, unknown, unknown, QueryKey>>,
        );
      },
      useSuspenseQuery: (first?: unknown, second?: unknown) => {
        const { args, options } = splitArgs(entry.hasArgs, first, second);
        return makeUseSuspenseQuery(
          entry,
          args,
          options as Partial<UseSuspenseQueryOptions<unknown, unknown, unknown, QueryKey>>,
        );
      },
      mutationOptions: (options?: Partial<UseMutationOptions<unknown, unknown, unknown>>) =>
        makeMutationOptions(entry, options),
      useMutation: (options?: Partial<UseMutationOptions<unknown, unknown, unknown>>) =>
        makeUseMutation(entry, options),
      useSubscription: <TEvent = StreamItemOf<unknown>>(
        first: unknown,
        options: UseCausewaySubscriptionOptions<TEvent>,
      ) => {
        const { args, options: subscriptionOptions } = splitArgs(entry.hasArgs, first, options);
        return makeUseSubscription(
          entry,
          args,
          subscriptionOptions as UseCausewaySubscriptionOptions<TEvent>,
        );
      },
    };
  }

  function resolveRouteFn(entry: NamespaceEntry): unknown {
    let cursor: unknown = api;
    for (const segment of entry.segments) {
      cursor = (cursor as Record<string, unknown> | undefined)?.[segment];
    }
    return (cursor as Record<string, unknown> | undefined)?.[entry.verb];
  }
}

function stableKey(value: unknown): string {
  if (value === undefined) return "";
  return JSON.stringify(value, (_k, v: unknown) => {
    if (v && typeof v === "object" && !Array.isArray(v)) {
      const out: Record<string, unknown> = {};
      for (const k of sortedKeys(v as Record<string, unknown>)) {
        out[k] = (v as Record<string, unknown>)[k];
      }
      return out;
    }
    return v;
  });
}

function sortedKeys(value: Record<string, unknown>): string[] {
  const keys: string[] = [];
  for (const key of Object.keys(value)) {
    const index = keys.findIndex((current) => current > key);
    if (index === -1) {
      keys.push(key);
    } else {
      keys.splice(index, 0, key);
    }
  }
  return keys;
}

// Use the shared envelope unwrapper from causeway-ts so the failure branch
// throws a real `CausewayError` instance (with `message`, `kind`, stack trace).
// A bare `throw value.error` would surface a plain object and break
// `err instanceof Error` / `err.message` in user code.
const dataOrThrow = unwrapResult;
