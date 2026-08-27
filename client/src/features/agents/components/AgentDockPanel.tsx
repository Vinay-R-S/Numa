"use client"

import type { RefObject } from "react"
import { X, Zap } from "lucide-react"

import type { AgentChatMessage } from "../agents.types"
import { AgentChatBubble } from "./AgentChatBubble"
import { AgentComposer } from "./AgentComposer"
import { AgentDockShell } from "./AgentDockShell"
import { AgentSuggestionChips } from "./AgentSuggestionChips"
import { AgentTypingIndicator } from "./AgentTypingIndicator"

/**
 * The sub-agent dock shared by the slack and health features (NUMA-118 P4).
 *
 * Those two panels were a structural copy of each other: the same shell, the
 * same Zap header with a provider badge, the same quick-action chips, the same
 * bubbles, the same typing dots, the same in-transcript error line and the same
 * composer. Everything they actually differed on is a prop.
 *
 * The calendar and master-agent docks are not folded in here. Their headers,
 * bubbles, busy indicators, error placement and composers are each a different
 * design, so they compose `AgentDockShell` and `AgentMessageContent` directly
 * rather than being reproduced through a dozen variant props.
 */
interface AgentDockPanelProps {
  title: string
  badge: string
  placeholder: string
  suggestions: readonly string[]
  messages: AgentChatMessage[]
  input: string
  sending: boolean
  canSend: boolean
  error: string | null
  endRef: RefObject<HTMLDivElement | null>
  /** Slack animates each turn in; health does not. */
  animated?: boolean
  idPrefix?: string
  inputId?: string
  sendButtonId?: string
  onInputChange: (value: string) => void
  onSend: () => void
  onStop: () => void
  onSelectSuggestion: (query: string) => void
  onClose: () => void
}

export function AgentDockPanel({
  title,
  badge,
  placeholder,
  suggestions,
  messages,
  input,
  sending,
  canSend,
  error,
  endRef,
  animated = false,
  idPrefix,
  inputId,
  sendButtonId,
  onInputChange,
  onSend,
  onStop,
  onSelectSuggestion,
  onClose,
}: AgentDockPanelProps) {
  return (
    <AgentDockShell>
      <div className="flex items-center gap-2 border-b border-border/40 px-1 pb-3 shrink-0">
        <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
          <Zap className="h-3.5 w-3.5 text-primary" />
        </div>
        <span className="text-sm font-semibold text-foreground">{title}</span>
        <span className="ml-auto rounded-full border border-border/30 bg-background/40 px-2 py-0.5 text-[10px] text-muted-foreground">
          {badge}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="ml-1 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <AgentSuggestionChips
        suggestions={suggestions}
        idPrefix={idPrefix}
        onSelect={onSelectSuggestion}
      />

      <div className="flex-1 overflow-y-auto space-y-3 px-1 py-3 min-h-0">
        {messages.map((message, index) => (
          <AgentChatBubble
            key={`${message.role}-${index}`}
            message={message}
            animated={animated}
          />
        ))}

        {sending && <AgentTypingIndicator animated={animated} />}

        {error && (
          <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">{error}</p>
        )}
        <div ref={endRef} />
      </div>

      <AgentComposer
        value={input}
        sending={sending}
        canSend={canSend}
        placeholder={placeholder}
        inputId={inputId}
        buttonId={sendButtonId}
        onChange={onInputChange}
        onSend={onSend}
        onStop={onStop}
      />
    </AgentDockShell>
  )
}
