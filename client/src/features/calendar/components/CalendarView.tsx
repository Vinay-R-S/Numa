"use client"

import { createPortal } from "react-dom"

import { useCalendarView } from "../useCalendarView"
import type { CalendarEvent, CalendarEventPayload } from "../calendar.types"
import { CalendarToolbar } from "./CalendarToolbar"
import { CreateEventPopup } from "./CreateEventPopup"
import { DayGrid } from "./DayGrid"
import { EventDetailPopup } from "./EventDetailPopup"
import { MonthGrid } from "./MonthGrid"
import { WeekGrid } from "./WeekGrid"

interface CalendarViewProps {
  events: CalendarEvent[]
  onCreateEvent?: (event: CalendarEventPayload) => Promise<void>
  onUpdateEvent?: (event: CalendarEvent) => Promise<void>
  onDeleteEvent?: (eventId: string) => Promise<void>
  onEditEvent?: (event: CalendarEvent) => void
}

/** Month/week/day calendar grid. State lives in `useCalendarView`. */
export function CalendarView({
  events,
  onCreateEvent,
  onUpdateEvent,
  onDeleteEvent,
  onEditEvent,
}: CalendarViewProps) {
  const {
    view,
    currentDate,
    today,
    isMobile,
    detailPopup,
    createPopup,
    headerLabel,
    showNowLine,
    nowTop,
    navigate,
    goToToday,
    changeView,
    openDay,
    closePopups,
    cancelScheduledClose,
    schedulePopupClose,
    handleSlotClick,
    handleEventHover,
    handleCreate,
    handleDelete,
    handleDragEnd,
    handleResizeEnd,
  } = useCalendarView({ events, onCreateEvent, onUpdateEvent, onDeleteEvent })

  return (
    <div className="flex h-full flex-col" onClick={closePopups}>
      <CalendarToolbar
        headerLabel={headerLabel}
        view={view}
        isMobile={isMobile}
        onChangeView={changeView}
        onNavigate={navigate}
        onToday={goToToday}
      />

      {view === "month" && (
        <MonthGrid
          events={events}
          currentDate={currentDate}
          today={today}
          isMobile={isMobile}
          onOpenDay={openDay}
          onEventHover={handleEventHover}
          onEventHoverEnd={schedulePopupClose}
          onEditEvent={onEditEvent}
        />
      )}

      {view === "week" && (
        <WeekGrid
          events={events}
          currentDate={currentDate}
          today={today}
          isMobile={isMobile}
          onSlotClick={handleSlotClick}
          onEventHover={handleEventHover}
          onEventHoverEnd={schedulePopupClose}
          onEditEvent={onEditEvent}
        />
      )}

      {view === "day" && (
        <DayGrid
          events={events}
          currentDate={currentDate}
          today={today}
          isMobile={isMobile}
          showNowLine={showNowLine}
          nowTop={nowTop}
          onSlotClick={handleSlotClick}
          onEventHover={handleEventHover}
          onEventHoverEnd={schedulePopupClose}
          onDragEnd={handleDragEnd}
          onResizeEnd={handleResizeEnd}
          onEditEvent={onEditEvent}
        />
      )}

      {detailPopup &&
        createPortal(
          <EventDetailPopup
            event={detailPopup.event}
            anchorRect={detailPopup.anchorRect}
            onEdit={onEditEvent}
            onDelete={handleDelete}
            onHoverStart={cancelScheduledClose}
            onHoverEnd={schedulePopupClose}
            onClose={closePopups}
          />,
          document.body
        )}

      {createPopup &&
        createPortal(
          <CreateEventPopup
            date={createPopup.date}
            hour={createPopup.hour}
            position={createPopup.pos}
            onClose={closePopups}
            onCreate={handleCreate}
          />,
          document.body
        )}
    </div>
  )
}
