import { unwrapResult } from "causeway-ts";
import { createEffect, createResource, createSignal, onCleanup } from "solid-js";
import type { Accessor, ResourceReturn } from "solid-js";

import type { ArgsOf, DataOf, ErrorOf, StreamItemOf, StreamKeys, UnaryKeys } from "./types.js";

type Unary = (args?: unknown, opts?: { signal?: AbortSignal }) => Promise<unknown>;
type Stream = (args?: unknown, opts?: { signal?: AbortSignal }) => AsyncIterable<unknown>;

export type QueryResource<TData, TError> = ResourceReturn<TData> & {
  error: Accessor<TError | undefined>;
};

export interface MutationResource<TData, TError, TArgs> {
  data: Accessor<TData | undefined>;
  error: Accessor<TError | undefined>;
  loading: Accessor<boolean>;
  mutate: (args: TArgs) => Promise<TData>;
  reset: () => void;
}

export interface SubscriptionResource<TError> {
  status: Accessor<"idle" | "connecting" | "open" | "closed" | "error">;
  error: Accessor<TError | undefined>;
}

export interface CausewayResources<TApi> {
  query: <K extends UnaryKeys<TApi>>(
    method: K,
    args: () => ArgsOf<TApi[K]>,
  ) => QueryResource<DataOf<TApi[K]>, ErrorOf<TApi[K]>>;

  mutation: <K extends UnaryKeys<TApi>>(
    method: K,
  ) => MutationResource<DataOf<TApi[K]>, ErrorOf<TApi[K]>, ArgsOf<TApi[K]>>;

  subscription: <K extends StreamKeys<TApi>>(
    method: K,
    args: () => ArgsOf<TApi[K]>,
    onEvent: (event: StreamItemOf<TApi[K]>) => void,
  ) => SubscriptionResource<unknown>;
}

export function createCausewayResources<TApi extends object>(api: TApi): CausewayResources<TApi> {
  function query<K extends UnaryKeys<TApi>>(method: K, args: () => ArgsOf<TApi[K]>) {
    const [errorSignal, setError] = createSignal<ErrorOf<TApi[K]> | undefined>(undefined);
    const resource = createResource<DataOf<TApi[K]>, ArgsOf<TApi[K]>>(args, async (a) => {
      const fn = api[method] as unknown as Unary;
      try {
        const data = unwrapResult(await fn(a as unknown)) as DataOf<TApi[K]>;
        setError(() => undefined);
        return data;
      } catch (error) {
        setError(() => error as ErrorOf<TApi[K]>);
        throw error;
      }
    });
    return Object.assign(resource, { error: errorSignal }) as QueryResource<
      DataOf<TApi[K]>,
      ErrorOf<TApi[K]>
    >;
  }

  function mutation<K extends UnaryKeys<TApi>>(method: K) {
    const [data, setData] = createSignal<DataOf<TApi[K]> | undefined>(undefined);
    const [errorSignal, setError] = createSignal<ErrorOf<TApi[K]> | undefined>(undefined);
    const [loading, setLoading] = createSignal(false);

    async function mutate(args: ArgsOf<TApi[K]>): Promise<DataOf<TApi[K]>> {
      setLoading(true);
      setError(() => undefined);
      try {
        const fn = api[method] as unknown as Unary;
        const result = unwrapResult(await fn(args as unknown)) as DataOf<TApi[K]>;
        setData(() => result);
        return result;
      } catch (error) {
        setError(() => error as ErrorOf<TApi[K]>);
        throw error;
      } finally {
        setLoading(false);
      }
    }

    function reset() {
      setData(() => undefined);
      setError(() => undefined);
      setLoading(false);
    }

    return { data, error: errorSignal, loading, mutate, reset };
  }

  function subscription<K extends StreamKeys<TApi>>(
    method: K,
    args: () => ArgsOf<TApi[K]>,
    onEvent: (event: StreamItemOf<TApi[K]>) => void,
  ) {
    const [status, setStatus] = createSignal<"idle" | "connecting" | "open" | "closed" | "error">(
      "idle",
    );
    const [errorSignal, setError] = createSignal<unknown>(undefined);

    createEffect(() => {
      const a = args();
      const controller = new AbortController();
      setStatus("connecting");
      setError(() => undefined);

      void (async () => {
        try {
          const fn = api[method] as unknown as Stream;
          const iter = fn(a as unknown, { signal: controller.signal });
          setStatus("open");
          for await (const ev of iter) {
            if (controller.signal.aborted) {
              return;
            }
            onEvent(ev as StreamItemOf<TApi[K]>);
          }
          if (controller.signal.aborted) {
            return;
          }
          setStatus("closed");
        } catch (error) {
          if (controller.signal.aborted) {
            return;
          }
          setError(() => error);
          setStatus("error");
        }
      })();

      onCleanup(() => controller.abort());
    });

    return { error: errorSignal, status };
  }

  return { mutation, query, subscription };
}
