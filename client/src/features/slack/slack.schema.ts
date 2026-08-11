/**
 * Slack validation schemas (NUMA-115 P4, PLAN 22.2 / 22.3).
 *
 * Mirrors the Pydantic DTOs in `server/src/slack_agent/schemas.py`. Response
 * schemas run through the shared `http` `schema` option so contract drift fails
 * loudly; the input schema mirrors `SlackSendMessageRequest` for the composer.
 *
 * `created_at` is kept as a plain string: the backend serializes a datetime and
 * the UI formats it, so structure is validated without coercing the value.
 */
import { z } from "@/lib/validation"
import type {
  SlackChannel,
  SlackChatResponse,
  SlackConnectUrlResponse,
  SlackMessage,
  SlackSendResult,
  SlackStatus,
  SlackSyncResult,
} from "./slack.types"

export const slackMessageSchema: z.ZodType<SlackMessage> = z.object({
  id: z.string(),
  user_id: z.string().nullish(),
  slack_user_id: z.string(),
  sender_name: z.string().nullish(),
  slack_channel_id: z.string(),
  channel_name: z.string().nullish(),
  text: z.string().nullish(),
  ts: z.string(),
  thread_ts: z.string().nullish(),
  message_type: z.string(),
  created_at: z.string().nullish(),
})

export const slackMessageListSchema = z.array(slackMessageSchema)

export const slackChannelSchema: z.ZodType<SlackChannel> = z.object({
  id: z.string(),
  slack_id: z.string(),
  name: z.string().nullish(),
  team_id: z.string(),
  is_private: z.boolean(),
  created_at: z.string().nullish(),
})

export const slackChannelListSchema = z.array(slackChannelSchema)

export const slackStatusSchema: z.ZodType<SlackStatus> = z.object({
  connected: z.boolean(),
  slack_user_id: z.string().nullish(),
  slack_team_id: z.string().nullish(),
  team_name: z.string().nullish(),
  bot_configured: z.boolean(),
})

export const slackSyncResultSchema: z.ZodType<SlackSyncResult> = z.object({
  ok: z.boolean(),
  fetched: z.number(),
  channels: z.number(),
  detail: z.string().nullish(),
})

export const slackSendResultSchema: z.ZodType<SlackSendResult> = z.object({
  ok: z.boolean(),
  ts: z.string().nullish(),
  error: z.string().nullish(),
})

export const slackChatResponseSchema: z.ZodType<SlackChatResponse> = z.object({
  response: z.string(),
  success: z.boolean(),
  delegated_to: z.string().nullish(),
  refresh_slack: z.boolean().optional(),
})

export const slackConnectUrlSchema: z.ZodType<SlackConnectUrlResponse> = z.object({
  authorization_url: z.string(),
})

/** Input schema for the channel composer; mirrors `SlackSendMessageRequest`. */
export const slackSendMessageSchema = z.object({
  channel_id: z.string().trim().min(1),
  text: z.string().trim().min(1),
  thread_ts: z.string().optional(),
})

export type SlackSendMessageInput = z.infer<typeof slackSendMessageSchema>
