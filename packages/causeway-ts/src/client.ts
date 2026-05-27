import { parseSSE } from "./sse.js";
import { buildError, CausewayError } from "./types.js";
import type { CallOptions, LazyClientConfig, Result, RouteDescriptor, RouteMeta } from "./types.js";

type Args = Record<string, unknown>;
type FetchImpl = typeof globalThis.fetch;

export function createLazyClient<TApi extends object = Record<string, unknown>>(
  config: LazyClientConfig,
): TApi {
  const baseUrl = (config.baseUrl ?? "").replace(/\/$/, "");
  const fetchImpl: FetchImpl = config.fetch ?? globalThis.fetch.bind(globalThis);
  const cache = new Map<string, Promise<RouteDescriptor>>();
  const root: Record<string, unknown> = Object.create(null);

  const loadRoute = (id: string): Promise<RouteDescriptor> => {
    let cached = cache.get(id);
    if (cached === undefined) {
      cached = Promise.resolve(config.loadRoute(id));
      cache.set(id, cached);
    }
    return cached;
  };

  for (const route of config.routeMeta) {
    const fn = (args?: Args, opts: CallOptions = {}) => {
      if (route.streams) {
        return streamCallLazy(
          route,
          args ?? {},
          opts,
          baseUrl,
          config.headers,
          fetchImpl,
          loadRoute,
        );
      }
      return loadRoute(route.id).then((loaded) => {
        const { url, init } = buildRequest(loaded, args ?? {}, opts, baseUrl, config.headers);
        return unaryCall(loaded, url, init, fetchImpl);
      });
    };

    installRoute(root, route, fn);
  }

  return root as TApi;
}

function installRoute(
  root: Record<string, unknown>,
  route: Pick<RouteDescriptor, "segments" | "verb">,
  fn: (args?: Args, opts?: CallOptions) => unknown,
): void {
  let cursor = root;
  for (const segment of route.segments) {
    const existing = cursor[segment];
    if (existing && typeof existing === "object") {
      cursor = existing as Record<string, unknown>;
    } else {
      const child: Record<string, unknown> = Object.create(null);
      cursor[segment] = child;
      cursor = child;
    }
  }
  cursor[route.verb] = fn;
}

function buildRequest(
  route: RouteDescriptor,
  args: Args,
  opts: CallOptions,
  baseUrl: string,
  defaultHeaders: Record<string, string> | undefined,
): { url: string; init: RequestInit } {
  let { path } = route;
  const query = new URLSearchParams();
  const headers: Record<string, string> = { ...defaultHeaders, ...opts.headers };

  const bodyEmbed: Record<string, unknown> = {};
  let bodyWhole: unknown;
  let bodyMode: "none" | "json" | "multipart" | "binary" | "form" = "none";
  let multipart: FormData | null = null;

  for (const p of route.params ?? []) {
    const v = args[p.name];
    if (v === undefined) continue;
    switch (p.in) {
      case "path": {
        path = path.replace(`{${p.alias}}`, encodeURIComponent(String(v)));
        break;
      }
      case "query": {
        // Arrays expand to repeated keys: ?tag=a&tag=b. Servers using
        // request.query_params.getlist(...) recover the list.
        if (Array.isArray(v)) for (const item of v) query.append(p.alias, String(item));
        else query.append(p.alias, String(v));
        break;
      }
      case "header": {
        headers[p.alias] = String(v);
        break;
      }
      case "cookie": {
        // Browsers won't let JS set Cookie directly — userland can override.
        const prev = headers["cookie"];
        headers["cookie"] = `${prev ? `${prev}; ` : ""}${p.alias}=${String(v)}`;
        break;
      }
      case "file": {
        if (multipart == null) multipart = new FormData();
        multipart.append(p.alias, v instanceof Blob ? v : String(v));
        bodyMode = "multipart";
        break;
      }
      case "body": {
        if (route.binaryBody) {
          // Raw-bytes body — pass the value through unchanged.
          bodyWhole = v;
          bodyMode = "binary";
        } else if (route.formBody) {
          bodyWhole = v;
          bodyMode = "form";
        } else if (p.embed) {
          bodyEmbed[p.alias] = v;
          if (bodyMode === "none") bodyMode = "json";
        } else {
          bodyWhole = v;
          if (bodyMode === "none") bodyMode = "json";
        }
        break;
      }
    }
  }

  let body: BodyInit | undefined;
  const requestOpaque = buildOpaqueTree(route.opaqueRequestPaths);
  if (bodyMode === "json") {
    headers["content-type"] ??= "application/json";
    const payload = Object.keys(bodyEmbed).length > 0 ? bodyEmbed : bodyWhole;
    // camelCase → snake_case so the Python server sees the keys it expects.
    // Subtrees flagged opaque in the route descriptor pass through untouched
    // so user-defined JSON (e.g. `definition: dict[str, Any]`) keeps its keys.
    body =
      payload === undefined
        ? undefined
        : JSON.stringify(camelToSnakeDeepGuarded(payload, requestOpaque));
  } else if (bodyMode === "multipart" && multipart != null) {
    // Let fetch set the multipart boundary; we must NOT pin content-type.
    delete headers["content-type"];
    body = multipart;
  } else if (bodyMode === "binary") {
    headers["content-type"] ??= "application/octet-stream";
    body = bodyWhole as BodyInit;
  } else if (bodyMode === "form") {
    headers["content-type"] ??= "application/x-www-form-urlencoded";
    const form = new URLSearchParams();
    const payload = camelToSnakeDeepGuarded(bodyWhole, requestOpaque) as Record<string, unknown>;
    for (const [k, val] of Object.entries(payload)) {
      if (val === undefined || val === null) continue;
      if (Array.isArray(val)) for (const item of val) form.append(k, String(item));
      else form.append(k, String(val));
    }
    body = form.toString();
  }

  const qs = query.toString();
  return {
    url: `${baseUrl}${path}${qs ? `?${qs}` : ""}`,
    init: { method: route.method, headers, body, signal: opts.signal },
  };
}

