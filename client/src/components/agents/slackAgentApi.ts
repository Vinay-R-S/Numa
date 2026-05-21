/**
 * Slack Sub-Agent API client
 * --------------------------
 * All calls go through /api/* which Next.js proxies to the FastAPI backend.
 */

// ── Types ──────────────────────────────────────────────────────────────────────

export interface SlackAgentMessage {
  role: "user" | "assistant"
  content: string
}

export interface SlackChatResponse {
  response: string
  success: boolean
  delegated_to?: string | null
  refresh_slack?: boolean
}

export interface SlackMessage {
  id: string
  user_id?: string | null
  slack_user_id: string
  sender_name?: string | null
  slack_channel_id: string
  channel_name?: string | null
  text?: string | null
  ts: string
  thread_ts?: string | null
  message_type: string
  created_at?: string | null
}

export interface SlackChannel {
  id: string
  slack_id: string
  name?: string | null
  team_id: string
  is_private: boolean
  created_at?: string | null
}

export interface SlackStatus {
  connected: boolean
  slack_user_id?: string | null
  slack_team_id?: string | null
  team_name?: string | null
  bot_configured: boolean
}

export interface SlackSyncResult {
  ok: boolean
  fetched: number
  channels: number
  detail?: string | null
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function authHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

const SLACK_AGENT_TIMEOUT_MS = 45_000

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    window.clearTimeout(timeoutId)
  }
}

async function parseJson<T>(res: Response, fallback: string): Promise<T> {
  if (!res.ok) {
    let detail = fallback
    try {
      const body = await res.json()
      if (typeof body?.detail === "string") detail = body.detail
    } catch {
      // keep fallback
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

// ── Chat ───────────────────────────────────────────────────────────────────────

export async function sendSlackAgentCommand(
  query: string,
  history: SlackAgentMessage[] = []
): Promise<SlackChatResponse> {
  let res: Response
  try {
    res = await fetchWithTimeout(
      "/api/slack/chat",
      {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ query, history }),
      },
      SLACK_AGENT_TIMEOUT_MS
    )
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Slack agent request timed out. The action may still have completed in Slack.")
    }
    throw err
  }
  const data = await parseJson<SlackChatResponse>(res, "Slack agent request failed")
  if (data.success === false) {
    throw new Error(data.response || "Slack agent request failed")
  }
  return data
}

// ── Messages ───────────────────────────────────────────────────────────────────

export async function getSlackMessages(params?: {
  channel?: string
  limit?: number
}): Promise<SlackMessage[]> {
  const qs = new URLSearchParams()
  if (params?.channel) qs.set("channel", params.channel)
  if (params?.limit)   qs.set("limit",   String(params.limit))

  const res = await fetch(`/api/slack/messages?${qs.toString()}`, {
    headers: authHeaders(),
  })
  return parseJson<SlackMessage[]>(res, "Failed to fetch Slack messages")
}

// ── Channels ───────────────────────────────────────────────────────────────────

export async function getSlackChannels(): Promise<SlackChannel[]> {
  const res = await fetch("/api/slack/channels", { headers: authHeaders() })
  return parseJson<SlackChannel[]>(res, "Failed to fetch Slack channels")
}

// ── Status ─────────────────────────────────────────────────────────────────────

export async function getSlackStatus(): Promise<SlackStatus> {
  const res = await fetch("/api/slack/status", { headers: authHeaders() })
  return parseJson<SlackStatus>(res, "Failed to fetch Slack status")
}

// ── Sync ─────────────────────────────────────────────────────────────────────

export async function syncSlack(): Promise<SlackSyncResult> {
  const res = await fetch("/api/slack/sync", {
    method: "POST",
    headers: authHeaders(),
  })
  return parseJson<SlackSyncResult>(res, "Failed to sync Slack")
}

// ── Send Message ───────────────────────────────────────────────────────────────

export interface SlackSendResult {
  ok: boolean
  ts?: string | null
  error?: string | null
}

export async function sendSlackMessage(
  channelId: string,
  text: string,
  threadTs?: string
): Promise<SlackSendResult> {
  const res = await fetch("/api/slack/send", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      channel_id: channelId,
      text,
      ...(threadTs ? { thread_ts: threadTs } : {}),
    }),
  })
  return parseJson<SlackSendResult>(res, "Failed to send Slack message")
}

// ── Connect ────────────────────────────────────────────────────────────────────

export async function connectSlack(): Promise<void> {
  const token = typeof window !== "undefined" ? localStorage.getItem("numa_token") : null
  if (!token) {
    window.location.href = "/auth"
    return
  }

  const res = await fetch("/api/slack/connect-url", {
    headers: authHeaders(),
  })
  const data = await parseJson<{ authorization_url: string }>(
    res,
    "Failed to start Slack authorization"
  )

  if (!data.authorization_url) {
    throw new Error("Slack authorization URL was not returned")
  }

  window.location.href = data.authorization_url
}

// ── Format helpers ─────────────────────────────────────────────────────────────

/** Strip Slack mrkdwn tokens for human-readable display */
export function formatSlackText(text: string): string {
  return text
    .replace(/<@([A-Z0-9]+)>/g, "@user")
    .replace(/<!channel>/g, "@channel")
    .replace(/<!here>/g, "@here")
    .replace(/<!everyone>/g, "@everyone")
    .replace(/<#[A-Z0-9]+\|([^>]+)>/g, "#$1")
    .replace(/<([^|>]+)\|([^>]+)>/g, "$2")
    .replace(/<([^>]+)>/g, "$1")
}
