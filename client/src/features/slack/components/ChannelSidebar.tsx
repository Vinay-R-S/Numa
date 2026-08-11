"use client"

import { Slack } from "lucide-react"

import type { SlackChannel } from "../slack.types"
import { channelDisplayName } from "../slack.utils"
import { ChannelIcon } from "./ChannelIcon"

interface ChannelItemProps {
  channel: SlackChannel
  active: boolean
  onSelect: () => void
}

function ChannelItem({ channel, active, onSelect }: ChannelItemProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm transition-colors ${
        active
          ? "bg-primary/15 text-primary font-medium"
          : "text-muted-foreground hover:bg-accent/40 hover:text-foreground"
      }`}
    >
      <ChannelIcon channel={channel} />
      <span className="truncate">{channelDisplayName(channel)}</span>
    </button>
  )
}

interface ChannelSidebarProps {
  channels: SlackChannel[]
  activeChannel: string
  connected: boolean
  onSelect: (slackId: string) => void
}

export function ChannelSidebar({ channels, activeChannel, connected, onSelect }: ChannelSidebarProps) {
  return (
    <aside className="hidden md:flex w-[240px] shrink-0 flex-col border-r border-border/40 bg-card/60">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border/30 shrink-0">
        <Slack className="h-4 w-4 text-[#E01E5A]" />
        <span className="text-sm font-semibold text-foreground">Channels</span>
        <span className="ml-auto rounded-full bg-muted/60 px-2 py-0.5 text-[10px] text-muted-foreground">
          {channels.length}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {channels.length === 0 ? (
          <p className="px-3 py-6 text-xs text-muted-foreground/60 text-center">
            {connected ? "No channels found. Try syncing." : "Connect Slack to see channels."}
          </p>
        ) : (
          channels.map((channel) => (
            <ChannelItem
              key={channel.id}
              channel={channel}
              active={activeChannel === channel.slack_id}
              onSelect={() => onSelect(channel.slack_id)}
            />
          ))
        )}
      </div>
    </aside>
  )
}
