"use client"

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Bot, Hash, MessageSquare, RefreshCw, Send, Slack, Wifi, WifiOff, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
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

// ── Connection Banner ────────────────────────────────────────────────────────────

function ConnectionBanner({ status, onConnect }: { status: SlackStatus | null; onConnect: () => void }) {
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
        onClick={onConnect}
        className="shrink-0 bg-[#E01E5A] text-white hover:bg-[#c91a4d] border-none"
      >
        <Slack className="mr-2 h-3.5 w-3.5" />
        Connect Slack
      </Button>
    </div>
  )
}

// ── Message Item ───────────────────────────────────────────────────────────────

function MessageItem({ msg }: { msg: SlackMessage }) {
  const displayText = formatSlackText(msg.text || "")
  const isThread = Boolean(msg.thread_ts && msg.thread_ts !== msg.ts)

  return (
    <div className="group flex items-start gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-accent/30">
      {/* Channel avatar */}
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/20">
        <span className="text-[11px] font-bold text-primary">{isThread ? "↩" : "#"}</span>
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0">
        <div className="mb-0.5 flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-primary/80">
            #{msg.channel_name || msg.slack_channel_id}
          </span>
          {isThread && (
            <span className="text-[10px] text-muted-foreground/60 border border-border/40 rounded px-1.5 py-px">
              thread
            </span>
          )}
          {msg.message_type !== "message" && (
            <span className="text-[10px] text-muted-foreground/60 border border-border/40 rounded px-1.5 py-px">
              {msg.message_type}
            </span>
          )}
        </div>
        <p className="text-sm text-foreground/90 whitespace-pre-line break-words leading-relaxed">
          {displayText || <span className="italic text-muted-foreground/50">(empty)</span>}
        </p>
      </div>

      {/* Time */}
      <span className="shrink-0 pt-0.5 text-[11px] text-muted-foreground/50 group-hover:text-muted-foreground/70 transition-colors">
        {timeAgo(msg.created_at)}
      </span>
    </div>
  )
}

