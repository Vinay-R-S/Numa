import { useState, useEffect, useRef } from "react";
import { CalendarEvent } from "@/lib/api";
import { Clock, CalendarX, Radio, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface TimelinePanelProps {
  events: CalendarEvent[];
}

function getEventStatus(ev: CalendarEvent, now: Date): "past" | "now" | "next" | "upcoming" {
  const nowMin = now.getHours() * 60 + now.getMinutes();
  const [sh, sm] = ev.startTime.split(":").map(Number);
  const [eh, em] = ev.endTime.split(":").map(Number);
  if (nowMin >= sh * 60 + sm && nowMin < eh * 60 + em) return "now";
  if (nowMin >= eh * 60 + em) return "past";
  return "upcoming";
}

export default function TimelinePanel({ events }: TimelinePanelProps) {
  // Live clock — ticks every 10 s
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 10_000);
    return () => window.clearInterval(id);
  }, []);

  // Deduplicate: if multiple events share the same title + startTime on the same
  // day (e.g. same event appearing in both primary and a shared calendar), keep only the first.
  const seen = new Set<string>();
  const todayEvents = events
    .filter(
      (e) =>
        e.date.getFullYear() === now.getFullYear() &&
        e.date.getMonth() === now.getMonth() &&
        e.date.getDate() === now.getDate()
    )
    .sort((a, b) => a.startTime.localeCompare(b.startTime))
    .filter((e) => {
      const key = `${e.title.trim().toLowerCase()}|${e.startTime}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

  let foundNext = false;
  const statuses = todayEvents.map((ev) => {
    const s = getEventStatus(ev, now);
    if (!foundNext && s === "upcoming") {
      foundNext = true;
      return "next" as const;
    }
    return s;
  });

  // ── DOM-measured progress ────────────────────────────────────
  // Refs point to each event's actual dot circle so we can read
  // its screen position instead of guessing from time ratios.
  const wrapRef = useRef<HTMLDivElement>(null);
  const dotRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [linePx, setLinePx] = useState(0);

  useEffect(() => {
    if (!wrapRef.current || todayEvents.length === 0) return;

    const wrapTop = wrapRef.current.getBoundingClientRect().top;
    // include seconds so the dot drifts continuously between ticks
    const nowMin = now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60;
    const TOP_OFFSET = 8; // px — matches `top-2` on the background line

    const nowIdx = statuses.indexOf("now" as const);
    let px = 0;

    if (nowIdx !== -1) {
      // Currently inside this event — interpolate its dot toward the next dot
      const dotEl = dotRefs.current[nowIdx];
      if (dotEl) {
        const dotCenter = dotEl.getBoundingClientRect().top + 7.5 - wrapTop; // 7.5 = half of 15 px dot
        const [sh, sm] = todayEvents[nowIdx].startTime.split(":").map(Number);
        const [eh, em] = todayEvents[nowIdx].endTime.split(":").map(Number);
        const frac = Math.max(0, Math.min(1, (nowMin - (sh * 60 + sm)) / ((eh * 60 + em) - (sh * 60 + sm))));
        const nextEl = dotRefs.current[nowIdx + 1];
        if (nextEl) {
          const nextCenter = nextEl.getBoundingClientRect().top + 7.5 - wrapTop;
          px = dotCenter + frac * (nextCenter - dotCenter);
        } else {
          px = dotCenter + frac * 24; // last event — extend slightly past its dot
        }
      }
    } else {
      // All events are past — stop at the last past dot
      const lastPastIdx = statuses.reduce<number>((acc, s, i) => (s === "past" ? i : acc), -1);
      if (lastPastIdx !== -1) {
        const dotEl = dotRefs.current[lastPastIdx];
        if (dotEl) {
          px = dotEl.getBoundingClientRect().top + 7.5 - wrapTop;
        }
      }
    }

    setLinePx(Math.max(0, px - TOP_OFFSET));
  }, [now, todayEvents.length, statuses.join(",")]);

  const showProgress = linePx > 0;
  const glowDotTop = linePx + 8 - 4.5; // TOP_OFFSET(8) + linePx - half of 9 px glow dot

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-lg font-heading font-bold text-foreground mb-4">
        Today's Timeline
      </h2>
      <div className="flex-1 overflow-auto pr-1">
        {todayEvents.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CalendarX className="w-8 h-8 text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">No events scheduled today.</p>
          </div>
        )}

        <div className="relative" ref={wrapRef}>
          {/* Background line */}
          {todayEvents.length > 0 && (
            <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border/20" />
          )}

          {/* Glowing progress line — height is pixel-measured, not a time percentage */}
          {showProgress && (
            <>
              <div
                className="absolute left-[6px] top-2 w-[3px] rounded-full transition-all duration-1000"
                style={{
                  height: `${linePx}px`,
                  background: "linear-gradient(to bottom, hsl(var(--primary) / 0.7), hsl(var(--secondary) / 0.5))",
                  boxShadow: "0 0 8px 1px hsl(var(--primary) / 0.4)",
                }}
              />
              <div
                className="absolute left-[3px] w-[9px] h-[9px] rounded-full animate-pulse z-10 transition-all duration-1000"
                style={{
                  top: `${glowDotTop}px`,
                  background: "hsl(var(--primary))",
                  boxShadow: "0 0 12px 3px hsl(var(--primary) / 0.6), 0 0 24px 6px hsl(var(--primary) / 0.2)",
                }}
              />
            </>
          )}

          <div className="space-y-1">
            {todayEvents.map((ev, i) => {
              const status = statuses[i];
              const isNow = status === "now";
              const isNext = status === "next";
              const isPast = status === "past";

              return (
                <div
                  key={ev.id}
                  className="flex gap-3 animate-fade-in relative"
                  style={{ animationDelay: `${i * 0.06}s` }}
                >
                  {/* Dot — ref placed on the circle itself so getBoundingClientRect gives accurate Y */}
                  <div className="relative z-10 flex flex-col items-center pt-3.5">
                    <div
                      ref={(el) => { dotRefs.current[i] = el; }}
                      className={cn(
                        "w-[15px] h-[15px] rounded-full border-2 flex items-center justify-center transition-all duration-300",
                        isNow
                          ? "border-primary bg-primary shadow-[0_0_12px_hsl(var(--primary)/0.6)]"
                          : isNext
                          ? "border-secondary bg-secondary/30 shadow-[0_0_8px_hsl(var(--secondary)/0.4)]"
                          : isPast
                          ? "border-muted-foreground/30 bg-muted"
                          : "border-border/50 bg-card"
                      )}
                    >
                      {isNow && (
                        <div className="w-1.5 h-1.5 rounded-full bg-primary-foreground animate-pulse" />
                      )}
                    </div>
                  </div>

                  {/* Card */}
                  <div
                    className={cn(
                      "flex-1 rounded-xl px-3.5 py-3 mb-1 transition-all duration-300 border",
                      isNow
                        ? "bg-primary/10 border-primary/30 shadow-[0_0_20px_-6px_hsl(var(--primary)/0.25)]"
                        : isNext
                        ? "bg-secondary/8 border-secondary/20 shadow-[0_0_16px_-6px_hsl(var(--secondary)/0.2)]"
                        : isPast
                        ? "bg-muted/30 border-border/10 opacity-60"
                        : "surface-panel cosmic-card"
                    )}
                  >
                    {(isNow || isNext) && (
                      <div className="flex items-center gap-1.5 mb-1.5">
                        {isNow ? (
                          <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-primary">
                            <Radio className="w-3 h-3 animate-pulse" />
                            Happening now
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-secondary">
                            <ArrowRight className="w-3 h-3" />
                            Up next
                          </span>
                        )}
                      </div>
                    )}

                    <h4
                      className={cn(
                        "text-sm font-semibold leading-snug mb-1",
                        isPast ? "text-muted-foreground" : "text-foreground"
                      )}
                    >
                      {ev.title}
                    </h4>

                    <div
                      className={cn(
                        "flex items-center gap-1.5 text-[11px] mb-1",
                        isPast ? "text-muted-foreground/60" : "text-muted-foreground"
                      )}
                    >
                      <Clock className="w-3 h-3" />
                      <span>{ev.startTime} – {ev.endTime}</span>
                    </div>

                    <p
                      className={cn(
                        "text-xs line-clamp-2 leading-relaxed",
                        isPast ? "text-muted-foreground/50" : "text-muted-foreground"
                      )}
                    >
                      {ev.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
