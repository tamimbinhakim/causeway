// Mirrors causeway-react's type-level helpers so the Svelte and React bindings
// Stay structurally interchangeable from the codegen's point of view.

import type { Result } from "causeway-ts";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFn = (...args: any[]) => any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FirstArg<F> = F extends (a: infer A, ...rest: any[]) => unknown ? A : void;

export type UnaryKeys<TApi> = {
  [K in keyof TApi]: TApi[K] extends AnyFn
    ? ReturnType<TApi[K]> extends Promise<unknown>
      ? K
      : never
    : never;
}[keyof TApi];

export type StreamKeys<TApi> = {
  [K in keyof TApi]: TApi[K] extends AnyFn
    ? ReturnType<TApi[K]> extends AsyncIterable<unknown>
      ? K
      : never
    : never;
}[keyof TApi];

type IsCallOptionsLike<T> = [T] extends [undefined]
  ? true
  : [Exclude<keyof NonNullable<T>, "signal" | "headers">] extends [never]
    ? true
    : false;

export type ArgsOf<F> = IsCallOptionsLike<FirstArg<F>> extends true ? void : FirstArg<F>;

type DataOfResolved<X> = X extends Result<infer T, unknown> ? T : X;
type ErrorOfResolved<X> = X extends Result<unknown, infer E> ? E : Error;

export type DataOf<F> = F extends AnyFn ? DataOfResolved<Awaited<ReturnType<F>>> : never;
export type ErrorOf<F> = F extends AnyFn ? ErrorOfResolved<Awaited<ReturnType<F>>> : Error;

export type StreamItemOf<F> = F extends AnyFn
  ? ReturnType<F> extends AsyncIterable<infer I>
    ? I
    : never
  : never;
