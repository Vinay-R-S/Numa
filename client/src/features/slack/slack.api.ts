/**
 * Slack API (NUMA-115 P4, PLAN 17.5 / 21.2 / 22.2).
 *
 * Typed fetchers built on the shared `http` client, replacing the per-feature
 * `authHeaders`/`parseJson`/`fetchWithTimeout` helpers that lived in
 * `components/agents/slackAgentApi.ts`. Per-endpoint fallback error text is
 * preserved via `errorMessage` (the backend `{ detail }` still wins) and
 * responses are validated with the feature's zod schemas.
 *
 * Behavior notes carried over deliberately:
 * - `sendSlackAgentCommand` keeps the 45s timeout surfaced as its own message,
 *   still forwards an external abort untouched (so the caller can tell "user
 *   stopped" from "timed out"), and still throws on the
 *   200-with-`{ success: false }` agent envelope. The timeout is the shared
 *   `http` one, which disarms once response headers arrive, so a slow body read
 *   or a large agent answer is never counted against the deadline.
 * - `connectSlack` still bounces to `/auth` when no token is stored, instead of
 *   firing a request that would only 401.
 * - Every endpoint here answers with JSON. `http` resolves a body-less or
 *   non-JSON 2xx to `undefined` (a proxy that drops the content-type header is
 *   enough), which would put `undefined` into React state and crash the page on
 *   the next render, so `expectBody` turns that into the endpoint's error.
 */
import { expectBody, getAuthToken, http } from "@/lib/http"
import {
  slackChannelListSchema,
  slackChatResponseSchema,
  slackConnectUrlSchema,
  slackMessageListSchema,
  slackSendResultSchema,
  slackStatusSchema,
  slackSyncResultSchema,
} from "./slack.schema"
import type {
  SlackAgentMessage,
  SlackChannel,
  SlackChatResponse,
  SlackMessage,
  SlackSendResult,
  SlackStatus,
  SlackSyncResult,
} from "./slack.types"
const SLACK_AGENT_TIMEOUT_MS = 45_000
const AGENT_TIMEOUT_MESSAGE =
  "Slack agent request timed out. The action may still have completed in Slack."

/** Reject instead of handing `undefined` to the caller (see the header note). */
export async function sendSlackAgentCommand(
  query: string,
  history: SlackAgentMessage[] = [],
  signal?: AbortSignal
): Promise<SlackChatResponse> {
  const data = await expectBody(
    http.post("/slack/chat", { query, history }, {
      signal,
      timeoutMs: SLACK_AGENT_TIMEOUT_MS,
      timeoutMessage: AGENT_TIMEOUT_MESSAGE,
      schema: slackChatResponseSchema,
      errorMessage: "Slack agent request failed",
    }),
    "Slack agent request failed"
  )

  if (data.success === false) throw new Error(data.response || "Slack agent request failed")

  return data
}

export function getSlackMessages(params?: {
  channel?: string
  limit?: number
}): Promise<SlackMessage[]> {
  const message = "Failed to fetch Slack messages"
  return expectBody(
    http.get("/slack/messages", {
      query: { channel: params?.channel || undefined, limit: params?.limit || undefined },
      schema: slackMessageListSchema,
      errorMessage: message,
    }),
    message
  )
}

export function getSlackChannels(): Promise<SlackChannel[]> {
  const message = "Failed to fetch Slack channels"
  return expectBody(
    http.get("/slack/channels", { schema: slackChannelListSchema, errorMessage: message }),
    message
  )
}

export function getSlackStatus(): Promise<SlackStatus> {
  const message = "Failed to fetch Slack status"
  return expectBody(
    http.get("/slack/status", { schema: slackStatusSchema, errorMessage: message }),
    message
  )
}

export function syncSlack(): Promise<SlackSyncResult> {
  const message = "Failed to sync Slack"
  return expectBody(
    http.post("/slack/sync", undefined, { schema: slackSyncResultSchema, errorMessage: message }),
    message
  )
}

export function sendSlackMessage(
  channelId: string,
  text: string,
  threadTs?: string
): Promise<SlackSendResult> {
  const message = "Failed to send Slack message"
  return expectBody(
    http.post(
      "/slack/send",
      { channel_id: channelId, text, ...(threadTs ? { thread_ts: threadTs } : {}) },
      { schema: slackSendResultSchema, errorMessage: message }
    ),
    message
  )
}

export async function connectSlack(): Promise<void> {
  if (!getAuthToken()) {
    globalThis.location.href = "/auth"
    return
  }

  const message = "Failed to start Slack authorization"
  const data = await expectBody(
    http.get("/slack/connect-url", { schema: slackConnectUrlSchema, errorMessage: message }),
    message
  )

  if (!data.authorization_url) throw new Error("Slack authorization URL was not returned")

  globalThis.location.href = data.authorization_url
}
