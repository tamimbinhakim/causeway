import { Fragment, createElement, useLayoutEffect, useMemo, useRef } from "react";
import type { ReactNode } from "react";

import type { CausewayClient, DehydratedClient } from "@causewayjs/client";
import {
  CausewayProvider,
  registerCausewayHydrationSnapshot,
  useOptionalCausewayClient,
  type CausewayFeedback,
} from "@causewayjs/react";

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
    const hydrationState = state ?? snapshot;
    const hydrationKey = useMemo(() => snapshotKey(hydrationState), [hydrationState]);
    const parentClient = useOptionalCausewayClient();
    const fallbackClient = useRef<CausewayClient | null>(null);
    const lastHydration = useRef<{ client: CausewayClient; key: string } | null>(null);
    const lastNotification = useRef<{ client: CausewayClient; key: string } | null>(null);

    if (parentClient === null && fallbackClient.current === null) {
      const next = factory(options);
      fallbackClient.current = next;
    }

    const client = parentClient ?? fallbackClient.current!;

    if (hydrationState != null && hydrationKey != null) {
      const last = lastHydration.current;
      if (last?.client !== client || last.key !== hydrationKey) {
        client.hydrate(hydrationState, { notify: false });
        lastHydration.current = { client, key: hydrationKey };
      }
    }

    useLayoutEffect(() => {
      if (hydrationState == null || hydrationKey == null) return;
      const last = lastNotification.current;
      if (last?.client === client && last.key === hydrationKey) return;
      client.hydrate(hydrationState, { forceNotify: true });
      registerCausewayHydrationSnapshot(client, hydrationState);
      lastNotification.current = { client, key: hydrationKey };
    }, [client, hydrationKey, hydrationState]);

    if (parentClient !== null && feedback === undefined) {
      return createElement(Fragment, null, children);
    }
    return createElement(CausewayProvider, { client, feedback }, children);
  };
}

function snapshotKey(snapshot: DehydratedClient | null | undefined): string | null {
  return snapshot == null ? null : JSON.stringify(snapshot);
}
