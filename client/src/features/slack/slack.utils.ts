/**
 * Slack pure helpers (NUMA-115 P4, PLAN 17.4).
 *
 * Display formatting and message classification lifted verbatim from
 * `slack/page.tsx` and `components/agents/slackAgentApi.ts`.
 */
import type { MessageRelevance, SlackChannel, SlackMessage } from "./slack.types"

// One home for the fetch-abort check: lib/http owns it.
export { isAbortError } from "@/lib/http"

export function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return ""

  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`

  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`

  return `${Math.floor(hrs / 24)}d ago`
}

export function formatTime(dateStr: string | null | undefined): string {
  if (!dateStr) return ""
  return new Date(dateStr).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

export function getRelevance(text: string, slackUserId?: string | null): MessageRelevance {
  const isDirect = Boolean(slackUserId && text.includes(`<@${slackUserId}>`))
  const isBroadcast =
    text.includes("<!channel>") || text.includes("<!here>") || text.includes("<!everyone>")
  return { isDirect, isBroadcast }
}

export function channelDisplayName(channel: SlackChannel): string {
  return channel.name || channel.slack_id
}

export function isDirectMessageChannel(channel: SlackChannel): boolean {
  return Boolean(channel.name?.startsWith("dm-") || channel.name?.startsWith("mpdm-"))
}

export function isThreadReply(message: SlackMessage): boolean {
  return Boolean(message.thread_ts && message.thread_ts !== message.ts)
}

/** DB timestamp when present, else the Slack epoch-seconds `ts`. */
export function messageTimestamp(message: SlackMessage): number {
  return new Date(message.created_at || Number(message.ts) * 1000).getTime()
}

export function sortMessagesByTime(messages: SlackMessage[]): SlackMessage[] {
  return [...messages].sort((a, b) => messageTimestamp(a) - messageTimestamp(b))
}

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
