import { createEffect, createResource, createSignal, onCleanup } from "solid-js";
import type { Accessor, ResourceReturn } from "solid-js";

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

type InputSource<TInput extends RouteInputValue> = TInput | Accessor<TInput>;
type QuerySource<TInput extends RouteInputValue> = { input: TInput };

export type QueryResource<TData, TError> = ResourceReturn<TData> & {
  error: Accessor<TError | undefined>;
};

export interface MutationResource<TData, TError, TVars extends RouteInputValue> {
  data: Accessor<TData | undefined>;
  error: Accessor<TError | undefined>;
  loading: Accessor<boolean>;
  mutate: (vars: TVars, opts?: CallOptions) => Promise<TData>;
  reset: () => void;
}

export interface SubscriptionResource<TError> {
  status: Accessor<"idle" | "connecting" | "open" | "closed" | "error">;
  error: Accessor<TError | undefined>;
}

export interface CausewayResources {
  query: {
    <K extends RegisteredQueryRouteKey>(
      routeKey: K,
      input?: InputSource<RegisteredRouteInput<K>>,
    ): QueryResource<RegisteredRouteData<K>, RegisteredRouteError<K>>;
    <TData = unknown, TError = unknown, TInput extends RouteInputValue = RouteInputValue>(
      routeKey: UnregisteredRouteKey,
      input?: InputSource<TInput>,
    ): QueryResource<TData, TError>;
  };

  mutation: {
    <K extends RegisteredMutationRouteKey>(
      routeKey: K,
    ): MutationResource<RegisteredRouteData<K>, RegisteredRouteError<K>, RegisteredRouteInput<K>>;
    <TVars extends RouteInputValue = Record<string, unknown>, TData = unknown, TError = unknown>(
      routeKey: UnregisteredRouteKey,
    ): MutationResource<TData, TError, TVars>;
  };

  subscription: {
    <K extends RegisteredQueryRouteKey>(
      routeKey: K,
      input: InputSource<RegisteredRouteInput<K>>,
      onEvent: (event: RegisteredRouteData<K>) => void,
    ): SubscriptionResource<RegisteredRouteError<K>>;
    <TEvent = unknown, TError = unknown, TInput extends RouteInputValue = RouteInputValue>(
      routeKey: UnregisteredRouteKey,
      input: InputSource<TInput>,
      onEvent: (event: TEvent) => void,
    ): SubscriptionResource<TError>;
  };
}

export function createCausewayResources(client: CausewayClient): CausewayResources {
  function query<K extends RegisteredQueryRouteKey>(
    routeKey: K,
    input?: InputSource<RegisteredRouteInput<K>>,
  ): QueryResource<RegisteredRouteData<K>, RegisteredRouteError<K>>;
  function query<
    TData = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(routeKey: UnregisteredRouteKey, input?: InputSource<TInput>): QueryResource<TData, TError>;
  function query<
    TData = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(routeKey: string, input?: InputSource<TInput>) {
    const [errorSignal, setError] = createSignal<TError | undefined>(undefined);
    const resource = createResource<TData, QuerySource<TInput>>(
      () => ({ input: readInput(input) }),
      async ({ input: vars }) => {
        try {
          const data = await client.query<TData>(routeKey, toInput(vars));
          setError(() => undefined);
          return data;
        } catch (error) {
          setError(() => error as TError);
          throw error;
        }
      },
    );
    return Object.assign(resource, { error: errorSignal }) as QueryResource<TData, TError>;
  }

  function mutation<K extends RegisteredMutationRouteKey>(
    routeKey: K,
  ): MutationResource<RegisteredRouteData<K>, RegisteredRouteError<K>, RegisteredRouteInput<K>>;
  function mutation<
    TVars extends RouteInputValue = Record<string, unknown>,
    TData = unknown,
    TError = unknown,
  >(routeKey: UnregisteredRouteKey): MutationResource<TData, TError, TVars>;
  function mutation<
    TVars extends RouteInputValue = Record<string, unknown>,
    TData = unknown,
    TError = unknown,
  >(routeKey: string) {
    const [data, setData] = createSignal<TData | undefined>(undefined);
    const [errorSignal, setError] = createSignal<TError | undefined>(undefined);
    const [loading, setLoading] = createSignal(false);

    async function mutate(vars: TVars, opts: CallOptions = {}): Promise<TData> {
      setLoading(true);
      setError(() => undefined);
      try {
        const result = await client.mutate<TData>(routeKey, toInput(vars), opts);
        setData(() => result);
        return result;
      } catch (error) {
        setError(() => error as TError);
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

  function subscription<K extends RegisteredQueryRouteKey>(
    routeKey: K,
    input: InputSource<RegisteredRouteInput<K>>,
    onEvent: (event: RegisteredRouteData<K>) => void,
  ): SubscriptionResource<RegisteredRouteError<K>>;
  function subscription<
    TEvent = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(
    routeKey: UnregisteredRouteKey,
    input: InputSource<TInput>,
    onEvent: (event: TEvent) => void,
  ): SubscriptionResource<TError>;
  function subscription<
    TEvent = unknown,
    TError = unknown,
    TInput extends RouteInputValue = RouteInputValue,
  >(routeKey: string, input: InputSource<TInput>, onEvent: (event: TEvent) => void) {
    const [status, setStatus] = createSignal<"idle" | "connecting" | "open" | "closed" | "error">(
      "idle",
    );
    const [errorSignal, setError] = createSignal<TError | undefined>(undefined);

    createEffect(() => {
      const vars = readInput(input);
      const controller = new AbortController();
      setStatus("connecting");
      setError(() => undefined);

      void (async () => {
        try {
          setStatus("open");
          for await (const ev of client.stream<TEvent>(routeKey, toInput(vars), {
            signal: controller.signal,
          })) {
            if (controller.signal.aborted) return;
            onEvent(ev);
          }
          if (controller.signal.aborted) return;
          setStatus("closed");
        } catch (error) {
          if (controller.signal.aborted) return;
          setError(() => error as TError);
          setStatus("error");
        }
      })();

      onCleanup(() => controller.abort());
    });

    return { error: errorSignal, status };
  }

  return { mutation, query, subscription };
}

function readInput<TInput extends RouteInputValue>(input: InputSource<TInput> | undefined): TInput {
  return typeof input === "function" ? (input as Accessor<TInput>)() : (input as TInput);
}

function toInput(input: RouteInputValue): Record<string, unknown> | void {
  return input;
}
