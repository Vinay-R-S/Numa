"use client"

import type { RefObject } from "react"
import { MessageSquare, RefreshCw } from "lucide-react"

import type { SlackMessage } from "../slack.types"
import { ChannelMessageItem } from "./ChannelMessageItem"

interface MessageListProps {
  messages: SlackMessage[]
  loading: boolean
  hasMessages: boolean
  activeChannel: string
  channelCount: number
  connected: boolean
  filtered: boolean
  endRef: RefObject<HTMLDivElement | null>
}

function emptyChannelHint(channelCount: number, connected: boolean): string {
  if (channelCount > 0) return "Pick a channel from the sidebar to view messages"
  if (connected) return "Sync your workspace to load channels"
  return "Connect Slack to get started"
}

export function MessageList({
  messages,
  loading,
  hasMessages,
  activeChannel,
  channelCount,
  connected,
  filtered,
  endRef,
}: MessageListProps) {
  if (!activeChannel) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/30">
            <MessageSquare className="h-8 w-8 text-muted-foreground/40" />
          </div>
          <div>
            <p className="text-base font-medium text-foreground/80">No channel selected</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {emptyChannelHint(channelCount, connected)}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (loading && !hasMessages) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="flex h-40 items-center justify-center">
          <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground/50" />
        </div>
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="flex h-48 flex-col items-center justify-center gap-3 text-center px-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted/40">
            <MessageSquare className="h-6 w-6 text-muted-foreground/50" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">No messages</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {filtered ? "No messages match your filters." : "No messages in this channel yet."}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="py-2">
        {messages.map((message) => (
          <ChannelMessageItem key={message.id} message={message} />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
