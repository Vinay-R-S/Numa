import { CalendarPlus, Search, Users, Mail } from "lucide-react";

const ACTIONS = [
  { label: "Create Event", icon: CalendarPlus, command: "__create_event__" },
  { label: "Find Free Slot", icon: Search, command: "Find a free slot tomorrow" },
  { label: "Schedule Meeting", icon: Users, command: "Schedule a meeting tomorrow at 4pm" },
  { label: "Send Email", icon: Mail, command: "Send an email summary of today's events" },
];

export default function QuickActions() {
  const handleClick = (command: string) => {
    if (command === "__create_event__") {
      window.dispatchEvent(new CustomEvent("numa-create-event"));
    } else {
      window.dispatchEvent(new CustomEvent("numa-fill-chat", { detail: command }));
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {ACTIONS.map((a) => (
        <button
          key={a.label}
          onClick={() => handleClick(a.command)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border/20 bg-accent/30 text-muted-foreground hover:text-foreground hover:bg-accent/50 hover:border-primary/30 hover:shadow-[0_0_12px_-4px_hsl(var(--primary)/0.25)] transition-all duration-300"
        >
          <a.icon className="w-3.5 h-3.5" />
          {a.label}
        </button>
      ))}
    </div>
  );
}
