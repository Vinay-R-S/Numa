"use client"

import type { SlackMessage } from "../slack.types"
import { formatSlackText, formatTime, isThreadReply, timeAgo } from "../slack.utils"

export function ChannelMessageItem({ message }: { message: SlackMessage }) {
  const displayText = formatSlackText(message.text || "")
  const isThread = isThreadReply(message)
  const senderName = message.sender_name || message.slack_user_id

  return (
    <div className={`group flex items-start gap-3 px-4 py-2 transition-colors hover:bg-accent/20 ${isThread ? "ml-8 border-l-2 border-primary/20 pl-4" : ""}`}>
      {/* Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20 mt-0.5">
        <span className="text-xs font-bold text-primary">
          {senderName?.slice(0, 2).toUpperCase() || "?"}
        </span>
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-foreground">
            {senderName || "Unknown"}
          </span>
          <span className="text-[11px] text-muted-foreground/60">
            {formatTime(message.created_at) || timeAgo(message.created_at)}
          </span>
          {isThread && (
            <span className="text-[10px] text-muted-foreground/50 border border-border/30 rounded px-1 py-px">
              thread
            </span>
          )}
        </div>
        <p className="mt-0.5 text-sm text-foreground/90 whitespace-pre-line wrap-break-word leading-relaxed">
          {displayText || <span className="italic text-muted-foreground/50">(empty)</span>}
        </p>
      </div>
    </div>
  )
}
