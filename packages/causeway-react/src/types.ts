// Small type helpers used by hook leaves. `createReactClient` maps the generated
// nested `ApiRoutes` type directly.

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- generic over arbitrary callables
type AnyFn = (...args: any[]) => any;

export type StreamItemOf<F> = F extends AnyFn
  ? ReturnType<F> extends AsyncIterable<infer I>
    ? I
    : never
  : never;

export type SubscriptionStatus = "idle" | "connecting" | "open" | "closed" | "error";
