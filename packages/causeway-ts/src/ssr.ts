export const DEFAULT_FORWARDED_HEADERS: readonly string[] = [
  "cookie",
  "authorization",
  "x-csrf-token",
  "x-request-id",
  "accept-language",
  "x-forwarded-for",
  "x-forwarded-proto",
  "x-forwarded-host",
] as const;

export type HeaderRecordValue = string | readonly string[] | null | undefined;
export type HeaderRecord = Record<string, HeaderRecordValue>;
export type HeadersLike = Pick<Headers, "get">;
export type HeaderSource =
  | HeadersLike
  | { headers: HeadersLike | HeaderRecord }
  | HeaderRecord
  | null
  | undefined;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isThenable(value: unknown): value is PromiseLike<unknown> {
  if ((typeof value !== "object" && typeof value !== "function") || value === null) {
    return false;
  }
  return typeof (value as { then?: unknown }).then === "function";
}

function hasGet(value: unknown): value is HeadersLike {
  return isObject(value) && typeof value.get === "function";
}

function normalizeHeaderValue(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    const parts = value.filter((item): item is string => typeof item === "string");
    return parts.length > 0 ? parts.join(", ") : null;
  }
  return null;
}

function readRecordHeader(headers: Record<string, unknown>, name: string): string | null {
  const exactValue = normalizeHeaderValue(headers[name]);
  if (exactValue != null) return exactValue;

  const lowerName = name.toLowerCase();
  const lowerValue = normalizeHeaderValue(headers[lowerName]);
  if (lowerValue != null) return lowerValue;

  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() === lowerName) {
      return normalizeHeaderValue(value);
    }
  }

  return null;
}

function unwrapHeaders(source: HeaderSource): HeadersLike | HeaderRecord | null | undefined {
  if (isThenable(source)) {
    throw new TypeError("forwardHeaders received a Promise; await headers() before calling it.");
  }
  if (isObject(source) && "headers" in source) {
    const { headers } = source;
    if (isThenable(headers)) {
      throw new TypeError(
        "forwardHeaders received Promise headers; await headers() before calling it.",
      );
    }
    return headers as HeadersLike | HeaderRecord | null | undefined;
  }
  return source as HeadersLike | HeaderRecord | null | undefined;
}

/** Pull a subset of headers off an incoming Request to replay on an outgoing Causeway call. */
export function forwardHeaders(
  source: HeaderSource,
  names: readonly string[] = DEFAULT_FORWARDED_HEADERS,
): Record<string, string> {
  const headers = unwrapHeaders(source);
  const out: Record<string, string> = {};

  if (headers == null) return out;

  for (const name of names) {
    const value = hasGet(headers) ? headers.get(name) : readRecordHeader(headers, name);
    if (value != null) out[name.toLowerCase()] = value;
  }
  return out;
}
