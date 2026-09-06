"use client"

import { AtSign, Hash, Lock, Megaphone } from "lucide-react"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { SlackChannel } from "../slack.types"
import { channelDisplayName } from "../slack.utils"
import { ChannelIcon } from "./ChannelIcon"

const NO_CHANNEL = "__none__"

interface ChannelHeaderProps {
  channels: SlackChannel[]
  activeChannel: string
  activeChannelObject?: SlackChannel
  filterMentions: boolean
  filterBroadcasts: boolean
  canFilterMentions: boolean
  onSelect: (slackId: string) => void
  onToggleMentions: () => void
  onToggleBroadcasts: () => void
}

export function ChannelHeader({
  channels,
  activeChannel,
  activeChannelObject,
  filterMentions,
  filterBroadcasts,
  canFilterMentions,
  onSelect,
  onToggleMentions,
  onToggleBroadcasts,
}: ChannelHeaderProps) {
  return (
    <div className="flex flex-col gap-2 border-b border-border/30 px-4 py-3 shrink-0">
      <div className="flex items-center gap-2 justify-between">
        <div className="flex items-center gap-2 min-w-0">
          {/* Mobile channel selector */}
          <div className="md:hidden">
            <Select
              value={activeChannel || NO_CHANNEL}
              onValueChange={(value) => onSelect(value === NO_CHANNEL ? "" : value)}
            >
              <SelectTrigger className="h-8 text-xs w-[180px]">
                <SelectValue placeholder="Select channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_CHANNEL}>Select a channel</SelectItem>
                {channels.map((channel) => (
                  <SelectItem key={channel.id} value={channel.slack_id}>
                    <span className="flex items-center gap-1.5">
                      {/* An icon, not an emoji: CLAUDE.md bans emoji in code. */}
                      {channel.is_private ? <Lock className="h-3 w-3" /> : <Hash className="h-3 w-3" />}
                      {channelDisplayName(channel)}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Desktop channel name */}
          <div className="hidden md:flex items-center gap-2">
            {activeChannelObject ? (
              <>
                <ChannelIcon channel={activeChannelObject} />
                <span className="text-sm font-semibold text-foreground truncate">
                  {channelDisplayName(activeChannelObject)}
                </span>
              </>
            ) : (
              <span className="text-sm text-muted-foreground">
                Select a channel to start chatting
              </span>
            )}
          </div>
        </div>

        {activeChannel && (
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={onToggleMentions}
              disabled={!canFilterMentions}
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                filterMentions
                  ? "bg-primary/15 text-primary"
                  : "bg-muted/40 text-muted-foreground hover:bg-muted/70"
              } ${canFilterMentions ? "" : "opacity-50 cursor-not-allowed"}`}
            >
              <AtSign className="h-3 w-3" />
              <span className="hidden sm:inline">Mentions</span>
            </button>
            <button
              type="button"
              onClick={onToggleBroadcasts}
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                filterBroadcasts
                  ? "bg-primary/15 text-primary"
                  : "bg-muted/40 text-muted-foreground hover:bg-muted/70"
              }`}
            >
              <Megaphone className="h-3 w-3" />
              <span className="hidden sm:inline">@channel</span>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
