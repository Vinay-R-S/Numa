"use client"

/**
 * Slack sub-agent chat hook (NUMA-115 P4 / NUMA-118 P4, PLAN 17.4 / 21.2).
 *
 * Rebuilt on the shared `useAgentChat`: the dock state, the Escape shortcut,
 * send/abort and the transcript bookkeeping live there. What stays here is the
 * session-backed transcript and the Slack-specific refresh, which runs when the
 * agent reports a mutation (`refresh_slack`) and reloads the channel feed.
 *
 * The public return shape is unchanged, so `slack/page.tsx` is untouched.
 */
import { useCallback } from "react"

import { useAgentChat } from "@/features/agents"
import { useSessionMessages } from "@/lib/useSessionMessages"
import { sendSlackAgentCommand } from "./slack.api"
import { SLACK_AGENT_GREETING, SLACK_AGENT_SESSION_KEY } from "./slack.constants"
import type { SlackAgentMessage, SlackChatResponse } from "./slack.types"

export function useSlackAgent(onSlackRefresh?: () => void) {
  const [messages, setMessages] = useSessionMessages<SlackAgentMessage>(
    SLACK_AGENT_SESSION_KEY,
    SLACK_AGENT_GREETING
  )

  const append = useCallback(
    (message: SlackAgentMessage) => setMessages((prev) => [...prev, message]),
    [setMessages]
  )

  const onResult = useCallback(
    (result: SlackChatResponse) => {
      if (result.refresh_slack) onSlackRefresh?.()
    },
    [onSlackRefresh]
  )

  const chat = useAgentChat<SlackAgentMessage, SlackChatResponse>({
    transcript: { messages, replace: setMessages, append },
    send: sendSlackAgentCommand,
    onResult,
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

export type UseSlackAgentReturn = ReturnType<typeof useSlackAgent>
