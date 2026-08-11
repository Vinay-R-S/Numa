"use client"

/**
 * Slack sub-agent chat hook (NUMA-115 P4, PLAN 17.4 / 21.2).
 *
 * Owns the floating agent dock: open/close, the session-persisted transcript,
 * send/abort and the Escape-to-close shortcut. `onSlackRefresh` runs when the
 * agent reports a mutation (`refresh_slack`), which reloads the channel feed.
 *
 * Quick actions prefill the composer, exactly as before: the chips drive
 * mutating tools (send a message, create a task), so the user reviews the text
 * and presses Send.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { useSessionMessages } from "@/lib/useSessionMessages"
import { sendSlackAgentCommand } from "./slack.api"
import { SLACK_AGENT_GREETING, SLACK_AGENT_SESSION_KEY } from "./slack.constants"
import type { SlackAgentMessage } from "./slack.types"
import { isAbortError } from "./slack.utils"

export function useSlackAgent(onSlackRefresh?: () => void) {
  const [agentOpen, setAgentOpen] = useState(false)
  const [messages, setMessages] = useSessionMessages<SlackAgentMessage>(
    SLACK_AGENT_SESSION_KEY,
    SLACK_AGENT_GREETING
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
    const query = input.trim()
    if (!query || sending) return

    const controller = new AbortController()
    abortRef.current = controller
    const nextHistory: SlackAgentMessage[] = [...messages, { role: "user", content: query }]
    setMessages(nextHistory)
    setInput("")
    setSending(true)
    setError(null)

    try {
      const result = await sendSlackAgentCommand(query, nextHistory, controller.signal)
      setMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.refresh_slack) onSlackRefresh?.()
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
  }, [input, sending, messages, setMessages, onSlackRefresh])

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

export type UseSlackAgentReturn = ReturnType<typeof useSlackAgent>
