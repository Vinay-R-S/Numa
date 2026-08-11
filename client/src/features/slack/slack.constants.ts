/**
 * Slack feature constants (NUMA-115 P4).
 *
 * Values lifted verbatim from `slack/page.tsx` so the polling cadence, the page
 * size and the agent greeting stay exactly what they were.
 */
import type { SlackAgentMessage } from "./slack.types"

/** Channel poll: sync when connected, plain reload otherwise. */
export const POLL_INTERVAL_MS = 20_000

export const MESSAGE_PAGE_SIZE = 60

export const SLACK_AGENT_SESSION_KEY = "numa:session:slack-agent-chat"

export const SLACK_AGENT_GREETING: SlackAgentMessage[] = [
  {
    role: "assistant",
    content:
      "Hi! I'm your NUMA Slack agent. I can search your Slack messages, send messages to channels, and create tasks from Slack discussions. What would you like to do?",
  },
]

export const SLACK_AGENT_SUGGESTIONS = [
  "Show recent messages",
  "Create a task from Slack",
  "List Slack tasks",
]
