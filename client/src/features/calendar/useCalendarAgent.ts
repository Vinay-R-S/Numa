"use client"

/**
 * Calendar sub-agent chat hook (NUMA-114 P4 / NUMA-118 P4, PLAN 21.2).
 *
 * Rebuilt on the shared `useAgentChat`: the dock state, the Escape shortcut,
 * send/abort and the transcript bookkeeping live there. What stays here is the
 * store-backed transcript (the calendar keeps its turns in `useCalendarStore`,
 * whose setter takes an array and whose append is a separate action, which is
 * why the shared hook takes `replace`/`append` rather than a `setState`), the
 * awaited event refetch, and this dock's own error wording.
 *
 * Suggestions fill the composer, they do not send. The old code called
 * `setAgentInput(query)` and then fired the previous render's send callback on
 * a 100 ms timer, which read the stale (empty) input and sent nothing; the dead
 * timer is gone but the observable behavior is kept deliberately. Auto-sending
 * would make one click perform an unconfirmed write to the user's real Google
 * Calendar (the "Reschedule <event>" chip drives `modify_event_by_description`),
 * so the user reviews the prefilled text and presses Send.
 *
 * The public return shape is unchanged, so `calendar/page.tsx` is untouched.
 */
import { useCallback } from "react"

import { useAgentChat } from "@/features/agents"
import { useCalendarStore } from "@/lib/stores"
import { sendAgentCommand } from "./calendar.api"
import type { AgentChatMessage, AgentChatResponse } from "./calendar.types"

export function useCalendarAgent() {
  // Selector per slice, not the whole store. Subscribing to the store object
  // re-rendered every consumer of this hook on any calendar state change, so
  // one agent message re-rendered the entire month grid (NUMA-142 P6, PLAN 9).
  const agentMessages = useCalendarStore((state) => state.agentMessages)
  const setAgentMessages = useCalendarStore((state) => state.setAgentMessages)
  const addAgentMessage = useCalendarStore((state) => state.addAgentMessage)
  const fetchEvents = useCalendarStore((state) => state.fetchEvents)

  const onResult = useCallback(
    async (result: AgentChatResponse) => {
      if (result.refreshCalendar) await fetchEvents(true)
    },
    [fetchEvents]
  )

  const chat = useAgentChat<AgentChatMessage, AgentChatResponse>({
    transcript: {
      messages: agentMessages,
      replace: setAgentMessages,
      append: addAgentMessage,
    },
    send: sendAgentCommand,
    onResult,
    errorFallback: "Calendar sub-agent request failed",
    errorPrefix: "I hit an error: ",
  })

  return {
    agentOpen: chat.open,
    agentInput: chat.input,
    agentSending: chat.sending,
    agentError: chat.error,
    agentMessages: chat.messages,
    setAgentInput: chat.setInput,
    toggleAgent: chat.toggleAgent,
    closeAgent: chat.closeAgent,
    sendMessage: chat.sendMessage,
    stopMessage: chat.stopMessage,
    selectSuggestion: chat.selectSuggestion,
  }
}

export type UseCalendarAgentReturn = ReturnType<typeof useCalendarAgent>
