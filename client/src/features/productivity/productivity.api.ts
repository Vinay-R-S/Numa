/**
 * Productivity API (NUMA-117 P4, PLAN 17.5 / 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client, replacing the
 * `API_BASE`/`getAuthHeaders`/`parseError` helpers that lived in
 * `components/productivity/productivityApi.ts`. Per-endpoint fallback error text
 * is preserved via `errorMessage` (the backend `{ detail }` still wins) and
 * responses are validated with the feature's zod schemas.
 *
 * Behavior notes carried over deliberately:
 * - `connectGitHub` still rejects an authorization URL that does not point at
 *   GitHub's authorize endpoint, so a compromised or misconfigured backend
 *   cannot redirect the browser somewhere else.
 * - `getGitHubStats` only sends `force` when forcing, exactly as the old query
 *   string did.
 * - `getIntegrationKeys` is the typed replacement for the raw `fetch` the page
 *   ran to discover the configured LeetCode username; callers keep swallowing
 *   its failures (it is a best-effort prefill, not an error state).
 * - Every endpoint here answers with JSON except `disconnectGitHub` (204).
 *   `http` resolves a body-less or non-JSON 2xx to `undefined` (a proxy dropping
 *   the content-type header is enough), which would put `undefined` into React
 *   state and crash the next render, so `expectBody` turns that into the
 *   endpoint's error.
 */
import { expectBody, http } from "@/lib/http"
import { GITHUB_AUTHORIZE_URL_PREFIX, assertExternalUrl } from "@/lib/externalUrl"
import {
  githubAuthStatusSchema,
  githubConnectResponseSchema,
  githubStatsSchema,
  integrationKeysSchema,
  leetCodeStatsSchema,
} from "./productivity.schema"
import type {
  GitHubAuthStatus,
  GitHubStats,
  IntegrationKeys,
  LeetCodeStats,
} from "./productivity.types"

export function getGitHubStatus(): Promise<GitHubAuthStatus> {
  const message = "Failed to fetch GitHub status"
  return expectBody(
    http.get("/github/status", { schema: githubAuthStatusSchema, errorMessage: message }),
    message
  )
}

export async function connectGitHub(): Promise<string> {
  const message = "Failed to get GitHub auth URL"
  const data = await expectBody(
    http.get("/github/connect", { schema: githubConnectResponseSchema, errorMessage: message }),
    message
  )

  // The shared guard, so the same check covers Google, Slack and the calendar
  // reconnect URL rather than GitHub alone (NUMA-142 P6, PLAN 8).
  return assertExternalUrl(data.authorization_url, [GITHUB_AUTHORIZE_URL_PREFIX], "GitHub")
}

export function connectGitHubToken(accessToken: string): Promise<GitHubAuthStatus> {
  const message = "Failed to connect GitHub token"
  return expectBody(
    http.post("/github/connect-token", { access_token: accessToken }, {
      schema: githubAuthStatusSchema,
      errorMessage: message,
    }),
    message
  )
}

export function getGitHubStats(force = false): Promise<GitHubStats> {
  const message = "Failed to fetch GitHub stats"
  return expectBody(
    http.get("/github/stats", {
      query: { force: force || undefined },
      schema: githubStatsSchema,
      errorMessage: message,
    }),
    message
  )
}

export function disconnectGitHub(): Promise<void> {
  return http.del("/github/disconnect", { errorMessage: "Failed to disconnect GitHub" })
}

export function getLeetCodeStats(username: string): Promise<LeetCodeStats> {
  const message = "Failed to fetch LeetCode stats"
  return expectBody(
    http.get("/leetcode/stats", {
      query: { username },
      schema: leetCodeStatsSchema,
      errorMessage: message,
    }),
    message
  )
}

export function getIntegrationKeys(): Promise<IntegrationKeys> {
  const message = "Failed to fetch integration keys"
  return expectBody(
    http.get("/ai-settings/integration-keys", {
      schema: integrationKeysSchema,
      errorMessage: message,
    }),
    message
  )
}
