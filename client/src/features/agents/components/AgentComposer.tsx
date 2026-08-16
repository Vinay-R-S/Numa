"use client"

import { Send, Square } from "lucide-react"

import { Button } from "@/components/ui/button"

/**
 * Composer for the sub-agent docks (NUMA-118 P4).
 *
 * Extracted from the identical input row in the slack and health panels. Enter
 * sends, Shift+Enter does not, and the send button becomes a destructive Stop
 * while a reply is streaming.
 *
 * The calendar and master-agent docks keep their own composers: their button
 * treatments (a text "Send", a screen-reader-only label) and input sizing are
 * genuinely different designs, and routing all three through one component
 * would cost more props than it saves.
 */
interface AgentComposerProps {
  value: string
  sending: boolean
  canSend: boolean
  placeholder: string
  inputId?: string
  buttonId?: string
  onChange: (value: string) => void
  onSend: () => void
  onStop: () => void
}

export function AgentComposer({
  value,
  sending,
  canSend,
  placeholder,
  inputId,
  buttonId,
  onChange,
  onSend,
  onStop,
}: AgentComposerProps) {
  return (
    <div className="border-t border-border/40 px-1 pt-3 shrink-0">
      <div className="flex gap-2">
        <input
          id={inputId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              onSend()
            }
          }}
          placeholder={placeholder}
          disabled={sending}
          className="flex-1 rounded-xl border border-border/40 bg-background px-3.5 py-2 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-50"
        />
        <Button
          id={buttonId}
          type="button"
          size="sm"
          variant={sending ? "destructive" : "default"}
          onClick={() => (sending ? onStop() : onSend())}
          disabled={!canSend && !sending}
          className="shrink-0"
        >
          {sending ? <Square className="h-4 w-4 sm:mr-1" /> : <Send className="h-4 w-4 sm:mr-1" />}
          <span className="hidden sm:inline">{sending ? "Stop" : "Send"}</span>
        </Button>
      </div>
    </div>
  )
}
