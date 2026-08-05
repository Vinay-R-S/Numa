import { cn } from "@/lib/utils"
import type { JournalEntry } from "../journal.types"
import { formatSidebarDate, moodEmoji } from "../journal.utils"

export function EntryCard({
  entry,
  active,
  onClick,
  layout,
}: {
  entry: JournalEntry
  active: boolean
  onClick: () => void
  layout: "vertical" | "horizontal"
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "text-left transition-all",
        layout === "vertical"
          ? "w-full rounded-xl border px-3 py-2.5"
          : "shrink-0 rounded-xl border px-3 py-2 min-w-[140px] max-w-[180px]",
        active
          ? "border-primary/30 bg-primary/10"
          : "border-border/30 bg-background/40 hover:border-border/50 hover:bg-card/60",
      )}
    >
      <div className="flex items-center gap-2 mb-0.5">
        {entry.mood && <span className="text-sm">{moodEmoji(entry.mood)}</span>}
        <span className="text-[10px] text-muted-foreground font-medium">
          {formatSidebarDate(entry.entry_date)}
        </span>
      </div>
      <p className={cn(
        "text-sm font-medium truncate",
        active ? "text-foreground" : "text-foreground/80",
      )}>
        {entry.title || "Untitled"}
      </p>
    </button>
  )
}
