import { createElement, useState } from "react";
import type { ReactNode } from "react";

import type { CausewayClient, DehydratedClient } from "@causewayjs/client";
import { CausewayProvider, type CausewayFeedback } from "@causewayjs/react";

export type ClientFactory<
  TClient extends CausewayClient = CausewayClient,
  TOptions extends object = object,
> = (options?: TOptions) => TClient;

export interface HydrateClientProps {
  state?: DehydratedClient | null;
  snapshot?: DehydratedClient | null;
  feedback?: CausewayFeedback;
  children?: ReactNode;
}

export function createHydrateClient<
  TFactory extends ClientFactory,
  TOptions extends object = Parameters<TFactory>[0] extends object
    ? NonNullable<Parameters<TFactory>[0]>
    : object,
>(factory: TFactory, options?: TOptions) {
  return function HydrateClient({ children, feedback, snapshot, state }: HydrateClientProps) {
    const initialState = state ?? snapshot;
    const [client] = useState(() => {
      const next = factory(options);
      if (initialState != null) next.hydrate(initialState);
      return next;
    });

    return createElement(CausewayProvider, { client, feedback }, children);
  };
}
