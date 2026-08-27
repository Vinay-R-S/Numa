"use client"

/**
 * Master agent dock state (NUMA-113 P4 / NUMA-118 P4, PLAN 17.3 / 21.2).
 *
 * Moved here from `features/dashboard` with `masterAgent.api.ts`, and rebuilt
 * on the shared `useAgentChat`. The chat loop, the Escape shortcut and the
 * abort handling now live there; what stays is what is genuinely master-agent
 * specific: the session-backed transcript, the `delegated_to` badge and the
 * refresh fan-out.
 *
 * The public return shape is unchanged, so `home/page.tsx` and
 * `MasterAgentPanel` are untouched apart from their import path.
 */
import { useCallback, useState } from "react"

import { useSessionMessages } from "@/lib/useSessionMessages"
import { MASTER_AGENT_GREETING_MESSAGES, MASTER_AGENT_SESSION_KEY } from "./agents.constants"
import { sendMasterAgentCommand } from "./masterAgent.api"
import type { MasterAgentMessage, MasterAgentResponse } from "./agents.types"
import { useAgentChat } from "./useAgentChat"

interface UseMasterAgentChatOptions {
  /** Called when the agent reports that a domain's data changed. */
  onDataChanged: () => void
}

export function useMasterAgentChat({ onDataChanged }: UseMasterAgentChatOptions) {
  const [messages, setMessages] = useSessionMessages<MasterAgentMessage>(
    MASTER_AGENT_SESSION_KEY,
    MASTER_AGENT_GREETING_MESSAGES
  )
  const [lastDelegation, setLastDelegation] = useState<string | null>(null)

  const append = useCallback(
    (message: MasterAgentMessage) => setMessages((prev) => [...prev, message]),
    [setMessages]
  )

  const onResult = useCallback(
    (result: MasterAgentResponse) => {
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
    },
    [onDataChanged]
  )

  const chat = useAgentChat<MasterAgentMessage, MasterAgentResponse>({
    transcript: { messages, replace: setMessages, append },
    send: sendMasterAgentCommand,
    onResult,
  })

  return {
    open: chat.open,
    messages: chat.messages,
    input: chat.input,
    sending: chat.sending,
    chatError: chat.error,
    lastDelegation,
    canSend: chat.canSend,
    chatEndRef: chat.chatEndRef,
    setInput: chat.setInput,
    toggle: chat.toggleAgent,
    close: chat.closeAgent,
    handleSend: chat.sendMessage,
    handleStop: chat.stopMessage,
  }
}

export type UseMasterAgentChatReturn = ReturnType<typeof useMasterAgentChat>