async function* streamCallLazy(
  route: RouteMeta,
  args: Args,
  opts: CallOptions,
  baseUrl: string,
  defaultHeaders: Record<string, string> | undefined,
  fetchImpl: FetchImpl,
  loadRoute: (id: string) => Promise<RouteDescriptor>,
): AsyncIterableIterator<unknown> {
  const loaded = await loadRoute(route.id);
  yield* streamCall(loaded, args, opts, baseUrl, defaultHeaders, fetchImpl);
}

async function unaryCall(
  route: RouteDescriptor,
  url: string,
  init: RequestInit,
  fetchImpl: FetchImpl,
): Promise<unknown> {
  const res = await fetchImpl(url, init);

  if (route.binaryResponse) {
    if (!res.ok) throw await httpError(res);
    // Server marked the route as raw bytes — hand back a Blob, skip JSON parsing.
    return await res.blob();
  }

  const ct = res.headers.get("content-type") ?? "";

  // JSON path — covers both 2xx envelopes and 4xx/5xx typed-error envelopes
  // ({ ok: false, error: { kind, … } }). Frameworks like Causeway map declared
  // `@raises` errors to their HTTP status code while keeping the envelope body;
  // we recognize that shape and surface it as `Result.error` instead of a
  // generic `HTTP NNN: …` so consumers can branch on `error.kind`.
  if (ct.includes("application/json")) {
    const raw = (await res.json()) as unknown;
    const responseOpaque = buildOpaqueTree(route.opaqueResponsePaths);
    const value = snakeToCamelDeepGuarded(raw, responseOpaque) as unknown;
    if (isTypedErrorEnvelope(value)) {
      if (route.result) return value as Result<unknown, unknown>;
      const errPayload = (value as { error: Record<string, unknown> }).error;
      // Carry the HTTP status onto the thrown error so consumers don't need
      // to inspect the response separately.
      throw buildError({ ...errPayload, status: errPayload.status ?? res.status });
    }
    if (!res.ok) throw httpErrorFromJson(res.status, raw);
    // `result: true` hands the envelope back untouched; the caller's static
    // type is `Result<T, E>` so TypeScript forces them to branch on `ok`.
    return route.result ? (value as Result<unknown, unknown>) : value;
  }

  if (!res.ok) throw await httpError(res);
  if (res.status === 204 || ct === "") return undefined;
  return await res.text();
}

