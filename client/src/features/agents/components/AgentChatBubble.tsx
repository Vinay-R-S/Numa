"use client"

import { Bot } from "lucide-react"

import type { AgentChatMessage } from "../agents.types"
import { AgentMessageContent } from "./AgentMessageContent"

/**
 * Transcript turn for the sub-agent docks (NUMA-118 P4).
 *
 * Extracted from the identical `ChatBubble` in the slack and health panels. The
 * slack copy animated each turn in; health did not, so the entry animation is a
 * prop rather than a new default for both.
 */
interface AgentChatBubbleProps {
  message: AgentChatMessage
  animated?: boolean
}

export function AgentChatBubble({ message, animated = false }: AgentChatBubbleProps) {
  const isUser = message.role === "user"

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"}${
        animated ? " animate-in fade-in slide-in-from-bottom-2 duration-200" : ""
      }`}
    >
      {!isUser && (
        <div className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <Bot className="h-3.5 w-3.5 text-primary" />
        </div>
      )}
      <div
        className={`min-w-0 max-w-[85%] overflow-hidden rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-primary/15 text-foreground rounded-br-sm"
            : "bg-muted/50 text-foreground rounded-bl-sm"
        }`}
      >
        <AgentMessageContent content={message.content} />
      </div>
    </div>
  )
}
