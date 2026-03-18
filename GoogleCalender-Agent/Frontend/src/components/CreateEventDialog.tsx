import { useState } from "react";
import { CalendarPlus, Clock, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CalendarEventPayload } from "@/lib/api";

interface CreateEventDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (event: CalendarEventPayload) => Promise<void>;
}

export default function CreateEventDialog({ open, onClose, onCreate }: CreateEventDialogProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  });
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");

  if (!open) return null;

  const handleSubmit = async () => {
    if (!title.trim()) return;
    await onCreate({
      title: title.trim(),
      date,
      startTime,
      endTime,
      description: description.trim() || "New event",
    });
    setTitle("");
    setDescription("");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-background/60 backdrop-blur-sm" />
      <div
        className="relative w-96 rounded-2xl border border-border/40 bg-card/95 backdrop-blur-2xl shadow-[0_8px_48px_-12px_hsl(var(--primary)/0.3)] p-6 animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/15 flex items-center justify-center ring-1 ring-primary/25">
              <CalendarPlus className="w-4 h-4 text-primary" />
            </div>
            <h3 className="text-base font-heading font-semibold text-foreground">Create Event</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3">
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Event title"
            className="w-full bg-muted/40 rounded-lg px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all"
          />
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            className="w-full bg-muted/40 rounded-lg px-3 py-2.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all"
          />
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full bg-muted/40 rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all [color-scheme:dark]"
          />
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" /> Start
              </label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full bg-muted/40 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all [color-scheme:dark]"
              />
            </div>
            <div className="flex-1">
              <label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" /> End
              </label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full bg-muted/40 rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 transition-all [color-scheme:dark]"
              />
            </div>
          </div>
        </div>

        <Button variant="glow" className="w-full mt-5" onClick={handleSubmit} disabled={!title.trim()}>
          Create Event
        </Button>
      </div>
    </div>
  );
}
