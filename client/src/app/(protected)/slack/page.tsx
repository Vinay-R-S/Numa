"use client"

import { AlertTriangle } from "lucide-react"

import {
  ChannelHeader,
  ChannelSidebar,
  ConnectionBanner,
  MessageComposer,
  MessageList,
  SlackAgentPanel,
  SlackPageHeader,
  channelDisplayName,
  connectSlack,
  useSlack,
  useSlackAgent,
} from "@/features/slack"

export default function SlackPage() {
  const {
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
  } = useSlack()

  const agent = useSlackAgent(() => { void loadMessages() })

  return (
    <div className="flex h-full w-full flex-col gap-3 px-4 py-4 sm:px-6 sm:py-5">
      <SlackPageHeader
        status={status}
        syncing={syncing}
        loadingMessages={loadingMessages}
        agentOpen={agent.agentOpen}
        onSync={() => { void syncMessages() }}
        onRefresh={refreshAll}
        onToggleAgent={agent.toggleAgent}
      />

      <div className="shrink-0">
        <ConnectionBanner status={status} onConnect={connectSlack} />
      </div>

      {syncError && (
        <div className="flex shrink-0 items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{syncError}</span>
        </div>
      )}

      <div className="flex flex-1 min-h-0 rounded-2xl border border-border/40 bg-card/40 overflow-hidden">
        <ChannelSidebar
          channels={channels}
          activeChannel={activeChannel}
          connected={Boolean(status?.connected)}
          onSelect={selectChannel}
        />

        <div className="flex flex-1 flex-col min-w-0">
          <ChannelHeader
            channels={channels}
            activeChannel={activeChannel}
            activeChannelObject={activeChannelObject}
            filterMentions={filterMentions}
            filterBroadcasts={filterBroadcasts}
            canFilterMentions={Boolean(status?.slack_user_id)}
            onSelect={selectChannel}
            onToggleMentions={toggleMentionFilter}
            onToggleBroadcasts={toggleBroadcastFilter}
          />

          <MessageList
            messages={filteredMessages}
            loading={loadingMessages}
            hasMessages={messages.length > 0}
            activeChannel={activeChannel}
            channelCount={channels.length}
            connected={Boolean(status?.connected)}
            filtered={filterMentions || filterBroadcasts}
            endRef={messagesEndRef}
          />

          {activeChannel && (
            <MessageComposer
              value={composeText}
              sending={composeSending}
              error={composeError}
              channelName={activeChannelObject ? channelDisplayName(activeChannelObject) : "channel"}
              onChange={setComposeText}
              onSend={() => { void sendComposeMessage() }}
            />
          )}
        </div>
      </div>

      {agent.agentOpen && (
        <SlackAgentPanel
          messages={agent.messages}
          input={agent.input}
          sending={agent.sending}
          canSend={agent.canSend}
          error={agent.error}
          endRef={agent.chatEndRef}
          onInputChange={agent.setInput}
          onSend={() => { void agent.sendMessage() }}
          onStop={agent.stopMessage}
          onSelectSuggestion={agent.selectSuggestion}
          onClose={agent.closeAgent}
        />
      )}
    </div>
  )
}