function isTypedErrorEnvelope(value: unknown): value is { ok: false; error: { kind: string } } {
  if (!value || typeof value !== "object") return false;
  const v = value as { ok?: unknown; error?: unknown };
  if (v.ok !== false) return false;
  const err = v.error as { kind?: unknown } | undefined;
  return Boolean(err) && typeof err?.kind === "string";
}

function httpErrorFromJson(status: number, raw: unknown): CausewayError {
  if (raw && typeof raw === "object") {
    return buildError({ ...(raw as Record<string, unknown>), status });
  }
  return new CausewayError({
    kind: "HttpError",
    status,
    message: `HTTP ${status}`,
    data: raw,
  });
}

// Streaming caller with built-in resume. We track the last `id:` seen and,
// if the connection drops mid-stream, reconnect with `Last-Event-Id`. The
// server's `retry:` value (in ms) controls the minimum backoff; we cap at
// 30s and abort on user cancellation.
async function* streamCall(
  route: RouteDescriptor,
  args: Args,
  opts: CallOptions,
  baseUrl: string,
  defaultHeaders: Record<string, string> | undefined,
  fetchImpl: FetchImpl,
): AsyncIterableIterator<unknown> {
  let lastId: string | undefined;
  let retryMs = 1000; // default backoff if server doesn't send `retry:`
  const startedAt = Date.now();
  const maxResumeWindowMs = 5 * 60 * 1000; // give up after 5 min of failed reconnects
  const streamOpaque = buildOpaqueTree(route.opaqueResponsePaths);

  while (true) {
    if (opts.signal?.aborted) return;
    const headers: Record<string, string> = { ...defaultHeaders, ...opts.headers };
    if (lastId !== undefined) headers["last-event-id"] = lastId;

    const { url, init } = buildRequest(route, args, { ...opts, headers }, baseUrl, defaultHeaders);
    let res: Response;
    try {
      res = await fetchImpl(url, init);
    } catch (error) {
      if (opts.signal?.aborted) return;
      if (Date.now() - startedAt > maxResumeWindowMs) throw error;
      await sleep(retryMs, opts.signal);
      continue;
    }
    if (!res.ok) throw await httpError(res);
    if (!res.body) return;

    let sawDone = false;
    try {
      for await (const ev of parseSSE(res.body)) {
        if (ev.retry !== undefined) retryMs = Math.min(ev.retry, 30_000);
        if (ev.id !== undefined) lastId = ev.id;
        if (ev.event === "done") {
          sawDone = true;
          return;
        }
        if (ev.event === "error") {
          // Typed stream errors are terminal — don't retry, propagate to caller.
          throw Object.assign(new Error("stream error"), {
            kind: "error",
            payload: safeJsonParse(ev.data),
            causewayTerminal: true,
          });
        }
        if (ev.data === "") continue;
        yield snakeToCamelDeepGuarded(safeJsonParse(ev.data), streamOpaque);
      }
    } catch (error) {
      if (opts.signal?.aborted) return;
      if ((error as { causewayTerminal?: boolean })?.causewayTerminal) throw error;
      if (Date.now() - startedAt > maxResumeWindowMs) throw error;
      await sleep(retryMs, opts.signal);
      continue;
    }
    // Stream ended without `event: done` — treat as a disconnect and reconnect.
    if (sawDone) return;
    if (opts.signal?.aborted) return;
    if (Date.now() - startedAt > maxResumeWindowMs) return;
    await sleep(retryMs, opts.signal);
  }
}

async function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return;
  await new Promise<void>((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      resolve();
    };
    const timer = setTimeout(finish, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        finish();
      },
      { once: true },
    );
  });
}

async function httpError(res: Response): Promise<CausewayError> {
  const body = await res.text();
  const parsed = safeJsonParse(body);
  if (parsed && typeof parsed === "object" && "kind" in (parsed as Record<string, unknown>)) {
    return buildError({ ...(parsed as Record<string, unknown>), status: res.status });
  }
  return new CausewayError({
    kind: "HttpError",
    status: res.status,
    message: `HTTP ${res.status}`,
    data: body,
  });
}

