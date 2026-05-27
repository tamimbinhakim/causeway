/**
 * Server-side helpers. The proxy returned by ``createReactClient`` is safe to
 * import in server code as long as you only touch the non-hook surface —
 * ``api.x.y.queryOptions(args)``, ``api.x.y.queryKey(args)``, etc. Pass those
 * straight into the React Query client:
 *
 * ```ts
 * await queryClient.prefetchQuery(api.customers.list.queryOptions({ limit: 50 }));
 * ```
 *
 * The bulk helper below covers the common multi-prefetch shape.
 */
import type { FetchQueryOptions, QueryClient } from "@tanstack/react-query";

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- variadic helper over generated leaves
export interface PrefetchableLeaf<TArgs extends readonly any[] = readonly any[]> {
  queryOptions: (...args: TArgs) => FetchQueryOptions;
}

export type PrefetchEntry<TLeaf extends PrefetchableLeaf> = readonly [
  leaf: TLeaf,
  ...args: Parameters<TLeaf["queryOptions"]>,
];

export async function prefetchQuery<TLeaf extends PrefetchableLeaf>(
  queryClient: QueryClient,
  leaf: TLeaf,
  ...args: Parameters<TLeaf["queryOptions"]>
): Promise<void> {
  await queryClient.prefetchQuery(leaf.queryOptions(...args));
}

export async function prefetchQueries<
  const TEntries extends readonly PrefetchEntry<PrefetchableLeaf>[],
>(queryClient: QueryClient, leaves: TEntries): Promise<void> {
  await Promise.all(
    leaves.map(([leaf, ...args]) => queryClient.prefetchQuery(leaf.queryOptions(...args))),
  );
}
