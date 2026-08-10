/**
 * Master Agent dock state (NUMA-113 P4, PLAN 17.3 / 21.2).
 *
 * Owns the floating agent panel on the dashboard: visibility, session-persisted
 * transcript, in-flight/abort state and the refresh signal the backend returns.
 * Still calls `components/agents/masterAgentApi`; NUMA-118 moves that API file
 * into `features/agents/` and this hook follows it there.
 */
"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  sendMasterAgentCommand,
  type MasterAgentMessage,
} from "@/components/agents/masterAgentApi"
import { useSessionMessages } from "@/lib/useSessionMessages"
import { MASTER_AGENT_GREETING } from "./dashboard.constants"
import { isAbortError } from "./dashboard.utils"

const SESSION_KEY = "numa:session:master-agent-chat"

const GREETING: MasterAgentMessage[] = [{ role: "assistant", content: MASTER_AGENT_GREETING }]

interface UseMasterAgentChatOptions {
  /** Called when the agent reports that a domain's data changed. */
  onDataChanged: () => void
}

export function useMasterAgentChat({ onDataChanged }: UseMasterAgentChatOptions) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useSessionMessages<MasterAgentMessage>(SESSION_KEY, GREETING)
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const [lastDelegation, setLastDelegation] = useState<string | null>(null)

  const chatEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const canSend = useMemo(() => input.trim().length > 0 && !sending, [input, sending])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (!open) return undefined

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false)
    }

    globalThis.addEventListener("keydown", onKeyDown)
    return () => globalThis.removeEventListener("keydown", onKeyDown)
  }, [open])

  const handleSend = useCallback(async () => {
    const query = input.trim()
    if (!query || sending) return

    const controller = new AbortController()
    abortRef.current = controller
    const nextHistory: MasterAgentMessage[] = [...messages, { role: "user", content: query }]
    setMessages(nextHistory)
    setInput("")
    setSending(true)
    setChatError(null)

    try {
      const result = await sendMasterAgentCommand(query, nextHistory, controller.signal)
      setMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.delegated_to) setLastDelegation(result.delegated_to)
      if (
        result.refreshCalendar ||
        result.refreshTasks ||
        result.refreshHealth ||
        result.refreshGithub ||
        result.refreshJournal
      ) {
        onDataChanged()
      }
    } catch (err) {
      if (isAbortError(err)) {
        setMessages((prev) => [...prev, { role: "assistant", content: "Generation stopped." }])
        return
      }
      const msg = err instanceof Error ? err.message : "Request failed"
      setChatError(msg)
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${msg}` }])
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      setSending(false)
    }
  }, [input, sending, messages, setMessages, onDataChanged])

  const handleStop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const toggle = useCallback(() => setOpen((prev) => !prev), [])
  const close = useCallback(() => setOpen(false), [])

  return {
    open,
    messages,
    input,
    sending,
    chatError,
    lastDelegation,
    canSend,
    chatEndRef,
    setInput,
    toggle,
    close,
    handleSend,
    handleStop,
  }
}

export type UseMasterAgentChatReturn = ReturnType<typeof useMasterAgentChat>
