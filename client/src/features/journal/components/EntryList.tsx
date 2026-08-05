import { Loader2 } from "lucide-react"
import type { JournalEntry } from "../journal.types"
import { EntryCard } from "./EntryCard"

/**
 * Inner content of the entry list (loading / empty / cards). The page wraps this
 * in the mobile horizontal strip and the desktop sidebar; `layout` selects the
 * card orientation and the loading/empty styling for each.
 */
export function EntryList({
  entries,
  loading,
  selectedDate,
  onSelect,
  layout,
}: {
  entries: JournalEntry[]
  loading: boolean
  selectedDate: string | null
  onSelect: (date: string) => void
  layout: "vertical" | "horizontal"
}) {
  if (loading) {
    return (
      <div
        className={
          layout === "vertical"
            ? "flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground"
            : "flex items-center gap-2 px-2 py-3 text-sm text-muted-foreground"
        }
      >
        <Loader2 className="h-4 w-4 animate-spin" /> Loading…
      </div>
    )
  }

  if (entries.length === 0) {
    return (
      <p
        className={
          layout === "vertical"
            ? "py-8 text-center text-sm text-muted-foreground"
            : "px-2 py-3 text-sm text-muted-foreground"
        }
      >
        No entries yet
      </p>
    )
  }

  return (
    <>
      {entries.map((entry) => (
        <EntryCard
          key={entry.id}
          entry={entry}
          active={selectedDate === entry.entry_date}
          onClick={() => void onSelect(entry.entry_date)}
          layout={layout}
        />
      ))}
    </>
  )
}
