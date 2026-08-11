/**
 * Slack domain types (NUMA-115 P4, PLAN 5.3 / 21.2).
 *
 * Mirrors the response models in `server/src/slack_agent/schemas.py`. Moved out
 * of `components/agents/slackAgentApi.ts` unchanged.
 */

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

export interface SlackSendResult {
  ok: boolean
  ts?: string | null
  error?: string | null
}

export interface SlackConnectUrlResponse {
  authorization_url: string
}

/** Why a message matters to the signed-in user: a direct mention or a broadcast. */
export interface MessageRelevance {
  isDirect: boolean
  isBroadcast: boolean
}
