"use client"

import { Square, X } from "lucide-react"

import { AgentDockShell, AgentMessageContent } from "@/features/agents"
import { Button } from "@/components/ui/button"
import type { AgentChatMessage, CalendarEvent } from "../calendar.types"
import { AgentSuggestions } from "./AgentSuggestions"

/**
 * Calendar sub-agent dock (NUMA-114 P4 / NUMA-118 P4).
 *
 * Keeps its own header, bubbles, busy line and composer: none match the slack
 * and health docks that share `AgentDockPanel`. Only the frame is shared, and
 * this is the one dock anchored below the page header rather than bottom-right.
 */

interface CalendarAgentPanelProps {
  events: CalendarEvent[]
  messages: AgentChatMessage[]
  input: string
  sending: boolean
  error: string | null
  onInputChange: (value: string) => void
  onSend: () => void
  onStop: () => void
  onSelectSuggestion: (query: string) => void
  onClose: () => void
}

export function CalendarAgentPanel({
  events,
  messages,
  input,
  sending,
  error,
  onInputChange,
  onSend,
  onStop,
  onSelectSuggestion,
  onClose,
}: CalendarAgentPanelProps) {
  return (
    <AgentDockShell anchor="top">
      <div className="mb-3 flex items-center justify-between">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-foreground">Calendar Sub-Agent</h2>
          <p className="truncate text-xs text-muted-foreground">
            Plan and manage meetings with natural language.
          </p>
        </div>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="mb-3 min-h-0 flex-1 space-y-2 overflow-y-auto rounded-xl border border-border/30 bg-background/40 p-2 sm:p-3">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={
              message.role === "user"
                ? "ml-auto min-w-0 max-w-[90%] overflow-hidden rounded-lg bg-primary/15 px-3 py-2 text-sm text-foreground"
                : "mr-auto min-w-0 max-w-[90%] overflow-hidden rounded-lg bg-muted/60 px-3 py-2 text-sm text-foreground"
            }
          >
            <AgentMessageContent content={message.content} />
          </div>
        ))}
        {sending && (
          <div className="mr-auto w-fit max-w-[90%] rounded-lg bg-muted/60 px-3 py-2 text-sm text-muted-foreground">
            Thinking and generating output...
          </div>
        )}
      </div>

      {messages.length <= 2 && (
        <AgentSuggestions events={events} onSelectSuggestion={onSelectSuggestion} />
      )}

      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              onSend()
            }
          }}
          placeholder="Try: Schedule product sync tomorrow at 10 AM"
          className="flex-1 rounded-lg border border-border/40 bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
          disabled={sending}
        />
        <Button
          type="button"
          size="sm"
          variant={sending ? "destructive" : "default"}
          className="shrink-0 sm:size-default"
          onClick={() => (sending ? onStop() : onSend())}
          disabled={!input.trim() && !sending}
        >
          {sending ? <Square className="h-4 w-4" /> : "Send"}
        </Button>
      </div>
    </AgentDockShell>
  )
}
