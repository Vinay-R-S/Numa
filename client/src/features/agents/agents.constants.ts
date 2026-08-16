/**
 * Master agent dock constants (NUMA-118 P4).
 *
 * Moved with the hook from `features/dashboard`; the session key is unchanged
 * so an open transcript survives the refactor.
 */
import type { MasterAgentMessage } from "./agents.types"

export const MASTER_AGENT_SESSION_KEY = "numa:session:master-agent-chat"

export const MASTER_AGENT_GREETING =
  "I'm your Master Agent. I can manage Calendar, Tasks, Slack, Health, GitHub, LeetCode, and Journal for you. What would you like to do?"

export const MASTER_AGENT_GREETING_MESSAGES: MasterAgentMessage[] = [
  { role: "assistant", content: MASTER_AGENT_GREETING },
]