// ── Chat Bubble ────────────────────────────────────────────────────────────────

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
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-primary/15 text-foreground rounded-br-sm"
            : "bg-muted/50 text-foreground rounded-bl-sm"
        }`}
      >
        {msg.content}
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

  // Agent chat
  const [chatMessages, setChatMessages] = useState<SlackAgentMessage[]>([
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

  // ── Status check ─────────────────────────────────────────────────────────────

  const checkStatus = useCallback(async () => {
    try {
      const s = await getSlackStatus()
      setStatus(s)
    } catch {
      setStatus({ connected: false, bot_configured: false })
    }
  }, [])

  // ── Load messages ─────────────────────────────────────────────────────────────

  const loadMessages = useCallback(async () => {
    setLoadingMsgs(true)
    try {
      const [msgs, chs] = await Promise.all([
        getSlackMessages({ channel: activeChannel || undefined, limit: 60 }),
        getSlackChannels(),
      ])
      setMessages(msgs)
      setChannels(chs)
    } catch {
      // fail silently — messages may be empty if Slack not connected
    } finally {
      setLoadingMsgs(false)
    }
  }, [activeChannel])

  // ── Boot ──────────────────────────────────────────────────────────────────────

  useEffect(() => {
    checkStatus()
  }, [checkStatus])

  useEffect(() => {
    loadMessages()
    const id = setInterval(loadMessages, 15_000)
    return () => clearInterval(id)
  }, [loadMessages])

  // ── Scroll chat to bottom ─────────────────────────────────────────────────────

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  // ── URL param: ?connected=1 after OAuth callback ──────────────────────────────

  useEffect(() => {
    if (searchParams.get("connected") === "1") {
      checkStatus()
      loadMessages()
    }
  }, [searchParams, checkStatus, loadMessages])

  // ── Send chat ─────────────────────────────────────────────────────────────────

  const handleSend = async () => {
    const q = chatInput.trim()
    if (!q || sending) return

    const next: SlackAgentMessage[] = [...chatMessages, { role: "user", content: q }]
    setChatMessages(next)
    setChatInput("")
    setSending(true)
    setChatError(null)

    try {
      const result = await sendSlackAgentCommand(q, next)
      setChatMessages((prev) => [...prev, { role: "assistant", content: result.response }])
      if (result.refresh_slack) {
        void loadMessages()
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Request failed"
      setChatError(msg)
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠️ ${msg}` },
      ])
    } finally {
      setSending(false)
    }
  }

  const canSend = useMemo(() => chatInput.trim().length > 0 && !sending, [chatInput, sending])

  // ── Render ─────────────────────────────────────────────────────────────────────

  return (
    <div className="mx-auto flex h-full w-full max-w-7xl flex-col gap-4 px-3 py-4 sm:px-6 sm:py-6">

      {/* ── Header ─────────────────────────────────────────────────────────────── */}
      <header className="flex flex-col gap-3 rounded-2xl border border-border/40 bg-card/40 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#E01E5A]/10 ring-1 ring-[#E01E5A]/20">
            <Slack className="h-5 w-5 text-[#E01E5A]" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              Slack Integration
            </h1>
            <p className="text-xs text-muted-foreground sm:text-sm">
              AI-powered Slack agent • 7-day rolling message window • HMAC-verified webhooks
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            id="slack-refresh-btn"
            variant="ghost"
            size="sm"
            onClick={() => { void checkStatus(); void loadMessages() }}
            className="gap-2 text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingMsgs ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </header>

      {/* ── Connection banner ────────────────────────────────────────────────── */}
      <ConnectionBanner status={status} onConnect={connectSlack} />

      {/* ── Main two-panel grid ──────────────────────────────────────────────── */}
      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-5 min-h-0">

        {/* ── LEFT: Message feed ────────────────────────────────────────────── */}
        <section className="flex flex-col rounded-2xl border border-border/40 bg-card/40 overflow-hidden lg:col-span-3">

          {/* Feed header */}
          <div className="flex items-center justify-between border-b border-border/40 px-4 py-3 shrink-0">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-primary/70" />
              <span className="text-sm font-semibold text-foreground">Recent Messages</span>
              <span className="rounded-full bg-muted/60 px-2 py-0.5 text-[10px] text-muted-foreground">
                7-day window
              </span>
            </div>
          </div>

          {/* Channel chips */}
          {channels.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap border-b border-border/30 px-4 py-2 shrink-0">
              <button
                id="slack-channel-all"
                onClick={() => setActiveChannel("")}
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                  activeChannel === ""
                    ? "bg-primary/15 text-primary"
                    : "bg-muted/40 text-muted-foreground hover:bg-muted/70"
                }`}
              >
                All channels
              </button>
              {channels.map((ch) => (
                <button
                  key={ch.id}
                  id={`slack-channel-${ch.slack_id}`}
                  onClick={() => setActiveChannel(ch.name || ch.slack_id)}
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                    activeChannel === (ch.name || ch.slack_id)
                      ? "bg-primary/15 text-primary"
                      : "bg-muted/40 text-muted-foreground hover:bg-muted/70"
                  }`}
                >
                  <Hash className="h-2.5 w-2.5" />
                  {ch.name || ch.slack_id}
                </button>
              ))}
            </div>
          )}

          {/* Messages list */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
            {loadingMsgs && messages.length === 0 ? (
              <div className="flex h-40 items-center justify-center">
                <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground/50" />
              </div>
            ) : messages.length === 0 ? (
              <div className="flex h-48 flex-col items-center justify-center gap-3 text-center px-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted/40">
                  <MessageSquare className="h-6 w-6 text-muted-foreground/50" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">No messages yet</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {status?.connected
                      ? "Messages from your Slack workspace will appear here automatically."
                      : "Connect your Slack workspace to start seeing messages here."}
                  </p>
                </div>
              </div>
            ) : (
              messages.map((msg) => <MessageItem key={msg.id} msg={msg} />)
            )}
          </div>
        </section>

        {/* ── RIGHT: Slack sub-agent chat ──────────────────────────────────── */}
        <section className="flex flex-col rounded-2xl border border-border/40 bg-card/40 overflow-hidden lg:col-span-2">

          {/* Chat header */}
          <div className="flex items-center gap-2 border-b border-border/40 px-4 py-3 shrink-0">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
              <Zap className="h-3.5 w-3.5 text-primary" />
            </div>
            <span className="text-sm font-semibold text-foreground">Slack Agent</span>
            <span className="ml-auto rounded-full border border-border/30 bg-background/40 px-2 py-0.5 text-[10px] text-muted-foreground">
              Groq · LangGraph
            </span>
          </div>

          {/* Quick actions */}
          <div className="border-b border-border/20 px-3 py-2 shrink-0">
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
          <div className="flex-1 overflow-y-auto space-y-3 p-4 min-h-0">
            {chatMessages.map((msg, i) => (
              <ChatBubble key={`${msg.role}-${i}`} msg={msg} />
            ))}

            {sending && (
              <div className="flex items-start gap-2 animate-in fade-in duration-200">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="rounded-2xl rounded-bl-sm bg-muted/50 px-4 py-3">
                  <div className="flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:300ms]" />
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
          <div className="border-t border-border/40 p-3 shrink-0">
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
                onClick={() => void handleSend()}
                disabled={!canSend}
                className="shrink-0"
              >
                <Send className="h-4 w-4 sm:mr-1" />
                <span className="hidden sm:inline">{sending ? "…" : "Send"}</span>
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
