"use client"

/**
 * Health sub-agent chat hook (NUMA-116 P4 / NUMA-118 P4, PLAN 17.2 / 21.2 / 22.2).
 *
 * Rebuilt on the shared `useAgentChat`: the dock state, the Escape shortcut,
 * send/abort and the transcript bookkeeping live there. What stays here is the
 * session-backed transcript, the health-specific refresh (`refresh_health`) and
 * the input validation, which still runs through `healthChatRequestSchema`
 * (mirrors `HealthChatRequest`) rather than a bare trim.
 *
 * The public return shape is unchanged, so `health/page.tsx` is untouched.
 */
import { useCallback } from "react"

import { useAgentChat } from "@/features/agents"
import { useSessionMessages } from "@/lib/useSessionMessages"
import { sendHealthAgentCommand } from "./health.api"
import { HEALTH_AGENT_GREETING, HEALTH_AGENT_SESSION_KEY } from "./health.constants"
import { healthChatRequestSchema } from "./health.schema"
import type { HealthAgentMessage, HealthChatResponse } from "./health.types"

/** Mirrors `HealthChatRequest`; rejects the input instead of trimming it. */
function normalizeHealthQuery(raw: string): string | null {
  const parsed = healthChatRequestSchema.safeParse({ query: raw })
  return parsed.success ? parsed.data.query : null
}

export function useHealthAgent(onHealthRefresh?: () => void) {
  const [messages, setMessages] = useSessionMessages<HealthAgentMessage>(
    HEALTH_AGENT_SESSION_KEY,
    HEALTH_AGENT_GREETING
  )

  const append = useCallback(
    (message: HealthAgentMessage) => setMessages((prev) => [...prev, message]),
    [setMessages]
  )

  const onResult = useCallback(
    (result: HealthChatResponse) => {
      if (result.refresh_health) onHealthRefresh?.()
    },
    [onHealthRefresh]
  )

  const chat = useAgentChat<HealthAgentMessage, HealthChatResponse>({
    transcript: { messages, replace: setMessages, append },
    send: sendHealthAgentCommand,
    onResult,
    normalizeQuery: normalizeHealthQuery,
  })

  return {
    agentOpen: chat.open,
    messages: chat.messages,
    input: chat.input,
    sending: chat.sending,
    error: chat.error,
    canSend: chat.canSend,
    chatEndRef: chat.chatEndRef,
    setInput: chat.setInput,
    toggleAgent: chat.toggleAgent,
    closeAgent: chat.closeAgent,
    sendMessage: chat.sendMessage,
    stopMessage: chat.stopMessage,
    selectSuggestion: chat.selectSuggestion,
  }
}

export type UseHealthAgentReturn = ReturnType<typeof useHealthAgent>
