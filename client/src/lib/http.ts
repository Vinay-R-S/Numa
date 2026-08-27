/**
 * Shared HTTP client (NUMA-110 P4, PLAN 21.2 / 22.2).
 *
 * One fetch wrapper for the whole client: attaches the auth header, serializes
 * JSON bodies, builds query strings, and maps the backend `{ detail }` envelope
 * to a typed ApiError. Feature `<feature>.api.ts` modules build on this instead
 * of re-declaring authHeaders/parseJson.
 *
 * Base URL honors `NEXT_PUBLIC_API_URL` (empty -> relative, so requests go
 * through the Next.js `/api/*` proxy to FastAPI). Leave it empty: `buildUrl`
 * always prefixes `/api`, which the proxy then strips, so pointing the var at
 * FastAPI directly 404s the eight routers that mount without an `/api` prefix.
 * Removing the double prefix is Tier 0 work (PLAN NUMA-116 deferred item).
 */
import type { ZodType } from "zod"

const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL || ""
const TOKEN_KEY = "numa_token"

export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

export type QueryParams = Record<string, string | number | boolean | null | undefined>

export interface RequestOptions<T> {
  method?: string
  body?: unknown
  query?: QueryParams
  headers?: HeadersInit
  signal?: AbortSignal
  cache?: RequestCache
  schema?: ZodType<T>
  errorMessage?: string
  /** Abort the request if the response headers do not arrive in time. */
  timeoutMs?: number
  /** Message thrown when `timeoutMs` elapses. Caller-abort still throws AbortError. */
  timeoutMessage?: string
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEY)
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

function withQuery(url: string, query?: QueryParams): string {
  if (!query) return url
  const qs = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    qs.set(key, String(value))
  })
  const search = qs.toString()
  return search ? `${url}?${search}` : url
}

function buildUrl(path: string, query?: QueryParams): string {
  if (/^https?:\/\//i.test(path)) return withQuery(path, query)
  const normalized = path.startsWith("/") ? path : `/${path}`
  const withApi = normalized === "/api" || normalized.startsWith("/api/") ? normalized : `/api${normalized}`
  return withQuery(`${API_ORIGIN}${withApi}`, query)
}

function isJsonBody(body: unknown): boolean {
  if (body === undefined || body === null) return false
  if (typeof body === "string") return false
  if (
    body instanceof FormData ||
    body instanceof Blob ||
    body instanceof ArrayBuffer ||
    body instanceof URLSearchParams
  ) {
    return false
  }
  return true
}

async function extractDetail(res: Response, fallback: string): Promise<string> {
  try {
    const body: unknown = await res.json()
    if (body && typeof body === "object" && "detail" in body) {
      const { detail } = body as { detail: unknown }
      if (typeof detail === "string") return detail
    }
  } catch {
    // No JSON body; fall back to the generic message.
  }
  return fallback
}

/**
 * Runs the fetch under an optional timeout. The timer is disarmed as soon as
 * the response headers arrive, so reading and parsing a slow body is never
 * counted against the deadline.
 */
async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs?: number,
  timeoutMessage?: string
): Promise<Response> {
  if (!timeoutMs) return fetch(url, init)

  const controller = new AbortController()
  const callerSignal = init.signal
  const abortFromCaller = () => controller.abort()
  callerSignal?.addEventListener("abort", abortFromCaller, { once: true })
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } catch (error) {
    if (!callerSignal?.aborted && isAbortError(error)) {
      throw new Error(timeoutMessage || "Request timed out")
    }
    throw error
  } finally {
    callerSignal?.removeEventListener("abort", abortFromCaller)
    clearTimeout(timeoutId)
  }
}

export async function request<T>(path: string, options: RequestOptions<T> = {}): Promise<T> {
  const {
    method = "GET",
    body,
    query,
    headers,
    signal,
    cache,
    schema,
    errorMessage,
    timeoutMs,
    timeoutMessage,
  } = options
  const token = getAuthToken()

  const finalHeaders = new Headers(headers)
  if (token && !finalHeaders.has("Authorization")) finalHeaders.set("Authorization", `Bearer ${token}`)
  if (isJsonBody(body) && !finalHeaders.has("Content-Type")) finalHeaders.set("Content-Type", "application/json")

  const res = await fetchWithTimeout(
    buildUrl(path, query),
    {
      method,
      headers: finalHeaders,
      body: isJsonBody(body) ? JSON.stringify(body) : (body as BodyInit | undefined),
      signal,
      cache,
    },
    timeoutMs,
    timeoutMessage
  )

  if (!res.ok) {
    const fallback = errorMessage || res.statusText || `Request failed (${res.status})`
    throw new ApiError(res.status, await extractDetail(res, fallback))
  }

  if (res.status === 204) return undefined as T
  if (!(res.headers.get("content-type") || "").includes("application/json")) return undefined as T

  const text = await res.text()
  if (!text) return undefined as T
  const data = JSON.parse(text) as T
  return schema ? schema.parse(data) : data
}

/**
 * Rejects a body-less 2xx for endpoints that must answer with JSON.
 *
 * `request` resolves to `undefined` for a 204, an empty body or a response
 * without a JSON content-type (a proxy dropping the header is enough), which
 * would otherwise put `undefined` into React state and crash the next render.
 * It is opt-in rather than built into `request` because
 * `checkCalendarTokenHealth` deliberately relies on the undefined-body path.
 */
export async function expectBody<T>(pending: Promise<T>, message: string): Promise<T> {
  const data = await pending
  if (data === undefined) throw new Error(message)
  return data
}

export const http = {
  get: <T>(path: string, options?: Omit<RequestOptions<T>, "method" | "body">) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions<T>, "method" | "body">) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: Omit<RequestOptions<T>, "method" | "body">) =>
    request<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions<T>, "method" | "body">) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  del: <T>(path: string, options?: Omit<RequestOptions<T>, "method" | "body">) =>
    request<T>(path, { ...options, method: "DELETE" }),
}
