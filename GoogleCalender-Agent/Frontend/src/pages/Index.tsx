import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import CalendarView from "@/components/CalendarView";
import TimelinePanel from "@/components/TimelinePanel";
import FloatingChat from "@/components/FloatingChat";
import QuickActions from "@/components/QuickActions";
import CreateEventDialog from "@/components/CreateEventDialog";
import {
  CalendarEvent,
  CalendarEventPayload,
  checkBackendStatus,
  createCalendarEvent,
  deleteCalendarEvent,
  fetchEvents,
  startCalendarWatch,
  subscribeToCalendarUpdates,
  updateCalendarEvent,
} from "@/lib/api";

const Index = () => {
  const [queryKey, setQueryKey] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const watchInitAttempted = useRef(false);

  const { data: events, isLoading, isError } = useQuery({
    queryKey: ["events", queryKey],
    queryFn: fetchEvents,
    retry: 1,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  const { data: backendOnline = false } = useQuery({
    queryKey: ["backend-status"],
    queryFn: checkBackendStatus,
    retry: 1,
    staleTime: 5_000,
    refetchInterval: 15_000,
  });

  const allEvents: CalendarEvent[] = events ?? [];

  const calendarEvents = useMemo(() => {
    if (!searchQuery.trim()) return allEvents;
    const q = searchQuery.toLowerCase();
    return allEvents.filter(
      (e) =>
        e.title.toLowerCase().includes(q) ||
        e.description.toLowerCase().includes(q)
    );
  }, [allEvents, searchQuery]);

  const refreshEvents = useCallback(() => {
    setQueryKey((k) => k + 1);
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeToCalendarUpdates(() => {
      refreshEvents();
    });

    return unsubscribe;
  }, [refreshEvents]);

  useEffect(() => {
    if (!backendOnline || watchInitAttempted.current) {
      return;
    }

    watchInitAttempted.current = true;
    startCalendarWatch().catch((error) => {
      console.error("Failed to initialize calendar watch:", error);
      watchInitAttempted.current = false;
    });
  }, [backendOnline]);

  // Listen for create event from QuickActions
  useEffect(() => {
    const handler = () => setCreateDialogOpen(true);
    window.addEventListener("numa-create-event", handler);
    return () => window.removeEventListener("numa-create-event", handler);
  }, []);

  const handleCreateEvent = useCallback(async (payload: CalendarEventPayload) => {
    await createCalendarEvent(payload);
    refreshEvents();
  }, [refreshEvents]);

  const handleUpdateEvent = useCallback(async (event: CalendarEvent) => {
    const payload: CalendarEventPayload = {
      title: event.title,
      date: event.date.toISOString().slice(0, 10),
      startTime: event.startTime,
      endTime: event.endTime,
      description: event.description,
    };
    await updateCalendarEvent(event.id, payload);
    refreshEvents();
  }, [refreshEvents]);

  const handleDeleteEvent = useCallback(async (eventId: string) => {
    await deleteCalendarEvent(eventId);
    refreshEvents();
  }, [refreshEvents]);

  return (
    <div className="min-h-screen p-5 md:p-8 flex flex-col gap-6 relative overflow-hidden">
      {/* Cosmic glow orbs */}
      <div
        className="cosmic-glow-orb animate-glow-pulse"
        style={{
          width: 400, height: 400,
          top: -80, left: -100,
          background: "radial-gradient(circle, hsl(225 85% 55% / 0.15), transparent 70%)",
        }}
      />
      <div
        className="cosmic-glow-orb animate-glow-pulse"
        style={{
          width: 350, height: 350,
          bottom: 40, right: -60,
          background: "radial-gradient(circle, hsl(265 55% 55% / 0.12), transparent 70%)",
          animationDelay: "2s",
        }}
      />
      <div
        className="cosmic-glow-orb animate-glow-pulse"
        style={{
          width: 250, height: 250,
          top: "45%", left: "40%",
          background: "radial-gradient(circle, hsl(230 70% 50% / 0.06), transparent 70%)",
          animationDelay: "3.5s",
        }}
      />

      <header className="relative z-10 space-y-3">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-heading font-bold text-gradient-primary tracking-tight">
            Numa AI
          </h1>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search events..."
                className="w-48 pl-8 pr-3 py-1.5 text-xs rounded-lg border border-border/20 bg-accent/20 text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/20 transition-all duration-200"
              />
            </div>
            <div className="flex items-center gap-3">
              {isLoading && (
                <span className="text-xs text-muted-foreground animate-pulse">Syncing…</span>
              )}
              {isError && (
                <span className="text-xs text-secondary">Calendar sync error</span>
              )}
              <span
                className={`text-[11px] px-2 py-1 rounded-full border ${backendOnline
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-300"
                }`}
              >
                {backendOnline ? "Backend Connected" : "Backend Offline"}
              </span>
              <span className="text-xs text-muted-foreground font-medium">
                {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Quick Actions + AI Chat trigger */}
      <div className="relative z-[90] space-y-4">
        <div className="flex items-center gap-2">
          <QuickActions />
          <div className="relative ml-auto z-[70]">
            <FloatingChat onCalendarRefresh={refreshEvents} />
          </div>
        </div>
      </div>

      {/* Main row: Calendar (70%) + Timeline (30%) */}
      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0 relative z-10">
        <section className="lg:w-[70%] glass-panel p-6 min-h-[420px] flex flex-col shadow-[0_0_40px_-12px_hsl(var(--primary)/0.18)]">
          <CalendarView
            events={calendarEvents}
            onCreateEvent={handleCreateEvent}
            onUpdateEvent={handleUpdateEvent}
            onDeleteEvent={handleDeleteEvent}
          />
        </section>

        <aside className="lg:w-[30%] glass-panel p-5">
          <TimelinePanel events={calendarEvents} />
        </aside>
      </div>




      {/* Create Event Dialog */}
      <CreateEventDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onCreate={handleCreateEvent}
      />
    </div>
  );
};

export default Index;
