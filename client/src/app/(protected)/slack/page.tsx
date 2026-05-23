"use client"

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"
import { AlertTriangle, AtSign, Bot, Hash, Lock, Megaphone, MessageSquare, RefreshCw, Send, Slack, Sparkles, Square, User, Wifi, WifiOff, X, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeaderActionButton } from "@/components/ui/header-action-button"
import { LiveDataPill } from "@/components/ui/live-data-pill"
import { AgentMessageContent } from "@/components/agents/AgentMessageContent"
import { useSessionMessages } from "@/lib/useSessionMessages"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  SlackAgentMessage,
  SlackChannel,
  SlackMessage,
  SlackStatus,
  connectSlack,
  formatSlackText,
  getSlackChannels,
  getSlackMessages,
  getSlackStatus,
  sendSlackAgentCommand,
  sendSlackMessage,
  syncSlack,
} from "@/components/agents/slackAgentApi"

// ── Helpers ─────────────────────────────────────────────────────────────────────

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return ""
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function formatTime(dateStr: string | null | undefined): string {
  if (!dateStr) return ""
  return new Date(dateStr).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function getRelevance(text: string, slackUserId?: string | null) {
  const isDirect = Boolean(slackUserId && text.includes(`<@${slackUserId}>`))
  const isBroadcast =
    text.includes("<!channel>") || text.includes("<!here>") || text.includes("<!everyone>")
  return { isDirect, isBroadcast }
}

function channelIcon(ch: SlackChannel) {
  if (ch.is_private) return <Lock className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
  if (ch.name?.startsWith("dm-") || ch.name?.startsWith("mpdm-"))
    return <User className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
  return <Hash className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
}

function channelDisplayName(ch: SlackChannel) {
  return ch.name || ch.slack_id
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError"
}

// ── Connection Banner ────────────────────────────────────────────────────────────

function ConnectionBanner({ status, onConnect }: { status: SlackStatus | null; onConnect: () => void | Promise<void> }) {
  if (!status) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-border/30 bg-card/60 px-5 py-3 text-sm text-muted-foreground">
        <RefreshCw className="h-4 w-4 animate-spin text-primary/60" />
        Checking Slack connection…
      </div>
    )
  }

  if (status.connected) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-5 py-3">
        <Wifi className="h-4 w-4 text-emerald-400" />
        <span className="text-sm font-medium text-emerald-400">
          Connected to {status.team_name || "Slack"}
        </span>
        {status.bot_configured && (
          <span className="ml-auto rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
            Bot Active
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-[#E01E5A]/20 bg-[#E01E5A]/5 px-5 py-4 sm:flex-row sm:items-center">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <WifiOff className="h-4 w-4 shrink-0 text-[#E01E5A]" />
        <div>
          <p className="text-sm font-medium text-foreground">Slack not connected</p>
          <p className="text-xs text-muted-foreground">Connect your Slack workspace to use the Slack agent</p>
        </div>
      </div>
      <Button
        id="slack-connect-btn"
        size="sm"
        onClick={() => { void onConnect() }}
        className="shrink-0 bg-[#E01E5A] text-white hover:bg-[#c91a4d] border-none"
      >
        <Slack className="mr-2 h-3.5 w-3.5" />
        Connect Slack
      </Button>
    </div>
  )
}

// ── Channel Sidebar Item ────────────────────────────────────────────────────────

function ChannelItem({ ch, active, onClick }: { ch: SlackChannel; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm transition-colors ${
        active
          ? "bg-primary/15 text-primary font-medium"
          : "text-muted-foreground hover:bg-accent/40 hover:text-foreground"
      }`}
    >
      {channelIcon(ch)}
      <span className="truncate">{channelDisplayName(ch)}</span>
    </button>
  )
}

// ── Message Item (channel-scoped) ───────────────────────────────────────────────

function ChannelMessageItem({ msg }: { msg: SlackMessage }) {
  const displayText = formatSlackText(msg.text || "")
  const isThread = Boolean(msg.thread_ts && msg.thread_ts !== msg.ts)
  const senderName = msg.sender_name || msg.slack_user_id

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
            {formatTime(msg.created_at) || timeAgo(msg.created_at)}
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

// ── Chat Bubble (Agent panel) ───────────────────────────────────────────────────

function ChatBubble({ msg }: { msg: SlackAgentMessage }) {
  const isUser = msg.role === "user"
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2 duration-200`}>
      {!isUser && (
        <div className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <Bot className="h-3.5 w-3.5 text-primary" />
        </div>
      )}
      <div
        className={`min-w-0 max-w-[85%] overflow-hidden rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-primary/15 text-foreground rounded-br-sm"
            : "bg-muted/50 text-foreground rounded-bl-sm"
        }`}
      >
        <AgentMessageContent content={msg.content} />
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function SlackPage() {
  const searchParams = useSearchParams()

  // Status
  const [status, setStatus] = useState<SlackStatus | null>(null)

  // Messages feed
  const [messages, setMessages] = useState<SlackMessage[]>([])
  const [channels, setChannels] = useState<SlackChannel[]>([])
  const [activeChannel, setActiveChannel] = useState<string>("")
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const [filterMentions, setFilterMentions] = useState(false)
  const [filterBroadcasts, setFilterBroadcasts] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncError, setSyncError] = useState<string | null>(null)

  // Compose (inline at bottom of messages area)
  const [composeText, setComposeText] = useState("")
  const [composeSending, setComposeSending] = useState(false)
  const [composeError, setComposeError] = useState<string | null>(null)

  // Agent panel
  const [agentOpen, setAgentOpen] = useState(false)

  // Agent chat
  const [chatMessages, setChatMessages] = useSessionMessages<SlackAgentMessage>("numa:session:slack-agent-chat", [
    {
      role: "assistant",
      content:
        "Hi! I'm your NUMA Slack agent. I can search your Slack messages, send messages to channels, and create tasks from Slack discussions. What would you like to do?",
    },
  ])
  const [chatInput, setChatInput] = useState("")
  const [sending, setSending] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatAbortRef = useRef<AbortController | null>(null)
  const initialSyncAttemptedRef = useRef(false)
  const syncingRef = useRef(false)

  // ── Status check ─────────────────────────────────────────────────────────────

  const checkStatus = useCallback(async () => {
    try {
      const s = await getSlackStatus()
      setStatus(s)
    } catch {
      setStatus({ connected: false, bot_configured: false })
    }
  }, [])

  // ── Load channels ────────────────────────────────────────────────────────────

  const loadChannels = useCallback(async () => {
    try {
      const chs = await getSlackChannels()
      setChannels(chs)
      setSyncError(null)
      setActiveChannel((current) => {
        if (current && chs.some((channel) => channel.slack_id === current)) {
          return current
        }
        return chs[0]?.slack_id ?? ""
      })
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Failed to load Slack channels")
    }
  }, [])

  // ── Load messages for active channel ─────────────────────────────────────────

  const loadMessages = useCallback(async () => {
    if (!activeChannel) {
      setMessages([])
      return
    }
    setLoadingMsgs(true)
    try {
      const msgs = await getSlackMessages({ channel: activeChannel, limit: 60 })
      setMessages(
        [...msgs].sort((a, b) => {
          const aTime = new Date(a.created_at || Number(a.ts) * 1000).getTime()
          const bTime = new Date(b.created_at || Number(b.ts) * 1000).getTime()
          return aTime - bTime
        })
      )
    } catch {
      // fail silently
    } finally {
      setLoadingMsgs(false)
    }
  }, [activeChannel])

  const syncMessages = useCallback(async () => {
    if (syncingRef.current) return

    syncingRef.current = true
    setSyncing(true)
    setSyncError(null)
    try {
      const result = await syncSlack()
      if (!result.ok) {
        throw new Error(result.detail || "Slack sync failed")
      }
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Slack sync failed")
    } finally {
      setSyncing(false)
      syncingRef.current = false
      await loadChannels()
      await loadMessages()
    }
  }, [loadChannels, loadMessages])

  // ── Boot ──────────────────────────────────────────────────────────────────────

  useEffect(() => {
    checkStatus()
    loadChannels()
  }, [checkStatus, loadChannels])

  useEffect(() => {
    if (!activeChannel) return
    void loadMessages()
    const id = setInterval(() => {
      if (status?.connected) {
        void syncMessages()
      } else {
        void loadMessages()
      }
    }, 20_000)
    return () => clearInterval(id)
  }, [loadMessages, activeChannel, status?.connected, syncMessages])

  // ── Auto-scroll to bottom of messages ────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // ── Scroll agent chat to bottom ──────────────────────────────────────────────

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  // ── URL param: ?connected=1 after OAuth callback ─────────────────────────────

  useEffect(() => {
    if (searchParams.get("connected") === "1") {
      checkStatus()
      void syncMessages()
    }
  }, [searchParams, checkStatus, syncMessages])

  useEffect(() => {
    if (!status?.connected || channels.length > 0 || syncing || initialSyncAttemptedRef.current) {
      return
    }

    initialSyncAttemptedRef.current = true
    void syncMessages()
  }, [channels.length, status?.connected, syncing, syncMessages])

  useEffect(() => {
    if (!agentOpen) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setAgentOpen(false)
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [agentOpen])

  // ── Select channel ───────────────────────────────────────────────────────────

  const selectChannel = useCallback((slackId: string) => {
    setActiveChannel(slackId)
    setComposeText("")
    setComposeError(null)
  }, [])

  // ── Send message to active channel ───────────────────────────────────────────

  const handleComposeSend = async () => {
    if (!activeChannel || !composeText.trim() || composeSending) return
    setComposeSending(true)
    setComposeError(null)
    try {
      const result = await sendSlackMessage(activeChannel, composeText.trim())
      if (!result.ok) {
        setComposeError(result.error || "Failed to send message")
      } else {
        setComposeText("")
        void loadMessages()
      }
    } catch (err) {
      setComposeError(err instanceof Error ? err.message : "Failed to send")
    } finally {
      setComposeSending(false)
    }
  }

  // ── Send agent chat ──────────────────────────────────────────────────────────

  const handleSend = async () => {
    const q = chatInput.trim()
    if (!q || sending) return

    const controller = new AbortController()
    chatAbortRef.current = controller
    const next: SlackAgentMessage[] = [...chatMessages, { role: "user", content: q }]
    setChatMessages(next)
    setChatInput("")
    setSending(true)
    setChatError(null)

    try {
      const result = await sendSlackAgentCommand(q, next, controller.signal)
      setChatMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.refresh_slack) {
        void loadMessages()
      }
    } catch (err) {
      if (isAbortError(err)) {
        setChatMessages((prev) => [...prev, { role: "assistant", content: "Generation stopped." }])
        return
      }
      const msg = err instanceof Error ? err.message : "Request failed"
      setChatError(msg)
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${msg}` },
      ])
    } finally {
      if (chatAbortRef.current === controller) {
        chatAbortRef.current = null
      }
      setSending(false)
    }
  }

  const handleStop = () => {
    chatAbortRef.current?.abort()
  }

  const canSend = useMemo(() => chatInput.trim().length > 0 && !sending, [chatInput, sending])

  const filteredMessages = useMemo(() => {
    if (!filterMentions && !filterBroadcasts) return messages

    const slackUserId = status?.slack_user_id || ""
    return messages.filter((msg) => {
      const { isDirect, isBroadcast } = getRelevance(msg.text || "", slackUserId)
      return (
        (filterMentions && isDirect) ||
        (filterBroadcasts && isBroadcast)
      )
    })
  }, [messages, filterMentions, filterBroadcasts, status?.slack_user_id])

  const activeChannelObj = useMemo(
    () => channels.find((ch) => ch.slack_id === activeChannel),
    [channels, activeChannel]
  )

  // ── Render ─────────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full w-full flex-col gap-3 px-4 py-4 sm:px-6 sm:py-5">

      {/* ── Header ─────────────────────────────────────────────────────────────── */}
      <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
            <Slack className="h-5 w-5 text-foreground" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              Slack Integration
            </h1>
            <p className="text-xs text-muted-foreground sm:text-sm">
              AI-powered Slack agent • 7-day rolling message window
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <LiveDataPill live={Boolean(status?.connected)} loading={!status} configured={Boolean(status?.connected)} />
          <HeaderActionButton
            id="slack-sync-btn"
            icon={RefreshCw}
            label="Sync"
            loading={syncing}
            onClick={() => { void syncMessages() }}
          >
            {syncing ? "Syncing..." : "Sync"}
          </HeaderActionButton>
          <HeaderActionButton
            id="slack-refresh-btn"
            icon={RefreshCw}
            label="Refresh"
            loading={loadingMsgs}
            onClick={() => { void checkStatus(); void loadChannels(); void loadMessages() }}
          />
          <HeaderActionButton
            id="slack-agent-toggle"
            icon={Sparkles}
            label="Agent"
            active={agentOpen}
            onClick={() => setAgentOpen((v) => !v)}
          />
        </div>
      </header>

      {/* ── Connection banner ────────────────────────────────────────────────── */}
      <div className="shrink-0">
        <ConnectionBanner status={status} onConnect={connectSlack} />
      </div>

      {/* ── Main chat area: sidebar + messages ───────────────────────────────── */}
      {syncError && (
        <div className="flex shrink-0 items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{syncError}</span>
        </div>
      )}

      <div className="flex flex-1 min-h-0 rounded-2xl border border-border/40 bg-card/40 overflow-hidden">

        {/* ── Channel sidebar (desktop) ──────────────────────────────────────── */}
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
                {status?.connected ? "No channels found. Try syncing." : "Connect Slack to see channels."}
              </p>
            ) : (
              channels.map((ch) => (
                <ChannelItem
                  key={ch.id}
                  ch={ch}
                  active={activeChannel === ch.slack_id}
                  onClick={() => selectChannel(ch.slack_id)}
                />
              ))
            )}
          </div>
        </aside>

        {/* ── Right: messages + input ────────────────────────────────────────── */}
        <div className="flex flex-1 flex-col min-w-0">

          {/* Channel header */}
          <div className="flex flex-col gap-2 border-b border-border/30 px-4 py-3 shrink-0">
            <div className="flex items-center gap-2 justify-between">
              <div className="flex items-center gap-2 min-w-0">
                {/* Mobile channel selector */}
                <div className="md:hidden">
                  <Select
                    value={activeChannel || "__none__"}
                    onValueChange={(v) => selectChannel(v === "__none__" ? "" : v)}
                  >
                    <SelectTrigger className="h-8 text-xs w-[180px]">
                      <SelectValue placeholder="Select channel" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">Select a channel</SelectItem>
                      {channels.map((ch) => (
                        <SelectItem key={ch.id} value={ch.slack_id}>
                          {ch.is_private ? "🔒 " : "# "}{channelDisplayName(ch)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Desktop channel name */}
                <div className="hidden md:flex items-center gap-2">
                  {activeChannelObj ? (
                    <>
                      {channelIcon(activeChannelObj)}
                      <span className="text-sm font-semibold text-foreground truncate">
                        {channelDisplayName(activeChannelObj)}
                      </span>
                    </>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      Select a channel to start chatting
                    </span>
                  )}
                </div>
              </div>

              {/* Filter pills */}
              {activeChannel && (
                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    type="button"
                    onClick={() => setFilterMentions((prev) => !prev)}
                    disabled={!status?.slack_user_id}
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                      filterMentions
                        ? "bg-primary/15 text-primary"
                        : "bg-muted/40 text-muted-foreground hover:bg-muted/70"
                    } ${!status?.slack_user_id ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <AtSign className="h-3 w-3" />
                    <span className="hidden sm:inline">Mentions</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterBroadcasts((prev) => !prev)}
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

          {/* Messages list */}
          <div className="flex-1 overflow-y-auto">
            {!activeChannel ? (
              <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/30">
                  <MessageSquare className="h-8 w-8 text-muted-foreground/40" />
                </div>
                <div>
                  <p className="text-base font-medium text-foreground/80">No channel selected</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {channels.length > 0
                      ? "Pick a channel from the sidebar to view messages"
                      : status?.connected
                        ? "Sync your workspace to load channels"
                        : "Connect Slack to get started"}
                  </p>
                </div>
              </div>
            ) : loadingMsgs && messages.length === 0 ? (
              <div className="flex h-40 items-center justify-center">
                <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground/50" />
              </div>
            ) : filteredMessages.length === 0 ? (
              <div className="flex h-48 flex-col items-center justify-center gap-3 text-center px-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted/40">
                  <MessageSquare className="h-6 w-6 text-muted-foreground/50" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">No messages</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {filterMentions || filterBroadcasts
                      ? "No messages match your filters."
                      : "No messages in this channel yet."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="py-2">
                {filteredMessages.map((msg) => (
                  <ChannelMessageItem key={msg.id} msg={msg} />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Message input bar (always visible when channel selected) */}
          {activeChannel && (
            <div className="border-t border-border/30 px-4 py-3 shrink-0 bg-card/60">
              {composeError && (
                <p className="mb-2 text-xs text-destructive rounded-lg bg-destructive/10 px-3 py-2">
                  {composeError}
                </p>
              )}
              <div className="flex gap-2">
                <input
                  value={composeText}
                  onChange={(e) => setComposeText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      void handleComposeSend()
                    }
                  }}
                  placeholder={`Message ${activeChannelObj ? channelDisplayName(activeChannelObj) : "channel"}…`}
                  className="flex-1 rounded-xl border border-border/40 bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-50"
                  disabled={composeSending}
                />
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void handleComposeSend()}
                  disabled={composeSending || !composeText.trim()}
                  className="shrink-0 h-[42px] px-4"
                >
                  <Send className="h-4 w-4 sm:mr-1.5" />
                  <span className="hidden sm:inline">{composeSending ? "…" : "Send"}</span>
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Floating Slack Agent chat panel ──────────────────────────────── */}
      {agentOpen && (
        <section className="fixed inset-x-3 bottom-3 top-auto z-40 flex max-h-[70vh] flex-col rounded-2xl border border-border/40 bg-card/95 p-3 shadow-2xl backdrop-blur-md sm:inset-auto sm:right-6 sm:bottom-6 sm:h-[min(70vh,640px)] sm:w-[min(420px,calc(100vw-3rem))] sm:p-4">

          {/* Chat header */}
          <div className="flex items-center gap-2 border-b border-border/40 px-1 pb-3 shrink-0">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
              <Zap className="h-3.5 w-3.5 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">Slack Agent</span>
            <span className="ml-auto rounded-full border border-border/30 bg-background/40 px-2 py-0.5 text-[10px] text-muted-foreground">
              Groq · LangGraph
            </span>
            <button
              type="button"
              onClick={() => setAgentOpen(false)}
              className="ml-1 flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Quick actions */}
          <div className="border-b border-border/20 px-1 py-2 shrink-0">
            <div className="flex flex-wrap gap-1.5">
              {[
                "Show recent messages",
                "Create a task from Slack",
                "List Slack tasks",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  id={`slack-suggestion-${suggestion.replace(/\s+/g, "-").toLowerCase()}`}
                  onClick={() => setChatInput(suggestion)}
                  className="rounded-full border border-border/40 bg-background/40 px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-foreground"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-3 px-1 py-3 min-h-0">
            {chatMessages.map((msg, i) => (
              <ChatBubble key={`${msg.role}-${i}`} msg={msg} />
            ))}

            {sending && (
              <div className="flex items-start gap-2 animate-in fade-in duration-200">
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
            )}

            {chatError && (
              <p className="rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {chatError}
              </p>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-border/40 px-1 pt-3 shrink-0">
            <div className="flex gap-2">
              <input
                id="slack-chat-input"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    void handleSend()
                  }
                }}
                placeholder="Ask the Slack agent…"
                disabled={sending}
                className="flex-1 rounded-xl border border-border/40 bg-background px-3.5 py-2 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-50"
              />
              <Button
                id="slack-send-btn"
                type="button"
                size="sm"
                variant={sending ? "destructive" : "default"}
                onClick={() => sending ? handleStop() : void handleSend()}
                disabled={!canSend && !sending}
                className="shrink-0"
              >
                {sending ? <Square className="h-4 w-4 sm:mr-1" /> : <Send className="h-4 w-4 sm:mr-1" />}
                <span className="hidden sm:inline">{sending ? "Stop" : "Send"}</span>
              </Button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
