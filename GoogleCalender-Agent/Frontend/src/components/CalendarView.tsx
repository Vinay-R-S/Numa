import { useState, useRef, useCallback, useLayoutEffect, useEffect } from "react";
import { createPortal } from "react-dom";
import { ChevronLeft, ChevronRight, X, Clock, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CalendarEvent, CalendarEventPayload } from "@/lib/api";
import { cn } from "@/lib/utils";

type ViewMode = "month" | "week" | "day";

interface CalendarViewProps {
  events: CalendarEvent[];
  onCreateEvent?: (event: CalendarEventPayload) => Promise<void>;
  onUpdateEvent?: (event: CalendarEvent) => Promise<void>;
  onDeleteEvent?: (eventId: string) => Promise<void>;
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function getMonthGrid(year: number, month: number) {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const startDay = first.getDay();
  const days: (Date | null)[] = [];
  for (let i = 0; i < startDay; i++) days.push(null);
  for (let d = 1; d <= last.getDate(); d++) days.push(new Date(year, month, d));
  while (days.length % 7 !== 0) days.push(null);
  return days;
}

function getWeekDates(date: Date) {
  const start = new Date(date);
  start.setDate(start.getDate() - start.getDay());
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    return d;
  });
}

function formatHour(h: number) {
  return h > 12 ? `${h - 12}PM` : h === 12 ? "12PM" : `${h}AM`;
}

function timeToMinutes(t: string) {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
}

function minutesToTime(m: number) {
  const h = Math.floor(m / 60);
  const min = m % 60;
  return `${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}`;
}

const HOURS = Array.from({ length: 14 }, (_, i) => i + 7);
const SLOT_HEIGHT = 56; // px per hour

