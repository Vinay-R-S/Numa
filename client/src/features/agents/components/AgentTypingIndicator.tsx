"use client"

import { Bot } from "lucide-react"

/**
 * "Thinking" bubble for the sub-agent docks (NUMA-118 P4).
 *
 * Extracted from the identical block in the slack and health panels; slack
 * faded it in, health did not.
 */
export function AgentTypingIndicator({ animated = false }: { animated?: boolean }) {
  return (
    <div className={`flex items-start gap-2${animated ? " animate-in fade-in duration-200" : ""}`}>
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
        <Bot className="h-3.5 w-3.5 text-primary" />
      </div>
      <div className="rounded-2xl rounded-bl-sm bg-muted/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
          </div>
          <span className="text-xs text-muted-foreground">Thinking and generating output...</span>
        </div>
      </div>
    </div>
  )
}
