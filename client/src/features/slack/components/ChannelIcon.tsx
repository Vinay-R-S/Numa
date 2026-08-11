"use client"

import { Hash, Lock, User } from "lucide-react"

import type { SlackChannel } from "../slack.types"
import { isDirectMessageChannel } from "../slack.utils"

const ICON_CLASS = "h-3.5 w-3.5 shrink-0 text-muted-foreground/70"

export function ChannelIcon({ channel }: { channel: SlackChannel }) {
  if (channel.is_private) return <Lock className={ICON_CLASS} />
  if (isDirectMessageChannel(channel)) return <User className={ICON_CLASS} />
  return <Hash className={ICON_CLASS} />
}
