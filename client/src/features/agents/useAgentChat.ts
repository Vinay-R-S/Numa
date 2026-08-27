"use client"

/**
 * Shared agent dock state (NUMA-118 P4, PLAN 17.5 / 21.2).
 *
 * One implementation of the chat loop the calendar, slack, health and master
 * docks each carried a copy of: open/close with Escape, composer input, the
 * in-flight guard, send with abort, the assistant reply, the "Generation
 * stopped." bubble on abort, the error bubble, and suggestion prefill.
 *
 * Everything the four copies actually disagreed on is a parameter:
 *
 * - `transcript` - where the turns live. Slack, health and the master agent
 *   keep theirs in session storage via `useSessionMessages`; the calendar keeps
 *   its own in the calendar store, whose setter takes an array and has a
 *   separate append action. Hence `replace`/`append` rather than a `setState`.
 * - `normalizeQuery` - health validates through `healthChatRequestSchema`, the
 *   others trim.
 * - `onResult` - the per-domain refresh. Awaited only when it returns a promise,
 *   so the calendar's `await fetchEvents(true)` still finishes before `sending`
 *   clears while the synchronous callbacks stay in one render pass.
 * - `errorFallback` / `errorPrefix` - the calendar says "I hit an error: ", the
 *   others "Error: ".
 *
 * `chatEndRef` is always returned. The calendar never attached it and still
 * does not, so its `scrollIntoView` stays a no-op on a null ref exactly as
 * before.
 *
 * Suggestions prefill the composer, they never send: the chips drive mutating
 * tools (write a calendar event, post to Slack, sync a provider), so the user
 * reviews the text and presses Send.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { isAbortError } from "@/lib/http"
import type { AgentChatMessage } from "./agents.types"

/** Storage adapter for a dock's turns: session-backed or store-backed. */
export interface AgentTranscript<M extends AgentChatMessage> {
  messages: M[]
  replace: (next: M[]) => void
  append: (message: M) => void
}

/** Every agent envelope carries the reply on `response`. */
export interface AgentChatResult {
  response: string
}

export interface UseAgentChatOptions<M extends AgentChatMessage, R extends AgentChatResult> {
  transcript: AgentTranscript<M>
  send: (query: string, history: M[], signal: AbortSignal) => Promise<R>
  /** Runs after a successful reply; awaited when it returns a promise. */
  onResult?: (result: R) => void | Promise<void>
  /** Returns the query to send, or null to reject the input. Defaults to a trim. */
  normalizeQuery?: (raw: string) => string | null
  errorFallback?: string
  errorPrefix?: string
}

const trimQuery = (raw: string): string | null => raw.trim() || null

export function useAgentChat<M extends AgentChatMessage, R extends AgentChatResult>({
  transcript,
  send,
  onResult,
  normalizeQuery = trimQuery,
  errorFallback = "Request failed",
  errorPrefix = "Error: ",
}: UseAgentChatOptions<M, R>) {
  const { messages, replace, append } = transcript

  const [open, setOpen] = useState(false)
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  const sendMessage = useCallback(async () => {
    const query = normalizeQuery(input)
    if (!query || sending) return

    const controller = new AbortController()
    abortRef.current = controller
    const nextHistory = [...messages, { role: "user", content: query } as M]
    replace(nextHistory)
    setInput("")
    setSending(true)
    setError(null)

    try {
      const result = await send(query, nextHistory, controller.signal)
      append({ role: "assistant", content: result.response } as M)

      const pending = onResult?.(result)
      if (pending) await pending
    } catch (err) {
      if (isAbortError(err)) {
        append({ role: "assistant", content: "Generation stopped." } as M)
        return
      }
      const message = err instanceof Error ? err.message : errorFallback
      setError(message)
      append({ role: "assistant", content: `${errorPrefix}${message}` } as M)
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      setSending(false)
    }
  }, [
    input,
    sending,
    messages,
    replace,
    append,
    send,
    onResult,
    normalizeQuery,
    errorFallback,
    errorPrefix,
  ])

  const stopMessage = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  // Prefill only: the user reviews the command and presses Send.
  const selectSuggestion = useCallback((query: string) => setInput(query), [])

  const toggleAgent = useCallback(() => setOpen((prev) => !prev), [])
  const closeAgent = useCallback(() => setOpen(false), [])

  return {
    open,
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

export type UseAgentChatReturn<
  M extends AgentChatMessage,
  R extends AgentChatResult,
> = ReturnType<typeof useAgentChat<M, R>>
