"use client"

import {
  CalendarAgentPanel,
  CalendarConnectPrompt,
  CalendarPageHeader,
  CalendarView,
  DayTimeline,
  DISABLED_WATER_CONFIG,
  EventEditDialog,
  useCalendar,
  useCalendarAgent,
} from "@/features/calendar"

export default function CalendarPage() {
  const {
    events,
    filteredEvents,
    todayEvents,
    loading,
    error,
    calendarConnected,
    connectingGoogle,
    refreshingEvents,
    searchQuery,
    editingEvent,
    timelineSettings,
    setSearchQuery,
    setEditingEvent,
    handleCreateEvent,
    handleUpdateEvent,
    handleDeleteEvent,
    handleConnectGoogleCalendar,
    handleRefreshEvents,
  } = useCalendar()

  const agent = useCalendarAgent()

  return (
    <div className="mx-auto flex h-[calc(100dvh-3rem)] w-full flex-col gap-3 overflow-hidden px-3 py-3 sm:h-dvh sm:gap-4 sm:px-6 sm:py-4">
      <CalendarPageHeader
        live={calendarConnected && events.length > 0}
        loading={loading}
        configured={calendarConnected}
        searchQuery={searchQuery}
        refreshing={refreshingEvents}
        agentOpen={agent.agentOpen}
        onSearchChange={setSearchQuery}
        onRefresh={() => void handleRefreshEvents()}
        onToggleAgent={agent.toggleAgent}
      />

      {loading && (
        <div className="shrink-0 rounded-xl border border-border/40 bg-card/40 p-3 text-sm text-muted-foreground sm:p-4">
          Loading calendar events...
        </div>
      )}

      {!loading && !calendarConnected && (
        <CalendarConnectPrompt connecting={connectingGoogle} onConnect={handleConnectGoogleCalendar} />
      )}

      {error && (
        <div className="shrink-0 rounded-xl border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          <p>{error}</p>
        </div>
      )}

      {!loading && (
        <div className="flex min-h-0 flex-1 gap-3 overflow-hidden sm:gap-4">
          <section className="min-h-0 min-w-0 flex-1 overflow-hidden rounded-xl border border-border/40 bg-card/40 p-2 sm:rounded-2xl sm:p-4">
            <CalendarView
              events={filteredEvents}
              onCreateEvent={handleCreateEvent}
              onUpdateEvent={handleUpdateEvent}
              onDeleteEvent={handleDeleteEvent}
              onEditEvent={setEditingEvent}
            />
          </section>

          <aside className="hidden h-full w-[320px] shrink-0 lg:block">
            <DayTimeline
              calendarEvents={todayEvents}
              updateIntervalMs={timelineSettings.updateIntervalMs}
              waterConfig={
                timelineSettings.waterEnabled === false
                  ? DISABLED_WATER_CONFIG
                  : timelineSettings.waterConfig
              }
              mealTimes={timelineSettings.mealTimes}
            />
          </aside>
        </div>
      )}

      {editingEvent && (
        <EventEditDialog
          event={editingEvent}
          onClose={() => setEditingEvent(null)}
          onSave={handleUpdateEvent}
          onDelete={handleDeleteEvent}
        />
      )}

      {agent.agentOpen && (
        <CalendarAgentPanel
          events={events}
          messages={agent.agentMessages}
          input={agent.agentInput}
          sending={agent.agentSending}
          error={agent.agentError}
          onInputChange={agent.setAgentInput}
          onSend={() => void agent.sendMessage()}
          onStop={agent.stopMessage}
          onSelectSuggestion={agent.selectSuggestion}
          onClose={agent.closeAgent}
        />
      )}
    </div>
  )
}
