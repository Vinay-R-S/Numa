"use client"

import {
  ActivityTrendsSection,
  HealthAgentPanel,
  HealthPageHeader,
  HealthScore,
  HeartMetricsSection,
  MetricCardGrid,
  SleepCard,
  useHealth,
  useHealthAgent,
} from "@/features/health"

export default function HealthPage() {
  const {
    snapshots,
    intraday,
    intradayLoading,
    intradayError,
    loading,
    syncing,
    error,
    selectedDate,
    availableDates,
    selectedSnapshot,
    isLive,
    isConfigured,
    setSelectedDate,
    loadData,
    syncHealth,
  } = useHealth()

  const agent = useHealthAgent(() => { void loadData() })

  return (
    <div className="flex h-full w-full flex-col gap-4 overflow-y-auto px-4 py-4 sm:px-6 sm:py-6">
      <HealthPageHeader
        selectedDate={selectedDate}
        availableDates={availableDates}
        live={isLive}
        loading={loading}
        configured={isConfigured}
        syncing={syncing}
        agentOpen={agent.agentOpen}
        onSelectDate={setSelectedDate}
        onSync={() => { void syncHealth() }}
        onRefresh={() => { void loadData() }}
        onToggleAgent={agent.toggleAgent}
      />

      {error && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <HealthScore snapshot={selectedSnapshot} />

      <HeartMetricsSection snapshot={selectedSnapshot} />

      <MetricCardGrid snapshot={selectedSnapshot} />

      <ActivityTrendsSection
        snapshots={snapshots}
        intraday={intraday}
        selectedDate={selectedDate}
        intradayLoading={intradayLoading}
        intradayError={intradayError}
      />

      <SleepCard snapshot={selectedSnapshot} />

      {agent.agentOpen && (
        <HealthAgentPanel
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
