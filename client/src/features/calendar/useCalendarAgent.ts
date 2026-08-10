/**
 * Calendar sub-agent chat hook (NUMA-114 P4, PLAN 21.2).
 *
 * Owns the agent dock: open/close, transcript (persisted in the calendar
 * store), send/abort and the Escape-to-close shortcut.
 *
 * Suggestions fill the composer, they do not send. The old code called
 * `setAgentInput(query)` and then fired the previous render's send callback on
 * a 100 ms timer, which read the stale (empty) input and sent nothing; the dead
 * timer is gone but the observable behavior is kept deliberately. Auto-sending
 * would make one click perform an unconfirmed write to the user's real Google
 * Calendar (the "Reschedule <event>" chip drives `modify_event_by_description`),
 * so the user reviews the prefilled text and presses Send.
 */
import { useCallback, useEffect, useRef, useState } from "react"

import { useCalendarStore } from "@/lib/stores"
import { sendAgentCommand } from "./calendar.api"
import { isAbortError } from "./calendar.utils"

export function useCalendarAgent() {
  const { agentMessages, setAgentMessages, addAgentMessage, fetchEvents } = useCalendarStore()

  const [agentOpen, setAgentOpen] = useState(false)
  const [agentInput, setAgentInput] = useState("")
  const [agentSending, setAgentSending] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const agentAbortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!agentOpen) return undefined

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAgentOpen(false)
    }

    globalThis.addEventListener("keydown", onKeyDown)
    return () => globalThis.removeEventListener("keydown", onKeyDown)
  }, [agentOpen])

  const sendMessage = useCallback(
    async () => {
      const query = agentInput.trim()
      if (!query || agentSending) return

      const controller = new AbortController()
      agentAbortRef.current = controller
      const nextHistory = [...agentMessages, { role: "user" as const, content: query }]
      setAgentMessages(nextHistory)
      setAgentInput("")
      setAgentSending(true)
      setAgentError(null)

      try {
        const result = await sendAgentCommand(query, nextHistory, controller.signal)
        addAgentMessage({ role: "assistant", content: result.response })

        if (result.refreshCalendar) await fetchEvents(true)
      } catch (err) {
        if (isAbortError(err)) {
          addAgentMessage({ role: "assistant", content: "Generation stopped." })
          return
        }
        const message = err instanceof Error ? err.message : "Calendar sub-agent request failed"
        setAgentError(message)
        addAgentMessage({ role: "assistant", content: `I hit an error: ${message}` })
      } finally {
        if (agentAbortRef.current === controller) agentAbortRef.current = null
        setAgentSending(false)
      }
    },
    [agentInput, agentSending, agentMessages, setAgentMessages, addAgentMessage, fetchEvents]
  )

  const stopMessage = useCallback(() => {
    agentAbortRef.current?.abort()
  }, [])

  // Prefill only: the user reviews the command and presses Send.
  const selectSuggestion = useCallback((query: string) => setAgentInput(query), [])

  const toggleAgent = useCallback(() => setAgentOpen((open) => !open), [])
  const closeAgent = useCallback(() => setAgentOpen(false), [])

  return {
    agentOpen,
    agentInput,
    agentSending,
    agentError,
    agentMessages,
    setAgentInput,
    toggleAgent,
    closeAgent,
    sendMessage,
    stopMessage,
    selectSuggestion,
  }
}

export type UseCalendarAgentReturn = ReturnType<typeof useCalendarAgent>
