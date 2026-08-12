"use client"

/**
 * Health sub-agent chat hook (NUMA-116 P4, PLAN 17.2 / 21.2 / 22.2).
 *
 * Owns the floating agent dock: open/close, the session-persisted transcript,
 * send/abort and the Escape-to-close shortcut. `onHealthRefresh` runs when the
 * agent reports a mutation (`refresh_health`), which reloads the dashboard.
 *
 * Quick actions prefill the composer, exactly as before: the chips drive tools
 * that can sync providers, so the user reviews the text and presses Send. The
 * non-empty guard the page had inline now runs through `healthChatRequestSchema`
 * (mirrors `HealthChatRequest`).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { useSessionMessages } from "@/lib/useSessionMessages"
import { sendHealthAgentCommand } from "./health.api"
import { HEALTH_AGENT_GREETING, HEALTH_AGENT_SESSION_KEY } from "./health.constants"
import { healthChatRequestSchema } from "./health.schema"
import type { HealthAgentMessage } from "./health.types"
import { isAbortError } from "./health.utils"

export function useHealthAgent(onHealthRefresh?: () => void) {
  const [agentOpen, setAgentOpen] = useState(false)
  const [messages, setMessages] = useSessionMessages<HealthAgentMessage>(
    HEALTH_AGENT_SESSION_KEY,
    HEALTH_AGENT_GREETING
  )
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const chatEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (!agentOpen) return undefined

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setAgentOpen(false)
    }

    globalThis.addEventListener("keydown", onKeyDown)
    return () => globalThis.removeEventListener("keydown", onKeyDown)
  }, [agentOpen])

  const sendMessage = useCallback(async () => {
    const parsed = healthChatRequestSchema.safeParse({ query: input })
    if (!parsed.success || sending) return

    const { query } = parsed.data
    const controller = new AbortController()
    abortRef.current = controller
    const nextHistory: HealthAgentMessage[] = [...messages, { role: "user", content: query }]
    setMessages(nextHistory)
    setInput("")
    setSending(true)
    setError(null)

    try {
      const result = await sendHealthAgentCommand(query, nextHistory, controller.signal)
      setMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.refresh_health) onHealthRefresh?.()
    } catch (err) {
      if (isAbortError(err)) {
        setMessages((prev) => [...prev, { role: "assistant", content: "Generation stopped." }])
        return
      }
      const message = err instanceof Error ? err.message : "Request failed"
      setError(message)
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${message}` }])
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      setSending(false)
    }
  }, [input, sending, messages, setMessages, onHealthRefresh])

  const stopMessage = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  // Prefill only: the user reviews the command and presses Send.
  const selectSuggestion = useCallback((query: string) => setInput(query), [])

  const toggleAgent = useCallback(() => setAgentOpen((open) => !open), [])
  const closeAgent = useCallback(() => setAgentOpen(false), [])

  const canSend = useMemo(() => input.trim().length > 0 && !sending, [input, sending])

  return {
    agentOpen,
    messages,
    input,
    sending,
    error,
    canSend,
    chatEndRef,
    setInput,
    toggleAgent,
    closeAgent,
    sendMessage,
    stopMessage,
    selectSuggestion,
  }
}

export type UseHealthAgentReturn = ReturnType<typeof useHealthAgent>