// ─── Event Details Popup ──────────────────────────
function EventDetailPopup({
  event,
  anchorRect,
  onDelete,
  onHoverStart,
  onHoverEnd,
  onClose,
}: {
  event: CalendarEvent;
  anchorRect: { top: number; right: number; bottom: number; left: number; width: number; height: number };
  onDelete: (eventId: string) => Promise<void>;
  onHoverStart: () => void;
  onHoverEnd: () => void;
  onClose: () => void;
}) {
  const popupRef = useRef<HTMLDivElement>(null);
  // Start off-screen so the element is measured before it becomes visible
  const [coords, setCoords] = useState({ left: -9999, top: -9999 });

  useLayoutEffect(() => {
    const popup = popupRef.current;
    if (!popup) {
      return;
    }

    const rect = popup.getBoundingClientRect();
    const margin = 12;
    const gap = 10;

    const spaceRight = window.innerWidth - anchorRect.right;
    const spaceLeft = anchorRect.left;
    const spaceBottom = window.innerHeight - anchorRect.bottom;
    const spaceTop = anchorRect.top;

    let left = spaceRight >= rect.width + gap
      ? anchorRect.right + gap
      : spaceLeft >= rect.width + gap
        ? anchorRect.left - rect.width - gap
        : Math.max(margin, Math.min(anchorRect.left, window.innerWidth - rect.width - margin));

    let top = anchorRect.top + (anchorRect.height - rect.height) / 2;

    if (top < margin && spaceBottom >= rect.height + gap) {
      top = anchorRect.bottom + gap;
    } else if (top + rect.height > window.innerHeight - margin && spaceTop >= rect.height + gap) {
      top = anchorRect.top - rect.height - gap;
    }

    left = Math.max(margin, Math.min(left, window.innerWidth - rect.width - margin));
    top = Math.max(margin, Math.min(top, window.innerHeight - rect.height - margin));

    setCoords({ left, top });
  }, [anchorRect, event.id]);

  const isSecondary = event.color === "secondary";
  const isReadonly = event.readonly;
  return (
    <div
      ref={popupRef}
      className="fixed z-[200] animate-scale-in"
      style={{ top: coords.top, left: coords.left }}
      onMouseEnter={onHoverStart}
      onMouseLeave={onHoverEnd}
    >
      <div className="w-72 rounded-xl border border-border/30 bg-card/95 backdrop-blur-2xl shadow-[0_8px_40px_-10px_hsl(var(--primary)/0.3)] p-4">
        <div className="flex items-start justify-between mb-3">
          <div className={cn("h-1 w-10 rounded-full", isSecondary ? "bg-secondary" : "bg-primary")} />
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <h3 className="text-sm font-heading font-semibold text-foreground mb-2">{event.title}</h3>
        {event.calendarName && (
          <div className="text-[11px] text-muted-foreground mb-1">Calendar: {event.calendarName}</div>
        )}
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-2">
          <Clock className="w-3 h-3" />
          <span>{event.startTime} – {event.endTime}</span>
        </div>
        <p className="text-xs text-muted-foreground/80 leading-relaxed">{event.description}</p>
        {!isReadonly && (
          <Button
            variant="outline"
            size="sm"
            className="mt-3 w-full"
            onClick={async () => {
              await onDelete(event.id);
              onClose();
            }}
          >
            Delete Event
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Create Event Popup ──────────────────────────
function CreateEventPopup({
  date,
  hour,
  position,
  onClose,
  onCreate,
}: {
  date: Date;
  hour: number;
  position: { x: number; y: number };
  onClose: () => void;
  onCreate: (ev: CalendarEventPayload) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const popupRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ left: position.x, top: position.y });
  const startTime = `${String(hour).padStart(2, "0")}:00`;
  const endTime = `${String(hour + 1).padStart(2, "0")}:00`;

  useLayoutEffect(() => {
    const popup = popupRef.current;
    if (!popup) return;
    const rect = popup.getBoundingClientRect();
    const margin = 12;
    const gap = 8;
    // Center horizontally on cursor, place below with gap
    let left = position.x - rect.width / 2;
    let top = position.y + gap;
    // If it would clip the bottom, show above the cursor instead
    if (top + rect.height > window.innerHeight - margin) {
      top = position.y - rect.height - gap;
    }
    left = Math.max(margin, Math.min(left, window.innerWidth - rect.width - margin));
    top = Math.max(margin, Math.min(top, window.innerHeight - rect.height - margin));
    setCoords({ left, top });
  }, [position]);

  const handleSubmit = async () => {
    if (!title.trim()) return;
    await onCreate({
      title: title.trim(),
      date: date.toISOString().slice(0, 10),
      startTime,
      endTime,
      description: desc.trim() || "New event",
    });
    onClose();
  };

  return (
    <div
      ref={popupRef}
      className="fixed z-[200] animate-scale-in"
      style={{ top: coords.top, left: coords.left }}
    >
      <div className="w-72 rounded-xl border border-border/30 bg-card/95 backdrop-blur-2xl shadow-[0_8px_40px_-10px_hsl(var(--primary)/0.3)] p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Plus className="w-3 h-3 text-primary" />
            <span className="font-heading font-semibold text-foreground text-sm">New Event</span>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-3">
          <Clock className="w-3 h-3" />
          <span>{startTime} – {endTime}</span>
        </div>
        <input
          autoFocus
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="Event title"
          className="w-full bg-muted/40 rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 mb-2 transition-all"
        />
        <input
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="Description (optional)"
          className="w-full bg-muted/40 rounded-lg px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 mb-3 transition-all"
        />
        <Button variant="glow" size="sm" className="w-full" onClick={handleSubmit} disabled={!title.trim()}>
          Create Event
        </Button>
      </div>
    </div>
  );
}

// ─── Draggable / Resizable Event Block ──────────────────
function DayEventBlock({
  event,
  onDragEnd,
  onResizeEnd,
  onHover,
  onHoverEnd,
}: {
  event: CalendarEvent;
  onDragEnd: (id: string, newStartMin: number) => void;
  onResizeEnd: (id: string, newEndMin: number) => void;
  onHover: (ev: CalendarEvent, e: React.MouseEvent<HTMLElement>) => void;
  onHoverEnd: () => void;
}) {
  const startMin = timeToMinutes(event.startTime);
  const endMin = timeToMinutes(event.endTime);
  const duration = endMin - startMin;
  const top = ((startMin - 7 * 60) / 60) * SLOT_HEIGHT;
  const height = (duration / 60) * SLOT_HEIGHT;

  const dragStartY = useRef(0);
  const resizeStartY = useRef(0);
  const isDragging = useRef(false);
  const isResizing = useRef(false);

  const isSecondary = event.color === "secondary";
  const isReadonly = event.readonly === true;

  const handleDragStart = (e: React.MouseEvent) => {
    if (isReadonly) {
      return;
    }
    e.stopPropagation();
    isDragging.current = true;
    dragStartY.current = e.clientY;
    const startMinOrig = startMin;

    const onMove = (me: MouseEvent) => {
      // visual feedback handled via CSS
    };
    const onUp = (me: MouseEvent) => {
      isDragging.current = false;
      const deltaY = me.clientY - dragStartY.current;
      const deltaMin = Math.round((deltaY / SLOT_HEIGHT) * 60 / 15) * 15;
      const newStart = Math.max(7 * 60, Math.min(20 * 60, startMinOrig + deltaMin));
      onDragEnd(event.id, newStart);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    if (isReadonly) {
      return;
    }
    e.stopPropagation();
    isResizing.current = true;
    resizeStartY.current = e.clientY;
    const endMinOrig = endMin;

    const onMove = (me: MouseEvent) => {};
    const onUp = (me: MouseEvent) => {
      isResizing.current = false;
      const deltaY = me.clientY - resizeStartY.current;
      const deltaMin = Math.round((deltaY / SLOT_HEIGHT) * 60 / 15) * 15;
      const newEnd = Math.max(startMin + 15, Math.min(21 * 60, endMinOrig + deltaMin));
      onResizeEnd(event.id, newEnd);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  return (
    <div
      className={cn(
        "absolute left-1 right-1 rounded-lg px-2.5 py-1.5 cursor-grab active:cursor-grabbing transition-all duration-200 group",
        isReadonly && "cursor-default",
        "border hover:shadow-[0_0_16px_-4px] hover:-translate-y-px",
        isSecondary
          ? "bg-gradient-to-br from-secondary/25 to-primary/10 border-secondary/20 hover:border-secondary/50 hover:shadow-secondary/30"
          : "bg-gradient-to-br from-primary/25 to-secondary/10 border-primary/20 hover:border-primary/50 hover:shadow-primary/30"
      )}
      style={{ top, height: Math.max(height, 24), zIndex: 10 }}
      onMouseDown={handleDragStart}
      onMouseEnter={(e) => {
        e.stopPropagation();
        onHover(event, e);
      }}
      onMouseLeave={onHoverEnd}
    >
      <div className="text-xs font-medium text-foreground truncate">{event.title}</div>
      {height >= 36 && (
        <div className="text-[10px] text-muted-foreground">{event.startTime} – {event.endTime}</div>
      )}
      {/* Resize handle */}
      {!isReadonly && (
        <div
          className="absolute bottom-0 left-0 right-0 h-2 cursor-s-resize opacity-0 group-hover:opacity-100 flex justify-center items-center"
          onMouseDown={handleResizeStart}
        >
          <div className="w-8 h-1 rounded-full bg-muted-foreground/30" />
        </div>
      )}
    </div>
  );
}

// ─── Main CalendarView ──────────────────────────
export default function CalendarView({ events, onCreateEvent, onUpdateEvent, onDeleteEvent }: CalendarViewProps) {
  const [view, setView] = useState<ViewMode>("month");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [detailPopup, setDetailPopup] = useState<{ event: CalendarEvent; anchorRect: { top: number; right: number; bottom: number; left: number; width: number; height: number } } | null>(null);
  const [createPopup, setCreatePopup] = useState<{ date: Date; hour: number; pos: { x: number; y: number } } | null>(null);
  const closeTimerRef = useRef<number | null>(null);

  // Live clock — updates every 30 s so the now-line tracks real time
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(id);
  }, []);
  const today = now; // alias kept so all isSameDay / date checks below still work

  const navigate = (dir: number) => {
    const d = new Date(currentDate);
    if (view === "month") d.setMonth(d.getMonth() + dir);
    else if (view === "week") d.setDate(d.getDate() + dir * 7);
    else d.setDate(d.getDate() + dir);
    setCurrentDate(d);
    closePopups();
  };

  const closePopups = () => {
    setDetailPopup(null);
    setCreatePopup(null);
  };

  const cancelScheduledClose = useCallback(() => {
    if (closeTimerRef.current) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  }, []);

  const schedulePopupClose = useCallback(() => {
    cancelScheduledClose();
    closeTimerRef.current = window.setTimeout(() => {
      setDetailPopup(null);
    }, 130);
  }, [cancelScheduledClose]);

  const eventsForDay = (date: Date) => events.filter((e) => isSameDay(e.date, date));

  const handleSlotClick = (date: Date, hour: number, e: React.MouseEvent) => {
    closePopups();
    setCreatePopup({ date, hour, pos: { x: e.clientX, y: e.clientY } });
  };

  const handleEventHover = useCallback((ev: CalendarEvent, e: React.MouseEvent<HTMLElement>) => {
    cancelScheduledClose();
    setCreatePopup(null);
    const rect = e.currentTarget.getBoundingClientRect();
    setDetailPopup({
      event: ev,
      anchorRect: {
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      },
    });
  }, [cancelScheduledClose]);

  const handleCreate = useCallback(async (payload: CalendarEventPayload) => {
    if (!onCreateEvent) return;
    await onCreateEvent(payload);
  }, [onCreateEvent]);

  const handleDelete = useCallback(async (eventId: string) => {
    const existing = events.find((ev) => ev.id === eventId);
    if (existing?.readonly) {
      return;
    }
    if (!onDeleteEvent) return;
    await onDeleteEvent(eventId);
  }, [events, onDeleteEvent]);

  const handleDragEnd = useCallback(async (id: string, newStartMin: number) => {
    if (!onUpdateEvent) return;

    const existing = events.find((ev) => ev.id === id);
    if (!existing) return;
    if (existing.readonly) return;

    const duration = timeToMinutes(existing.endTime) - timeToMinutes(existing.startTime);
    await onUpdateEvent({
      ...existing,
      startTime: minutesToTime(newStartMin),
      endTime: minutesToTime(newStartMin + duration),
    });
  }, [events, onUpdateEvent]);

  const handleResizeEnd = useCallback(async (id: string, newEndMin: number) => {
    if (!onUpdateEvent) return;

    const existing = events.find((ev) => ev.id === id);
    if (!existing) return;
    if (existing.readonly) return;

    await onUpdateEvent({
      ...existing,
      endTime: minutesToTime(newEndMin),
    });
  }, [events, onUpdateEvent]);

  const headerLabel =
    view === "month"
      ? `${MONTHS[currentDate.getMonth()]} ${currentDate.getFullYear()}`
      : view === "week"
        ? (() => {
            const week = getWeekDates(currentDate);
            return `${MONTHS[week[0].getMonth()]} ${week[0].getDate()} – ${week[6].getDate()}, ${week[6].getFullYear()}`;
          })()
        : `${MONTHS[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`;

  // ─── Time indicator position ──────────────
  const nowMin = today.getHours() * 60 + today.getMinutes();
  const showNowLine = nowMin >= 7 * 60 && nowMin <= 21 * 60;
  const nowTop = ((nowMin - 7 * 60) / 60) * SLOT_HEIGHT;

  return (
    <div className="flex flex-col h-full" onClick={closePopups}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-heading font-bold text-foreground">{headerLabel}</h2>
        <div className="flex items-center gap-2">
          <div className="flex surface-panel p-0.5 gap-0.5">
            {(["month", "week", "day"] as ViewMode[]).map((v) => (
              <button
                key={v}
                onClick={(e) => { e.stopPropagation(); setView(v); closePopups(); }}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-md capitalize transition-all duration-300",
                  view === v
                    ? "bg-primary text-primary-foreground shadow-[0_0_12px_-3px_hsl(var(--primary)/0.4)]"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent/40"
                )}
              >
                {v}
              </button>
            ))}
          </div>
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)} className="hover:bg-accent/50 transition-all duration-200">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => { setCurrentDate(new Date()); closePopups(); }} className="hover:bg-accent/50 transition-all duration-200">
            Today
          </Button>
          <Button variant="ghost" size="icon" onClick={() => navigate(1)} className="hover:bg-accent/50 transition-all duration-200">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Month View */}
      {view === "month" && (
        <div className="flex-1 glass-panel p-2">
          <div className="grid grid-cols-7 mb-1">
            {DAYS.map((d) => (
              <div key={d} className="text-center text-xs font-medium text-muted-foreground py-2">{d}</div>
            ))}
          </div>
          <div className="grid grid-cols-7 flex-1 gap-px">
            {getMonthGrid(currentDate.getFullYear(), currentDate.getMonth()).map((date, i) => {
              const dayEvents = date ? eventsForDay(date) : [];
              const isToday = date && isSameDay(date, today);
              return (
                <div
                  key={i}
                  className={cn(
                    "min-h-[80px] p-1.5 rounded-md transition-all duration-300",
                    date ? "hover:bg-accent/30 cursor-pointer" : "opacity-0",
                    isToday && "bg-primary/10 ring-1 ring-primary/40 shadow-[inset_0_0_16px_hsl(var(--primary)/0.08)]"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (date) { setCurrentDate(date); setView("day"); }
                  }}
                >
                  {date && (
                    <>
                      <span className={cn("text-xs font-medium", isToday ? "text-primary font-bold" : "text-muted-foreground")}>
                        {date.getDate()}
                      </span>
                      <div className="mt-0.5 space-y-0.5">
                        {dayEvents.slice(0, 2).map((ev) => (
                          <div
                            key={ev.id}
                            onMouseEnter={(e) => handleEventHover(ev, e)}
                            onMouseLeave={schedulePopupClose}
                            className={cn(
                              "text-[10px] leading-tight px-1.5 py-0.5 rounded truncate font-medium transition-all duration-300",
                              "border hover:shadow-[0_0_10px_-2px] hover:-translate-y-px",
                              ev.color === "secondary"
                                ? "bg-gradient-to-r from-secondary/25 to-primary/15 text-secondary-foreground border-secondary/20 hover:border-secondary/50 hover:shadow-secondary/30"
                                : "bg-gradient-to-r from-primary/25 to-secondary/15 text-primary-foreground border-primary/20 hover:border-primary/50 hover:shadow-primary/30"
                            )}
                          >
                            {ev.title}
                          </div>
                        ))}
                        {dayEvents.length > 2 && (
                          <span className="text-[10px] text-muted-foreground">+{dayEvents.length - 2} more</span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Week View */}
      {view === "week" && (
        <div className="flex-1 overflow-auto glass-panel p-2">
          <div className="grid grid-cols-[50px_repeat(7,1fr)] gap-px">
            <div />
            {getWeekDates(currentDate).map((d, i) => (
              <div key={i} className={cn("text-center py-2 text-xs font-medium", isSameDay(d, today) ? "text-primary" : "text-muted-foreground")}>
                <div>{DAYS[d.getDay()]}</div>
                <div className={cn("text-lg font-heading font-bold", isSameDay(d, today) ? "text-primary" : "text-foreground")}>{d.getDate()}</div>
              </div>
            ))}
            {HOURS.map((h) => (
              <div key={`row-${h}`} className="contents">
                <div className="text-[10px] text-muted-foreground text-right pr-2 pt-1">{formatHour(h)}</div>
                {getWeekDates(currentDate).map((d, di) => (
                  <div
                    key={`${h}-${di}`}
                    className="border-t border-border/20 min-h-[48px] p-0.5 relative cursor-pointer hover:bg-accent/10 transition-colors"
                    onClick={(e) => handleSlotClick(d, h, e)}
                  >
                    {eventsForDay(d).filter((ev) => parseInt(ev.startTime) === h).map((ev) => (
                      <div
                        key={ev.id}
                        onMouseEnter={(e) => handleEventHover(ev, e)}
                        onMouseLeave={schedulePopupClose}
                        className={cn(
                          "text-[10px] px-1.5 py-1 rounded font-medium transition-all duration-300 cursor-pointer",
                          "border hover:shadow-[0_0_12px_-3px] hover:-translate-y-px",
                          ev.color === "secondary"
                            ? "bg-gradient-to-r from-secondary/25 to-primary/15 text-foreground/90 border-secondary/20 hover:border-secondary/50 hover:shadow-secondary/30"
                            : "bg-gradient-to-r from-primary/25 to-secondary/15 text-foreground/90 border-primary/20 hover:border-primary/50 hover:shadow-primary/30"
                        )}
                      >
                        <div className="truncate">{ev.title}</div>
                        <div className="text-muted-foreground">{ev.startTime}</div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Day View — fully interactive */}
      {view === "day" && (
        <div className="flex-1 overflow-auto glass-panel p-2">
          <div className="grid grid-cols-[50px_1fr] gap-px">
            <div className="relative" style={{ height: HOURS.length * SLOT_HEIGHT }}>
              {HOURS.map((h) => (
                <div key={h} className="absolute text-[10px] text-muted-foreground text-right pr-2 w-full" style={{ top: (h - 7) * SLOT_HEIGHT }}>
                  {formatHour(h)}
                </div>
              ))}
            </div>
            <div className="relative" style={{ height: HOURS.length * SLOT_HEIGHT }}>
              {/* Hour grid lines */}
              {HOURS.map((h) => (
                <div
                  key={h}
                  className="absolute left-0 right-0 border-t border-border/15 cursor-pointer hover:bg-accent/10 transition-colors"
                  style={{ top: (h - 7) * SLOT_HEIGHT, height: SLOT_HEIGHT }}
                  onClick={(e) => handleSlotClick(currentDate, h, e)}
                />
              ))}

              {/* Now indicator */}
              {showNowLine && isSameDay(currentDate, today) && (
                <div className="absolute left-0 right-0 z-20 flex items-center" style={{ top: nowTop }}>
                  <div className="w-2 h-2 rounded-full bg-destructive shadow-[0_0_8px_hsl(var(--destructive)/0.5)]" />
                  <div className="flex-1 h-px bg-destructive/60" />
                </div>
              )}

              {/* Events */}
              {eventsForDay(currentDate).map((ev) => (
                <DayEventBlock
                  key={ev.id}
                  event={ev}
                  onDragEnd={handleDragEnd}
                  onResizeEnd={handleResizeEnd}
                  onHover={handleEventHover}
                  onHoverEnd={schedulePopupClose}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Popups — portaled to document.body to escape backdrop-filter containing blocks */}
      {detailPopup && createPortal(
        <EventDetailPopup
          event={detailPopup.event}
          anchorRect={detailPopup.anchorRect}
          onDelete={handleDelete}
          onHoverStart={cancelScheduledClose}
          onHoverEnd={schedulePopupClose}
          onClose={closePopups}
        />,
        document.body
      )}
      {createPopup && createPortal(
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
  );
}
