/**
 * Agent domain types (NUMA-118 P4, PLAN 17.5 / 21.2).
 *
 * `AgentChatMessage` is the transcript turn every dock speaks. The four feature
 * agents (calendar, slack, health, master) declare structurally identical turn
 * types in their own modules; `useAgentChat` is generic over this shape so they
 * keep their own names without a conversion at the boundary.
 */

export interface AgentChatMessage {
  role: "user" | "assistant"
  content: string
}

/** Kept as the historical alias used by the master agent call sites. */
export type MasterAgentMessage = AgentChatMessage

/** Mirrors `MasterAgentChatResponse` in `server/src/master_agent/schemas.py`. */
export interface MasterAgentResponse {
  response: string
  success: boolean
  delegated_to?: string | null
  refreshCalendar?: boolean
  refreshTasks?: boolean
  refreshSlack?: boolean
  refreshHealth?: boolean
  refreshGithub?: boolean
  refreshJournal?: boolean
}

/** Mirrors `MasterAgentFetchLatestResponse`; `results` is `list[dict]` server-side. */
export interface MasterAgentFetchLatestResponse {
  ok: boolean
  scope: string
  users: number
  results: Array<Record<string, unknown>>
  retention: Record<string, unknown>
}

export interface FetchLatestOptions {
  background?: boolean
}
