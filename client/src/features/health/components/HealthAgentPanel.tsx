"use client"

import type { RefObject } from "react"

import { AgentDockPanel } from "@/features/agents"
import { HEALTH_AGENT_SUGGESTIONS } from "../health.constants"
import type { HealthAgentMessage } from "../health.types"

/**
 * Health sub-agent dock (NUMA-116 P4 / NUMA-118 P4).
 *
 * The markup moved verbatim into the shared `AgentDockPanel`, which the slack
 * dock renders too; only this feature's copy stays here. This dock never
 * animated its turns in, so it does not pass `animated`.
 */
interface HealthAgentPanelProps {
  messages: HealthAgentMessage[]
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

export function HealthAgentPanel(props: HealthAgentPanelProps) {
  return (
    <AgentDockPanel
      {...props}
      title="Health Agent"
      badge="Groq • LangGraph"
      placeholder="Ask the Health agent..."
      suggestions={HEALTH_AGENT_SUGGESTIONS}
    />
  )
}
