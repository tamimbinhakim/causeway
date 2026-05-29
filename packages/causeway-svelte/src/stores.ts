import { readable, writable } from "svelte/store";
import type { Readable, Writable } from "svelte/store";

import type {
  CallOptions,
  CausewayClient,
  RegisteredMutationRouteKey,
  RegisteredQueryRouteKey,
  RegisteredRouteData,
  RegisteredRouteError,
  RegisteredRouteInput,
  RouteInputValue,
  UnregisteredRouteKey,
} from "@causewayjs/client";

export interface QueryStoreOptions {
  enabled?: boolean;
}

export interface QueryStoreValue<TData, TError> {
  status: "idle" | "loading" | "success" | "error";
  data: TData | undefined;
  error: TError | undefined;
  refetch: (opts?: CallOptions) => void;
}

export interface MutationStoreValue<TData, TError, TVars extends RouteInputValue> {
  status: "idle" | "loading" | "success" | "error";
  data: TData | undefined;
  error: TError | undefined;
  mutate: (vars: TVars, opts?: CallOptions) => Promise<TData>;
  reset: () => void;
}

export interface SubscriptionStoreValue<TError> {
  status: "idle" | "connecting" | "open" | "closed" | "error";
  error: TError | undefined;
}

export interface CausewayStores {
  query: {
    <K extends RegisteredQueryRouteKey>(
      routeKey: K,
      ...args: QueryStoreArgs<K>
    ): Readable<QueryStoreValue<RegisteredRouteData<K>, RegisteredRouteError<K>>>;
    <TData = unknown, TError = unknown, TInput extends RouteInputValue = RouteInputValue>(
      routeKey: UnregisteredRouteKey,
      input?: TInput,
      options?: QueryStoreOptions,
    ): Readable<QueryStoreValue<TData, TError>>;
  };

  mutation: {
    <K extends RegisteredMutationRouteKey>(
      routeKey: K,
    ): Readable<
      MutationStoreValue<RegisteredRouteData<K>, RegisteredRouteError<K>, RegisteredRouteInput<K>>
    >;
    <TVars extends RouteInputValue = Record<string, unknown>, TData = unknown, TError = unknown>(
      routeKey: UnregisteredRouteKey,
    ): Readable<MutationStoreValue<TData, TError, TVars>>;
  };

  subscription: {
    <K extends RegisteredQueryRouteKey>(
      routeKey: K,
      input: RegisteredRouteInput<K>,
      onEvent: (event: RegisteredRouteData<K>) => void,
      options?: { enabled?: boolean },
    ): Readable<SubscriptionStoreValue<RegisteredRouteError<K>>>;
    <TEvent = unknown, TError = unknown, TInput extends RouteInputValue = RouteInputValue>(
      routeKey: UnregisteredRouteKey,
      input: TInput,
      onEvent: (event: TEvent) => void,
      options?: { enabled?: boolean },
    ): Readable<SubscriptionStoreValue<TError>>;
  };
}

type QueryStoreArgs<K extends string> = [RegisteredRouteInput<K>] extends [void]
  ? [input?: void, options?: QueryStoreOptions]
  : [input: RegisteredRouteInput<K>, options?: QueryStoreOptions];