function safeJsonParse(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

// ---- snake_case ↔ camelCase ----
// Causeway runs Python (snake_case) on the wire and TS (camelCase) in the editor.
// We walk plain-object trees only — arrays of objects descend, scalars and class
// instances (Blob, Date, FormData, …) pass through untouched.

const camelCache = new Map<string, string>();
const snakeCache = new Map<string, string>();

function snakeToCamel(s: string): string {
  const hit = camelCache.get(s);
  if (hit !== undefined) return hit;
  const out = s.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
  camelCache.set(s, out);
  return out;
}

function camelToSnake(s: string): string {
  const hit = snakeCache.get(s);
  if (hit !== undefined) return hit;
  const out = s.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
  snakeCache.set(s, out);
  return out;
}

function isPlainObject(x: unknown): x is Record<string, unknown> {
  return (
    Boolean(x) &&
    typeof x === "object" &&
    (Object.getPrototypeOf(x) === Object.prototype || Object.getPrototypeOf(x) === null)
  );
}

function snakeToCamelDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(snakeToCamelDeep);
  if (!isPlainObject(value)) return value;
  const out: Record<string, unknown> = {};
  for (const k of Object.keys(value)) out[snakeToCamel(k)] = snakeToCamelDeep(value[k]);
  return out;
}

function camelToSnakeDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(camelToSnakeDeep);
  if (!isPlainObject(value)) return value;
  const out: Record<string, unknown> = {};
  for (const k of Object.keys(value)) out[camelToSnake(k)] = camelToSnakeDeep(value[k]);
  return out;
}

// Opaque-subtree-aware variants. Routes declare opaque paths in their
// descriptor when they accept or return user-defined JSON payloads
// (`dict[str, Any]` / `JsonObject`). At each declared path we skip the
// recursive rename so the payload's own keys survive the round trip.

interface OpaqueTree {
  opaque?: boolean;
  children?: Record<string, OpaqueTree>;
}

function buildOpaqueTree(paths: ReadonlyArray<string> | undefined): OpaqueTree | null {
  if (!paths || paths.length === 0) return null;
  const root: OpaqueTree = {};
  for (const path of paths) {
    let node = root;
    for (const seg of path.split(".")) {
      if (!seg) continue;
      const children = node.children ?? (node.children = {});
      node = children[seg] ?? (children[seg] = {});
    }
    node.opaque = true;
  }
  return root;
}

function snakeToCamelDeepGuarded(value: unknown, tree: OpaqueTree | null): unknown {
  if (tree === null) return snakeToCamelDeep(value);
  // Arrays inherit the parent path — opaque paths are property-relative.
  if (Array.isArray(value)) return value.map((v) => snakeToCamelDeepGuarded(v, tree));
  if (!isPlainObject(value)) return value;
  const out: Record<string, unknown> = {};
  for (const k of Object.keys(value)) {
    const renamed = snakeToCamel(k);
    const child = tree.children?.[renamed];
    if (child?.opaque) {
      // Preserve the opaque subtree verbatim — don't even rename inside it.
      out[renamed] = value[k];
    } else if (child) {
      out[renamed] = snakeToCamelDeepGuarded(value[k], child);
    } else {
      out[renamed] = snakeToCamelDeep(value[k]);
    }
  }
  return out;
}

function camelToSnakeDeepGuarded(value: unknown, tree: OpaqueTree | null): unknown {
  if (tree === null) return camelToSnakeDeep(value);
  if (Array.isArray(value)) return value.map((v) => camelToSnakeDeepGuarded(v, tree));
  if (!isPlainObject(value)) return value;
  const out: Record<string, unknown> = {};
  for (const k of Object.keys(value)) {
    const child = tree.children?.[k];
    const renamed = camelToSnake(k);
    if (child?.opaque) {
      out[renamed] = value[k];
    } else if (child) {
      out[renamed] = camelToSnakeDeepGuarded(value[k], child);
    } else {
      out[renamed] = camelToSnakeDeep(value[k]);
    }
  }
  return out;
}
