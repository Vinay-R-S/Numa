"use client"

import { Send } from "lucide-react"

import { Button } from "@/components/ui/button"

interface MessageComposerProps {
  value: string
  sending: boolean
  error: string | null
  channelName: string
  onChange: (value: string) => void
  onSend: () => void
}

export function MessageComposer({
  value,
  sending,
  error,
  channelName,
  onChange,
  onSend,
}: MessageComposerProps) {
  return (
    <div className="border-t border-border/30 px-4 py-3 shrink-0 bg-card/60">
      {error && (
        <p className="mb-2 text-xs text-destructive rounded-lg bg-destructive/10 px-3 py-2">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              onSend()
            }
          }}
          placeholder={`Message ${channelName}…`}
          className="flex-1 rounded-xl border border-border/40 bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-50"
          disabled={sending}
        />
        <Button
          type="button"
          size="sm"
          onClick={onSend}
          disabled={sending || !value.trim()}
          className="shrink-0 h-[42px] px-4"
        >
          <Send className="h-4 w-4 sm:mr-1.5" />
          <span className="hidden sm:inline">{sending ? "…" : "Send"}</span>
        </Button>
      </div>
    </div>
  )
}