export function createCausewayStores(client: CausewayClient): CausewayStores {
  function query<K extends RegisteredQueryRouteKey>(
    routeKey: K,
    ...args: QueryStoreArgs<K>
  ): Readable<QueryStoreValue<RegisteredRouteData<K>, RegisteredRouteError<K>>>;
  function query<
    TData = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(
    routeKey: UnregisteredRouteKey,
    input?: TInput,
    options?: QueryStoreOptions,
  ): Readable<QueryStoreValue<TData, TError>>;
  function query<
    TData = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(routeKey: string, input?: TInput, options: QueryStoreOptions = {}) {
    const enabled = options.enabled ?? true;
    type V = QueryStoreValue<TData, TError>;
    let controller: AbortController | null = null;
    const inner: Writable<V> = writable({
      data: undefined,
      error: undefined,
      refetch: (opts?: CallOptions) => run(opts),
      status: enabled ? "loading" : "idle",
    });

    function run(opts: CallOptions = {}) {
      controller?.abort();
      controller = new AbortController();
      inner.update((s) => ({ ...s, error: undefined, status: "loading" }));
      void (async () => {
        try {
          const data = await client.query<TData>(routeKey, toInput(input), {
            ...opts,
            signal: opts.signal ?? controller?.signal,
          });
          inner.update((s) => ({ ...s, data, error: undefined, status: "success" }));
        } catch (error) {
          if (isAbortError(error)) return;
          inner.update((s) => ({
            ...s,
            error: error as TError,
            status: "error",
          }));
        }
      })();
    }

    if (enabled) run();
    return { subscribe: inner.subscribe };
  }

  function mutation<K extends RegisteredMutationRouteKey>(
    routeKey: K,
  ): Readable<
    MutationStoreValue<RegisteredRouteData<K>, RegisteredRouteError<K>, RegisteredRouteInput<K>>
  >;
  function mutation<
    TVars extends RouteInputValue = Record<string, unknown>,
    TData = unknown,
    TError = unknown,
  >(routeKey: UnregisteredRouteKey): Readable<MutationStoreValue<TData, TError, TVars>>;
  function mutation<
    TVars extends RouteInputValue = Record<string, unknown>,
    TData = unknown,
    TError = unknown,
  >(routeKey: string) {
    type V = MutationStoreValue<TData, TError, TVars>;
    const inner: Writable<V> = writable({
      data: undefined,
      error: undefined,
      mutate: async (vars: TVars, opts: CallOptions = {}) => {
        inner.update((s) => ({ ...s, error: undefined, status: "loading" }));
        try {
          const data = await client.mutate<TData>(routeKey, toInput(vars), opts);
          inner.update((s) => ({ ...s, data, status: "success" }));
          return data;
        } catch (error) {
          inner.update((s) => ({
            ...s,
            error: error as TError,
            status: "error",
          }));
          throw error;
        }
      },
      reset: () =>
        inner.set({
          status: "idle",
          data: undefined,
          error: undefined,
          mutate: getStore().mutate,
          reset: getStore().reset,
        }),
      status: "idle",
    });
    let captured: V;
    inner.subscribe((v) => (captured = v));
    function getStore(): V {
      return captured;
    }
    return { subscribe: inner.subscribe };
  }

  function subscription<K extends RegisteredQueryRouteKey>(
    routeKey: K,
    input: RegisteredRouteInput<K>,
    onEvent: (event: RegisteredRouteData<K>) => void,
    options?: { enabled?: boolean },
  ): Readable<SubscriptionStoreValue<RegisteredRouteError<K>>>;
  function subscription<
    TEvent = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(
    routeKey: UnregisteredRouteKey,
    input: TInput,
    onEvent: (event: TEvent) => void,
    options?: { enabled?: boolean },
  ): Readable<SubscriptionStoreValue<TError>>;
  function subscription<
    TEvent = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(
    routeKey: string,
    input: TInput,
    onEvent: (event: TEvent) => void,
    options: { enabled?: boolean } = {},
  ) {
    const enabled = options.enabled ?? true;
    return readable<SubscriptionStoreValue<TError>>(
      { error: undefined, status: enabled ? "connecting" : "idle" },
      (set) => {
        if (!enabled) return;
        const controller = new AbortController();
        set({ error: undefined, status: "connecting" });
        void (async () => {
          try {
            set({ error: undefined, status: "open" });
            for await (const ev of client.stream<TEvent>(routeKey, toInput(input), {
              signal: controller.signal,
            })) {
              if (controller.signal.aborted) return;
              onEvent(ev);
            }
            if (controller.signal.aborted) return;
            set({ error: undefined, status: "closed" });
          } catch (error) {
            if (controller.signal.aborted) return;
            set({ error: error as TError, status: "error" });
          }
        })();
        return () => controller.abort();
      },
    );
  }

  return { mutation, query, subscription };
}

function toInput(input: RouteInputValue): Record<string, unknown> | void {
  return input;
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}
