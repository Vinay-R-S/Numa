"use client"

/**
 * Slack workspace hook (NUMA-115 P4, PLAN 17.4 / 21.2).
 *
 * Owns everything the page used to hold inline: connection status, channels,
 * the active channel's messages, the 20s poll, the sync guard, the mention /
 * broadcast filters and the composer. Effect dependencies and ordering are
 * unchanged from `slack/page.tsx`, so fetch timing is identical.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"

import {
  getSlackChannels,
  getSlackMessages,
  getSlackStatus,
  sendSlackMessage,
  syncSlack,
} from "./slack.api"
import { MESSAGE_PAGE_SIZE, POLL_INTERVAL_MS } from "./slack.constants"
import { slackSendMessageSchema } from "./slack.schema"
import type { SlackChannel, SlackMessage, SlackStatus } from "./slack.types"
import { getRelevance, sortMessagesByTime } from "./slack.utils"

const DISCONNECTED: SlackStatus = { connected: false, bot_configured: false }

export function useSlack() {
  const searchParams = useSearchParams()

  const [status, setStatus] = useState<SlackStatus | null>(null)
  const [channels, setChannels] = useState<SlackChannel[]>([])
  const [messages, setMessages] = useState<SlackMessage[]>([])
  const [activeChannel, setActiveChannel] = useState("")
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [filterMentions, setFilterMentions] = useState(false)
  const [filterBroadcasts, setFilterBroadcasts] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [composeText, setComposeText] = useState("")
  const [composeSending, setComposeSending] = useState(false)
  const [composeError, setComposeError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const initialSyncAttemptedRef = useRef(false)
  const syncingRef = useRef(false)

  const checkStatus = useCallback(async () => {
    try {
      setStatus(await getSlackStatus())
    } catch {
      setStatus(DISCONNECTED)
    }
  }, [])

  const loadChannels = useCallback(async () => {
    try {
      const loaded = await getSlackChannels()
      setChannels(loaded)
      setSyncError(null)
      setActiveChannel((current) => {
        if (current && loaded.some((channel) => channel.slack_id === current)) return current
        return loaded[0]?.slack_id ?? ""
      })
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Failed to load Slack channels")
    }
  }, [])

  const loadMessages = useCallback(async () => {
    if (!activeChannel) {
      setMessages([])
      return
    }

    setLoadingMessages(true)
    try {
      const loaded = await getSlackMessages({ channel: activeChannel, limit: MESSAGE_PAGE_SIZE })
      setMessages(sortMessagesByTime(loaded))
    } catch {
      // fail silently
    } finally {
      setLoadingMessages(false)
    }
  }, [activeChannel])

  const syncMessages = useCallback(async () => {
    if (syncingRef.current) return

    syncingRef.current = true
    setSyncing(true)
    setSyncError(null)
    try {
      const result = await syncSlack()
      if (!result.ok) throw new Error(result.detail || "Slack sync failed")
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : "Slack sync failed")
    } finally {
      setSyncing(false)
      syncingRef.current = false
      await loadChannels()
      await loadMessages()
    }
  }, [loadChannels, loadMessages])

  useEffect(() => {
    checkStatus()
    loadChannels()
  }, [checkStatus, loadChannels])

  useEffect(() => {
    if (!activeChannel) return undefined

    void loadMessages()
    const id = setInterval(() => {
      if (status?.connected) {
        void syncMessages()
        return
      }
      void loadMessages()
    }, POLL_INTERVAL_MS)

    return () => clearInterval(id)
  }, [loadMessages, activeChannel, status?.connected, syncMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // ?connected=1 lands here after the Slack OAuth callback.
  useEffect(() => {
    if (searchParams.get("connected") !== "1") return
    checkStatus()
    void syncMessages()
  }, [searchParams, checkStatus, syncMessages])

  // A connected workspace with no channels yet gets one automatic sync.
  useEffect(() => {
    if (!status?.connected || channels.length > 0 || syncing || initialSyncAttemptedRef.current) {
      return
    }

    initialSyncAttemptedRef.current = true
    void syncMessages()
  }, [channels.length, status?.connected, syncing, syncMessages])

  const selectChannel = useCallback((slackId: string) => {
    setActiveChannel(slackId)
    setComposeText("")
    setComposeError(null)
  }, [])

  const refreshAll = useCallback(() => {
    void checkStatus()
    void loadChannels()
    void loadMessages()
  }, [checkStatus, loadChannels, loadMessages])

  const sendComposeMessage = useCallback(async () => {
    const parsed = slackSendMessageSchema.safeParse({ channel_id: activeChannel, text: composeText })
    if (!parsed.success || composeSending) return

    setComposeSending(true)
    setComposeError(null)
    try {
      const result = await sendSlackMessage(parsed.data.channel_id, parsed.data.text)
      if (!result.ok) {
        setComposeError(result.error || "Failed to send message")
        return
      }
      setComposeText("")
      void loadMessages()
    } catch (err) {
      setComposeError(err instanceof Error ? err.message : "Failed to send")
    } finally {
      setComposeSending(false)
    }
  }, [activeChannel, composeText, composeSending, loadMessages])

  const toggleMentionFilter = useCallback(() => setFilterMentions((prev) => !prev), [])
  const toggleBroadcastFilter = useCallback(() => setFilterBroadcasts((prev) => !prev), [])

  const filteredMessages = useMemo(() => {
    if (!filterMentions && !filterBroadcasts) return messages

    const slackUserId = status?.slack_user_id || ""
    return messages.filter((message) => {
      const { isDirect, isBroadcast } = getRelevance(message.text || "", slackUserId)
      return (filterMentions && isDirect) || (filterBroadcasts && isBroadcast)
    })
  }, [messages, filterMentions, filterBroadcasts, status?.slack_user_id])

  const activeChannelObject = useMemo(
    () => channels.find((channel) => channel.slack_id === activeChannel),
    [channels, activeChannel]
  )

  return {
    status,
    channels,
    messages,
    filteredMessages,
    activeChannel,
    activeChannelObject,
    loadingMessages,
    filterMentions,
    filterBroadcasts,
    syncing,
    syncError,
    composeText,
    composeSending,
    composeError,
    messagesEndRef,
    setComposeText,
    selectChannel,
    refreshAll,
    syncMessages,
    loadMessages,
    sendComposeMessage,
    toggleMentionFilter,
    toggleBroadcastFilter,
  }
}

export type UseSlackReturn = ReturnType<typeof useSlack>
