"use client"

import type { RefObject } from "react"

import { AgentDockPanel } from "@/features/agents"
import { SLACK_AGENT_SUGGESTIONS } from "../slack.constants"
import type { SlackAgentMessage } from "../slack.types"

/**
 * Slack sub-agent dock (NUMA-115 P4 / NUMA-118 P4).
 *
 * The markup moved verbatim into the shared `AgentDockPanel`, which the health
 * dock renders too; only this feature's copy stays here. The element ids
 * (`slack-chat-input`, `slack-send-btn`, the per-chip ids) and the entry
 * animation are preserved through props.
 */
interface SlackAgentPanelProps {
  messages: SlackAgentMessage[]
  input: string
  sending: boolean
  canSend: boolean
  error: string | null
  endRef: RefObject<HTMLDivElement | null>
  onInputChange: (value: string) => void
  onSend: () => void
  onStop: () => void
  onSelectSuggestion: (query: string) => void
  onClose: () => void
}

export function SlackAgentPanel(props: SlackAgentPanelProps) {
  return (
    <AgentDockPanel
      {...props}
      title="Slack Agent"
      badge="Groq · LangGraph"
      placeholder="Ask the Slack agent…"
      suggestions={SLACK_AGENT_SUGGESTIONS}
      animated
      idPrefix="slack-suggestion"
      inputId="slack-chat-input"
      sendButtonId="slack-send-btn"
    />
  )
}
